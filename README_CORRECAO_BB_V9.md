# Correção Faturamento / Banco do Brasil — V9

Esta versão corrige a tela inicial de geração de declaração:

- Banco do Brasil aparece como **4º card**, lado a lado com Últimos 12 meses, Anual e Personalizado no desktop.
- Modal inicial foi ampliado para manter os 4 cards visíveis.
- Responsividade: 4 colunas no desktop, 2 em telas médias, 1 no celular.
- A opção visual "Competência de controle" não faz parte desta versão do componente principal.
- O card Banco do Brasil continua abrindo o fluxo automático já implementado.

Arquivos principais:
- frontend/src/modules/faturamento/FaturamentoPage.tsx
- frontend/src/modules/faturamento/Faturamento.css

Não substitua omega.db nem storage.
