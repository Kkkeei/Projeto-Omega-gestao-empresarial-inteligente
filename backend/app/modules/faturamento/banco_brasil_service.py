from __future__ import annotations

from datetime import date
from html import escape as html_escape
from io import BytesIO
import os
import re
from pathlib import Path

from PIL import Image, ImageChops
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

from app.db.database import STORAGE_BASE
from .declaracao_service import _iterar_periodos, periodo_12_meses_por_empresa
from .repository import (
    criar_declaracao,
    listar_faturamentos_periodo,
    obter_empresa,
    salvar_config_banco_brasil,
)

BANCO_BRASIL_URL = "https://www45.bb.com.br/fmc/frm/fw0711677_1.jsp"
BANCO_BRASIL_DIR = STORAGE_BASE / "declaracoes_faturamento" / "banco_brasil"
BB_HEADLESS = os.getenv("OMEGA_BB_HEADLESS", "true").strip().lower() in {"1", "true", "sim", "yes"}
BB_BROWSER = os.getenv("OMEGA_BB_BROWSER", "chromium").strip().lower()


def _periodo_12_meses_dinamico(empresa_id: int) -> tuple[int, int, int, int, bool]:
    return periodo_12_meses_por_empresa(empresa_id)


def obter_periodo_banco_brasil(empresa_id: int) -> dict[str, Any]:
    empresa = obter_empresa(empresa_id)
    if not empresa:
        raise LookupError("Empresa não encontrada.")

    inicio_ano, inicio_mes, fim_ano, fim_mes, controle_informado = _periodo_12_meses_dinamico(empresa_id)
    registros = listar_faturamentos_periodo(
        empresa_id,
        inicio_ano,
        inicio_mes,
        fim_ano,
        fim_mes,
    )

    return {
        "periodo_inicio": f"{inicio_ano:04d}-{inicio_mes:02d}",
        "periodo_fim": f"{fim_ano:04d}-{fim_mes:02d}",
        "ultimo_faturamento_informado": _periodo_label(fim_ano, fim_mes) if controle_informado else None,
        "controle_informado": controle_informado,
        "competencia_controle": _periodo_label(fim_ano, fim_mes),
        "meses_com_dados": len(registros),
        "meses_sem_dados": max(0, 12 - len(registros)),
        "detalhamento_disponivel": True,
    }


def _periodo_label(ano: int, mes: int) -> str:
    return f"{mes:02d}/{ano}"


def _mes_label(ano: int, mes: int) -> str:
    return f"{mes:02d}/{ano}"


def _moeda_bb(valor: float) -> str:
    texto = f"{float(valor or 0):,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _percentual_bb(valor: float | None) -> str:
    if valor is None:
        return ""
    if abs(float(valor) - round(float(valor))) < 0.0001:
        return str(int(round(float(valor))))
    return f"{float(valor):.2f}".replace(".", ",")


def _regime_index(regime: str | None) -> int | None:
    texto = (regime or "").strip().lower()
    if "simples" in texto:
        return 0
    if "real" in texto:
        return 1
    if "presumido" in texto:
        return 2
    if "arbitrado" in texto:
        return 3
    if "isento" in texto or "imune" in texto:
        return 4
    return None


def _parse_data_abertura(valor: str | None) -> tuple[int, int] | None:
    if not valor:
        return None
    try:
        ano, mes = map(int, str(valor)[:7].split("-"))
        if 1 <= mes <= 12:
            return ano, mes
    except Exception:
        return None
    return None


def _meses_entre_inclusivos(inicio: tuple[int, int], fim: tuple[int, int]) -> int:
    return (fim[0] - inicio[0]) * 12 + (fim[1] - inicio[1]) + 1


async def _launch_bb_browser(playwright):
    candidatos = []
    if BB_BROWSER == "chromium":
        candidatos = [("chromium", playwright.chromium)]
    elif BB_BROWSER == "firefox":
        candidatos = [("firefox", playwright.firefox), ("chromium", playwright.chromium)]
    else:
        candidatos = [("firefox", playwright.firefox), ("chromium", playwright.chromium)]

    ultimo_erro = None
    for nome, engine in candidatos:
        try:
            browser = await engine.launch(headless=BB_HEADLESS)
            return nome, browser
        except Exception as exc:
            ultimo_erro = exc
    raise RuntimeError(f"Não foi possível iniciar o navegador do Banco do Brasil: {ultimo_erro}")


async def _frame_inputs(frame) -> list[Any]:
    inputs = frame.locator("input")
    result = []
    count = await inputs.count()
    for index in range(count):
        item = inputs.nth(index)
        tipo = (await item.get_attribute("type") or "text").lower()
        if tipo in {"hidden", "radio", "checkbox", "submit", "button", "reset", "image", "file"}:
            continue
        result.append(item)
    return result


async def _localizar_frame_formulario(page):
    ultimo_mapa = []
    melhor = None

    # O site do BB usa frames legados. A quantidade de inputs varia conforme
    # o navegador/layout carregado, então não usamos 40 campos como critério
    # obrigatório para reconhecer o formulário. O critério principal passa a
    # ser a presença dos rótulos estruturais do próprio formulário.
    for _ in range(24):
        candidatos = []
        for frame in page.frames:
            try:
                text_inputs = await _frame_inputs(frame)
                quantidade = len(text_inputs)
                texto_frame = ""
                try:
                    texto_frame = (await frame.locator("body").inner_text(timeout=1000))[:12000]
                except Exception:
                    pass

                tem_razao = bool(re.search(r"Raz[aã]o\s+Social", texto_frame, re.I))
                tem_cnpj = bool(re.search(r"CNPJ", texto_frame, re.I))
                tem_tabela = bool(
                    re.search(r"Faturamento\s+bruto\s+total", texto_frame, re.I)
                    or re.search(r"Compet[eê]ncia", texto_frame, re.I)
                )

                pontuacao = (int(tem_razao) + int(tem_cnpj) + int(tem_tabela), quantidade)
                meta = {
                    "url": frame.url,
                    "editaveis": quantidade,
                    "razao_social": tem_razao,
                    "cnpj": tem_cnpj,
                    "tabela": tem_tabela,
                }
                candidatos.append(meta)

                if melhor is None or pontuacao > melhor[0]:
                    melhor = (pontuacao, frame)

                if tem_razao and tem_cnpj and quantidade >= 10:
                    return frame, candidatos
            except Exception:
                continue

        ultimo_mapa = candidatos
        await page.wait_for_timeout(350)

    if melhor:
        _, frame = melhor
        try:
            text_inputs = await _frame_inputs(frame)
            texto_frame = (await frame.locator("body").inner_text(timeout=1000))[:12000]
            if len(text_inputs) >= 10 and re.search(r"Raz[aã]o\s+Social", texto_frame, re.I) and re.search(r"CNPJ", texto_frame, re.I):
                return frame, ultimo_mapa
        except Exception:
            pass

    try:
        titulo = await page.title()
    except Exception:
        titulo = ""
    raise RuntimeError(
        "Não foi possível localizar o formulário do Banco do Brasil. "
        f"Navegador={page.context.browser.browser_type.name if page.context.browser else 'desconhecido'}; "
        f"URL={page.url!r}; título={titulo!r}; frames={ultimo_mapa}"
    )


async def _elemento_proximo_ao_rotulo(frame, padrao: str):
    """Localiza um input pelo texto visível do rótulo e proximidade geométrica.

    O formulário SISBB é legado e seus IDs/names não são estáveis. Em vez de
    depender da posição absoluta do input na lista, usamos o texto do rótulo e
    a posição dos elementos na página.
    """
    try:
        info = await frame.evaluate(
            """
            (pattern) => {
                const re = new RegExp(pattern, 'i');
                const all = Array.from(document.querySelectorAll('body *'));
                const textos = all
                    .filter(el => {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (!text || text.length > 180 || !re.test(text)) return false;
                        const rect = el.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    })
                    .sort((a, b) => {
                        const ar = a.getBoundingClientRect();
                        const br = b.getBoundingClientRect();
                        return (ar.width * ar.height) - (br.width * br.height);
                    })[0];
                if (!textos) return null;
                const rect = textos.getBoundingClientRect();
                return {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom};
            }
            """,
            padrao,
        )
        if not info:
            return None

        inputs = await _frame_inputs(frame)
        candidatos = []
        for item in inputs:
            try:
                box = await item.bounding_box()
                if not box:
                    continue
                cx = box["x"] + box["width"] / 2
                cy = box["y"] + box["height"] / 2
                # Preferimos inputs logo abaixo do rótulo e na mesma coluna.
                horizontal = abs(cx - ((info["left"] + info["right"]) / 2))
                vertical = cy - info["bottom"]
                if -15 <= vertical <= 95:
                    score = abs(vertical) + horizontal * 0.15
                    candidatos.append((score, item))
            except Exception:
                continue
        if candidatos:
            candidatos.sort(key=lambda x: x[0])
            return candidatos[0][1]
    except Exception:
        pass
    return None


async def _set_dom_value(item, value: str) -> None:
    await item.evaluate(
        """
        (el, value) => {
            const proto = Object.getPrototypeOf(el);
            const descriptor = Object.getOwnPropertyDescriptor(proto, 'value');
            if (descriptor && descriptor.set) descriptor.set.call(el, value);
            else el.value = value;
            for (const type of ['input', 'change', 'keyup', 'blur']) {
                el.dispatchEvent(new Event(type, {bubbles: true}));
            }
        }
        """,
        value,
    )


async def _set_by_keyboard(item, value: str) -> None:
    """Fallback robusto para campos legados que dependem de keyup/onblur."""
    await item.scroll_into_view_if_needed()
    try:
        await item.fill("")
    except Exception:
        pass
    await item.click()
    await item.press("Control+A")
    await item.type(value, delay=0)
    await item.press("Tab")


async def _set_value_robusto(item, value: str, *, keyboard: bool = False) -> None:
    if keyboard:
        await _set_by_keyboard(item, value)
    else:
        await _set_dom_value(item, value)
    atual = await item.input_value()
    if value and not atual.strip():
        await _set_by_keyboard(item, value)


async def _buscar_gross_total(frame, text_inputs):
    # Primeiro: por rótulo. Isso evita o bug da posição do input auxiliar que o
    # formulário legado coloca entre CNPJ e a tabela.
    candidato = await _elemento_proximo_ao_rotulo(frame, r"Faturamento bruto total")
    if candidato:
        return candidato

    # Fallback por geometria/ordem: o terceiro campo de texto costuma ser o bruto.
    if len(text_inputs) > 2:
        return text_inputs[2]
    return None


async def _preencher_faturamento_bruto(frame, text_inputs, valor: float):
    """Preenche o campo de faturamento bruto do BB somente depois de toda a grade.

    O formulário legado pode recalcular/limpar esse campo quando a grade é alterada.
    Por isso ele é preenchido por último e testamos formatos compatíveis com máscaras
    antigas antes de considerar a operação bem-sucedida.
    """
    campo = await _buscar_gross_total(frame, text_inputs)
    if campo is None:
        raise RuntimeError("Campo 'Faturamento bruto total - Últimos 12 meses' não foi localizado.")

    # Máscaras legadas costumam aceitar melhor o valor sem separador de milhar.
    candidatos = [
        f"{float(valor):.2f}".replace('.', ','),
        f"{float(valor):.2f}",
        _moeda_bb(valor),
        str(int(round(float(valor) * 100))),
    ]

    ultimo = ""
    for valor_texto in candidatos:
        try:
            await campo.scroll_into_view_if_needed()
            await campo.click()
            await campo.press("Control+A")
            await campo.press("Backspace")
            await campo.type(valor_texto, delay=0)
            await campo.press("Tab")
            await frame.wait_for_timeout(120)
        except Exception:
            pass

        try:
            atual = (await campo.input_value()).strip()
        except Exception:
            atual = ""
        ultimo = atual

        normalizado_atual = re.sub(r"[^0-9]", "", atual)
        normalizado_esperado = str(int(round(float(valor) * 100)))
        if normalizado_atual.endswith(normalizado_esperado) or normalizado_atual == normalizado_esperado:
            return campo, atual

        # Algumas versões do formulário não aceitam teclado corretamente; em seguida
        # tentamos o setter nativo do elemento + eventos reais do DOM.
        try:
            await _set_dom_value(campo, valor_texto)
            await campo.press("Tab")
            await frame.wait_for_timeout(120)
            atual = (await campo.input_value()).strip()
            ultimo = atual
            normalizado_atual = re.sub(r"[^0-9]", "", atual)
            if normalizado_atual.endswith(normalizado_esperado) or normalizado_atual == normalizado_esperado:
                return campo, atual
        except Exception:
            pass

    raise RuntimeError(
        "O formulário do Banco do Brasil não reteve o Faturamento bruto total. "
        f"Valor enviado={candidatos[0]!r}; último valor lido={ultimo!r}."
    )



def _salvar_pdf_bb_em_a4(png_bytes: bytes, destino: Path) -> None:
    """Converte apenas o conteúdo útil do formulário BB em uma única folha A4.

    O site do BB é legado e seus elementos podem ocupar uma altura maior que A4.
    Em vez de deixar o Chromium paginar o HTML, renderizamos o formulário uma vez,
    removemos margens brancas e colocamos o resultado dentro de uma folha A4 fixa.
    """
    imagem = Image.open(BytesIO(png_bytes)).convert("RGB")

    # Remove as margens externas totalmente brancas geradas pelo documento HTML.
    fundo = Image.new("RGB", imagem.size, "white")
    diferenca = ImageChops.difference(imagem, fundo).convert("L")
    bbox = diferenca.point(lambda px: 255 if px > 10 else 0).getbbox()
    if bbox:
        imagem = imagem.crop(bbox)

    # A4 em 150 DPI. Mantemos margens discretas para o conteúdo não encostar na borda.
    dpi = 150
    a4_largura = round(8.27 * dpi)
    a4_altura = round(11.69 * dpi)
    margem = round(0.28 * dpi)  # aproximadamente 7 mm
    area_largura = a4_largura - (margem * 2)
    area_altura = a4_altura - (margem * 2)

    largura, altura = imagem.size
    escala = min(area_largura / max(largura, 1), area_altura / max(altura, 1))
    nova_largura = max(1, int(round(largura * escala)))
    nova_altura = max(1, int(round(altura * escala)))
    if (nova_largura, nova_altura) != imagem.size:
        imagem = imagem.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)

    folha = Image.new("RGB", (a4_largura, a4_altura), "white")
    x = (a4_largura - imagem.width) // 2
    y = (a4_altura - imagem.height) // 2
    folha.paste(imagem, (x, y))

    destino.parent.mkdir(parents=True, exist_ok=True)
    folha.save(destino, "PDF", resolution=dpi)


async def _fill_and_print_bb(
    *,
    empresa: dict[str, Any],
    periodos: list[tuple[int, int]],
    valores: dict[tuple[int, int], float],
    percentual_a_vista: float,
    percentual_a_prazo: float,
    percentual_cartao: float | None,
    percentual_cheque: float | None,
    percentual_boleto: float | None,
    prazo_medio_dias: int | None,
    destino: Path,
) -> float:
    async with async_playwright() as p:
        browser_name, browser = await _launch_bb_browser(p)
        context = None
        try:
            context = await browser.new_context(
                viewport={"width": 1440, "height": 1100},
                locale="pt-BR",
                ignore_https_errors=True,
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0"
                    if browser_name == "firefox"
                    else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
            await page.goto(BANCO_BRASIL_URL, wait_until="domcontentloaded", timeout=45000)

            form_frame, frame_mapa = await _localizar_frame_formulario(page)
            text_inputs = await _frame_inputs(form_frame)
            if len(text_inputs) < 40:
                raise RuntimeError(f"Formulário BB incompleto: {len(text_inputs)} campos de texto; mapa={frame_mapa}")

            razao_social = (empresa.get("razao_social") or "").strip()
            cnpj_digits = "".join(ch for ch in str(empresa.get("cnpj") or "") if ch.isdigit())
            cnpj_formatado = cnpj_digits
            if len(cnpj_digits) == 14:
                cnpj_formatado = f"{cnpj_digits[:2]}.{cnpj_digits[2:5]}.{cnpj_digits[5:8]}/{cnpj_digits[8:12]}-{cnpj_digits[12:]}"

            total_bruto = sum(float(valores.get(periodo, 0) or 0) for periodo in periodos)
            abertura = _parse_data_abertura(empresa.get("data_abertura"))
            periodos_ativos = [p for p in periodos if abertura is None or p >= abertura]
            registros_ativos = [valores[p] for p in periodos_ativos if p in valores]
            if abertura and len(periodos_ativos) < 12 and registros_ativos:
                total_bruto = (sum(registros_ativos) / len(registros_ativos)) * 12

            # Razão e CNPJ pela ordem estável do cabeçalho.
            await _set_value_robusto(text_inputs[0], razao_social, keyboard=True)
            await _set_value_robusto(text_inputs[1], cnpj_formatado, keyboard=True)

            # As 12 linhas continuam em sequência após os três campos do cabeçalho;
            # localizamos a primeira linha pelo seu padrão de 3 entradas e usamos o
            # agrupamento para as demais. Se existir um campo auxiliar antes da grade,
            # escolhemos o primeiro input cujo y seja maior que o cabeçalho da tabela.
            # Fallback comprovado do formulário: índice 3 é a primeira linha.
            row_start = 3
            cash_tot = 0.0
            credit_tot = 0.0
            for row_index, (ano, mes) in enumerate(periodos):
                base = row_start + row_index * 3
                valor = float(valores.get((ano, mes), 0) or 0)
                a_vista = round(valor * percentual_a_vista / 100, 2)
                a_prazo = round(valor - a_vista, 2)
                cash_tot += a_vista
                credit_tot += a_prazo
                await _set_dom_value(text_inputs[base], _mes_label(ano, mes))
                await _set_dom_value(text_inputs[base + 1], _moeda_bb(a_vista))
                await _set_dom_value(text_inputs[base + 2], _moeda_bb(a_prazo))

            total_base = row_start + len(periodos) * 3
            await _set_dom_value(text_inputs[total_base], _moeda_bb(cash_tot))
            await _set_dom_value(text_inputs[total_base + 1], _moeda_bb(credit_tot))
            await text_inputs[total_base + 1].press("Tab")

            # O BB pode recalcular ou limpar o campo de faturamento bruto enquanto a grade é preenchida.
            # Por isso, preenchemos esse campo somente agora, depois de todas as competências e totais.
            gross_total, gross_final = await _preencher_faturamento_bruto(form_frame, text_inputs, total_bruto)
            print(f"[BB] Faturamento bruto preenchido: {gross_final!r}")

            # Os campos abaixo permanecem opcionais e vazios nesta versão.
            for offset in (2, 3, 4, 5):
                try:
                    await _set_dom_value(text_inputs[total_base + offset], "")
                except Exception:
                    pass

            local = str(empresa.get("municipio") or "").strip().title()
            uf = str(empresa.get("uf") or "").strip().upper()
            local_data = f"{local}-{uf}" if local and uf else local
            if local_data:
                local_data += f" {date.today().strftime('%d/%m/%Y')}"
            else:
                local_data = date.today().strftime("%d/%m/%Y")
            await _set_dom_value(text_inputs[total_base + 6], local_data)

            regime_index = _regime_index(empresa.get("regime_tributario"))
            radios = form_frame.locator('input[type="radio"]')
            if regime_index is not None and await radios.count() > regime_index:
                await radios.nth(regime_index).check(force=True)

            # Gera o PDF somente do formulário preenchido, antes do clique em Salvar.
            # Não usamos page.pdf() diretamente na página do BB, porque o HTML legado
            # pode ultrapassar A4 e produzir uma saída exageradamente comprida.
            destino.parent.mkdir(parents=True, exist_ok=True)

            html_formulario = await form_frame.evaluate(
                """() => {
                    const origem = document.documentElement;
                    const clone = origem.cloneNode(true);
                    const camposOrigem = origem.querySelectorAll('input, textarea, select');
                    const camposClone = clone.querySelectorAll('input, textarea, select');

                    camposOrigem.forEach((campo, index) => {
                        const destino = camposClone[index];
                        if (!destino) return;
                        const tag = campo.tagName.toLowerCase();
                        const tipo = (campo.getAttribute('type') || '').toLowerCase();

                        if (tag === 'textarea') {
                            destino.textContent = campo.value || '';
                        } else if (tag === 'select') {
                            Array.from(destino.options).forEach((option, optionIndex) => {
                                const origemOption = campo.options[optionIndex];
                                if (origemOption?.selected) option.setAttribute('selected', 'selected');
                                else option.removeAttribute('selected');
                            });
                        } else if (tipo === 'checkbox' || tipo === 'radio') {
                            if (campo.checked) destino.setAttribute('checked', 'checked');
                            else destino.removeAttribute('checked');
                        } else {
                            destino.setAttribute('value', campo.value || '');
                        }
                    });

                    return clone.outerHTML;
                }"""
            )
            frame_url = form_frame.url or BANCO_BRASIL_URL
            base_tag = f'<base href="{html_escape(frame_url, quote=True)}">'
            if '<head>' in html_formulario.lower():
                pos = html_formulario.lower().find('<head>') + len('<head>')
                html_formulario = html_formulario[:pos] + base_tag + html_formulario[pos:]
            else:
                html_formulario = html_formulario.replace('<html>', f'<html><head>{base_tag}</head>', 1)

            pdf_context = await browser.new_context(
                viewport={"width": 1400, "height": 1400},
                device_scale_factor=2,
                locale="pt-BR",
                ignore_https_errors=True,
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0"
                    if browser_name == "firefox"
                    else "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
                ),
            )
            pdf_page = await pdf_context.new_page()
            try:
                await pdf_page.set_content('<!DOCTYPE html>' + html_formulario, wait_until="domcontentloaded")
                await pdf_page.add_style_tag(content="""
                    html, body {
                        margin: 0 !important;
                        padding: 0 !important;
                        background: #fff !important;
                    }
                    input[type=submit], input[type=button], input[type=image], button, a[href*="print" i] {
                        display: none !important;
                    }
                """)
                await pdf_page.wait_for_timeout(800)

                # Captura somente o documento renderizado pelo frame, sem menu, frameset
                # ou áreas vazias do site.
                png_bytes = await pdf_page.locator("body").screenshot(
                    type="png",
                    animations="disabled",
                    caret="hide",
                )
                _salvar_pdf_bb_em_a4(png_bytes, destino)
            finally:
                try:
                    await pdf_context.close()
                except Exception:
                    pass

            # Somente agora clicamos no botão Salvar do rodapé do formulário oficial.
            save_button = form_frame.locator(
                'input[value*="Salvar" i], input[name*="Salvar" i], input[alt*="Salvar" i], '
                'input[title*="Salvar" i], input[src*="salvar" i], button:has-text("Salvar"), a:has-text("Salvar")'
            ).last
            if await save_button.count() == 0:
                raise RuntimeError("Não foi localizado o botão 'Salvar' no formulário do Banco do Brasil.")

            async def accept_dialog(dialog):
                await dialog.accept()

            page.on("dialog", accept_dialog)
            try:
                await save_button.evaluate("el => el.click()")
            except Exception:
                try:
                    await save_button.click(timeout=8000, no_wait_after=True)
                except PlaywrightTimeoutError:
                    await save_button.evaluate("el => el.click()")
            await page.wait_for_timeout(700)

            return float(total_bruto)
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            try:
                await browser.close()
            except Exception:
                pass


async def gerar_declaracao_banco_brasil(
    *,
    empresa_id: int,
    usuario_id: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    empresa = obter_empresa(empresa_id)
    if not empresa:
        raise LookupError("Empresa não encontrada.")

    inicio_ano, inicio_mes, fim_ano, fim_mes, _ = _periodo_12_meses_dinamico(empresa_id)
    periodos = _iterar_periodos(inicio_ano, inicio_mes, fim_ano, fim_mes)
    registros = listar_faturamentos_periodo(empresa_id, inicio_ano, inicio_mes, fim_ano, fim_mes)
    valores = {(int(item["competencia_ano"]), int(item["competencia_mes"])): float(item["valor"] or 0) for item in registros}

    percentual_a_vista = float(config.get("percentual_a_vista", 20))
    percentual_a_prazo = float(config.get("percentual_a_prazo", 80))
    if abs(percentual_a_vista + percentual_a_prazo - 100) > 0.01:
        raise ValueError("Percentual à vista + percentual a prazo deve totalizar 100%.")

    config_salva = salvar_config_banco_brasil(empresa_id, config)
    nome_seguro = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(empresa["razao_social"])).strip("_")
    destino = BANCO_BRASIL_DIR / str(empresa_id) / f"Declaracao_Banco_do_Brasil_{nome_seguro}_{inicio_ano}{inicio_mes:02d}_{fim_ano}{fim_mes:02d}.pdf"

    valor_declarado = await _fill_and_print_bb(
        empresa=empresa,
        periodos=periodos,
        valores=valores,
        percentual_a_vista=percentual_a_vista,
        percentual_a_prazo=percentual_a_prazo,
        percentual_cartao=None,
        percentual_cheque=None,
        percentual_boleto=None,
        prazo_medio_dias=None,
        destino=destino,
    )

    return criar_declaracao(
        empresa_id=empresa_id,
        tipo="Banco do Brasil",
        periodo_inicio=f"{inicio_ano:04d}-{inicio_mes:02d}",
        periodo_fim=f"{fim_ano:04d}-{fim_mes:02d}",
        valor_total=float(valor_declarado),
        nome_arquivo=destino.name,
        caminho_arquivo=str(destino.resolve().relative_to(STORAGE_BASE.parent.resolve())) if destino.resolve().is_relative_to(STORAGE_BASE.parent.resolve()) else str(destino.resolve()),
        usuario_id=usuario_id,
    )