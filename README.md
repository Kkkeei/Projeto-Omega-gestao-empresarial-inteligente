# PATCH FATURAMENTO BB V12

Patch cirúrgico: preserva a página existente e altera somente o necessário.

- adiciona o 4º card Banco do Brasil;
- mantém percentuais editáveis (20/80 por padrão);
- remove visualmente o seletor "Competência de controle" da página principal;
- não depende de obterConfigBancoBrasil/salvarConfigBancoBrasil;
- reaproveita gerarDeclaracaoBancoBrasil já existente.

Aplicação:
`bash APLICAR_PATCH.sh ~/Documentos/Projeto`
