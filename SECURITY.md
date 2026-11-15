# Política de segurança — Plataforma ÔMEGA

## Reportar vulnerabilidades

Não publique detalhes de vulnerabilidades, credenciais ou dados de clientes em Issues públicas. Para reportar um problema, entre em contato com o mantenedor do repositório por um canal privado.

## Informações que nunca devem ser versionadas

- Arquivos `.env` reais, tokens, senhas, chaves JWT e chaves de criptografia.
- Certificados digitais A1/A3, arquivos PFX/P12, PINs e chaves privadas.
- Bancos de dados locais, backups e dumps com dados reais.
- XMLs, PDFs, planilhas, procurações e documentos fiscais de clientes.
- Logs, screenshots e relatórios que exponham dados pessoais ou empresariais.

Use apenas dados sintéticos ou anonimizados em exemplos e testes.

## Certificados e OMEGA Bridge

O Bridge A3 deve executar localmente no computador do usuário, aceitar somente origens confiáveis e não ser exposto à internet. A chave privada deve permanecer no cartão/token. Não registre PINs nem material criptográfico em logs.

## Antes de publicar

Revise os arquivos adicionados ao commit e o histórico do Git. Remover um arquivo de um commit atual não apaga versões anteriores. Se um segredo tiver sido publicado, revogue/rotacione-o imediatamente e trate a limpeza do histórico como etapa separada.
