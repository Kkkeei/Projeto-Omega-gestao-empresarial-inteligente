# ÔMEGA — Implementação do Módulo de Impostos

**Versão:** conclusão técnica da área de Impostos
**Base funcional:** `ABA IMPOSTOS(5).pdf`

## Escopo concluído

A implementação foi revisada e fechada considerando o fluxo funcional especificado para:

```text
Cadastro global de tributos
        ↓
Configuração do tributo na empresa
        ↓
Competência
        ↓
Registro mensal
        ↓
Guia / Credor / Sem movimentação
        ↓
Leitura e conferência
        ↓
Pagamento
        ↓
Histórico
        ↓
Notificações
        ↓
Relatório / PDF
```

## Ajustes realizados

### Configuração e vigência

- histórico de configurações preservado;
- competência encerrada continua disponível no histórico;
- configuração encerrada deixa de aparecer nas competências posteriores;
- prevenção de sobreposição de vigências;
- tributo inativo não pode ser usado para novos vínculos.

### Registro mensal

- situações válidas controladas no backend;
- um único registro por Empresa + Imposto + Competência;
- edição mantém histórico;
- `Pendente` não é tratado como valor zero;
- `Credor` e `Sem movimentação` permanecem distintos.

### Guia

- validação de vínculo do documento com a competência correta;
- somente rascunho pode ser confirmado;
- histórico de documentos confirmados preservado;
- correção/substituição da guia mantém documentos anteriores;
- informações de competência, valor, vencimento, código, CNPJ, pagamento e período de apuração permanecem armazenadas.

### Pagamento

- somente registros `A_VENCER` ou `EM_ATRASO` podem ser marcados como pagos pelo fluxo de pagamento;
- registro pago precisa ter data de pagamento;
- a alteração é registrada no histórico.

### Notificações

- configurações de cliente e contabilidade persistidas;
- eventos de guia enviada, proximidade do vencimento e vencimento programados conforme configuração;
- pagamento identificado impede a programação dos eventos de vencimento;
- guia sem data de vencimento ainda gera o evento de guia enviada;
- prevenção de duplicidade de eventos;
- reenvio preserva o histórico do evento original.

### Relatórios

- relatório considera os registros existentes;
- `Pendente`, `Credor` e `Sem movimentação` são diferenciados;
- colunas de tributos são dinâmicas;
- totais não contam competências pendentes como valor recolhido;
- PDF gerado a partir da mesma prévia.

### Interface

- status exibidos com textos amigáveis;
- fluxo de alteração do registro mensal disponível após a primeira apuração;
- tela de conferência permite editar também o período de apuração;
- documento atual possui visualização e download;
- documentos confirmados anteriores ficam acessíveis no histórico.

## Validação técnica

### Testes específicos de Impostos

```text
backend/tests/test_impostos_completo.py

7 passed
```

A suíte cobre:

- vigência e histórico;
- unicidade do registro mensal;
- validação de status;
- OCR/extratação e confirmação da guia;
- histórico de documentos;
- notificações;
- regras de pagamento;
- relatório e PDF;
- distinção entre Pendente, Credor e Sem movimentação.

### Backend

```text
python -m compileall backend
```

Resultado: **OK**.

### Frontend

Os arquivos TS/TSX alterados foram analisados com o compilador TypeScript disponível no ambiente para validação de sintaxe.

Resultado: **syntax OK**.

O build completo via `npm run build` não foi homologado neste ambiente porque a instalação das dependências do frontend não foi concluída por timeout do gerenciador npm.

## Observação sobre a suíte completa do projeto

Na execução da suíte completa do backend, foram identificadas **3 falhas preexistentes relacionadas ao módulo de Faturamento/Banco do Brasil** (`test_faturamento_periodo.py`).

Resultado observado:

```text
23 passed
3 failed
```

Essas falhas não pertencem ao módulo de Impostos e não foram alteradas nesta implementação.

## Critério de conclusão

O módulo de Impostos deve ser considerado funcionalmente concluído quando a homologação real no ambiente de uso confirmar o fluxo:

```text
Empresa
 ↓
Imposto
 ↓
Competência
 ↓
Guia / Credor / Sem movimentação
 ↓
Conferência
 ↓
Registro
 ↓
Pagamento
 ↓
Notificação
 ↓
Histórico
 ↓
Relatório
 ↓
PDF
```

Nenhuma alteração desta implementação substitui o banco operacional `backend/omega.db`.
