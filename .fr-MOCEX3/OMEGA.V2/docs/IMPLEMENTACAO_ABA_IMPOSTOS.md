# Implementação — Aba Impostos

Base: `ABA IMPOSTOS(4).pdf`.

## Escopo implementado

- Visão geral de empresas por regime, pesquisa e situação.
- Indicador `informados/total` e prioridade `Vencido > Vencendo > Pendente > Em dia`.
- Cadastro mestre de tributos, edição e inativação sem exclusão física.
- Configuração de tributos por empresa com competência inicial/final e preservação de histórico.
- Painel mensal por competência e esfera.
- Registro mensal como guia, credor ou sem movimentação.
- Upload PDF/JPG/PNG até 10 MB, leitura de texto/OCR e etapa de conferência.
- Edição dos dados extraídos antes da confirmação.
- Armazenamento do documento, dados extraídos, observações e histórico.
- Marcação de pagamento.
- Configuração persistente de notificações para cliente/contabilidade.
- Eventos de guia registrada, proximidade do vencimento, vencimento e alerta interno de imposto vencido.
- Relatório por empresa/período, prévia e PDF, diferenciando Pendente, Credor e Sem movimentação.
- Rotas frontend e backend integradas.

## Ajustes feitos nesta revisão

1. Status da tela individual passou a usar os rótulos funcionais da especificação (`Pago`, `A vencer`, `A pagar`, `Em atraso`, `Aguardando informação`, etc.), em vez dos códigos internos.
2. Conferência da guia passou a exibir também o período de apuração extraído e permitir sua correção.
3. Datas extraídas são exibidas em formato brasileiro sem perder o formato ISO utilizado internamente na edição.
4. A mensagem padrão de comunicação passou a incluir o nome do tributo.
5. O botão `Voltar` da conferência retorna corretamente ao modal de registro.
6. A pesquisa da visão geral aceita CNPJ com ou sem pontuação.

## Validação

- `python -m compileall -q app` — OK.
- Smoke test isolado do módulo Impostos — OK.
- Parser TypeScript/TSX dos arquivos do módulo — OK.
- A suíte geral existente possui 3 falhas pré-existentes em testes do módulo Faturamento/Banco do Brasil, fora do escopo desta implementação.
- O build completo do frontend não pôde ser executado neste ambiente porque o `node_modules` distribuído no ZIP está sem os arquivos dos pacotes; a tentativa de instalação offline não encontrou os pacotes no cache local.
