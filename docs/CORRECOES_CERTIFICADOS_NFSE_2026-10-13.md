# Correções — Certificados e NFS-e

Data: 13/10/2026

## Certificados

- A validade A3 é interpretada preservando horário e fuso informados pelo OMEGA Bridge. Valores legados no formato `YYYY-MM-DD` são considerados válidos até o fim daquele dia em UTC.
- A3 PF expirado é salvo com status `EXPIRADO` e `apto_para_uso = false`, em vez de ser marcado como utilizável.
- O formulário A3 não exige PIN para cadastrar um certificado já vencido; para certificados vigentes o PIN é enviado somente ao Bridge para a assinatura de teste e não é enviado para a API de cadastro.
- A tela avalia vencimento por instante real, além do status persistido.
- Ao selecionar arquivo PFX/P12 inválido ou acima de 10 MB, o estado anterior é limpo para impedir que um arquivo previamente selecionado seja enviado por engano.
- O formulário A3 continua usando os metadados detectados pelo Bridge e exige thumbprint SHA-256 e validade.

## NFS-e

- A extração reconhece nomes de campos JSON independentemente de maiúsculas/minúsculas e suporta aliases adicionais de payload, incluindo `ArquivoXml`, `Schema` e `NSU`.
- Um lote não vazio que não possui campo XML reconhecido é reportado como `ERRO_LAYOUT`; o cursor NSU não avança silenciosamente.
- Falhas ao persistir documentos não são mais ignoradas por linha. A operação reporta erro, tenta reverter a transação e remove XMLs criados pela tentativa que falhou.
- Documentos sem NSU e sem chave de acesso não são gravados, pois não há identidade estável para deduplicação.
- `ultimo_nsu` e `max_nsu` são monotônicos: uma resposta antiga não regride os cursores já persistidos.
- A importação A3 preserva o cursor quando o lote tem estrutura desconhecida ou ocorre falha de persistência.
- O parser suporta XML com namespaces, conteúdo XML simples, Base64 e GZIP/Base64, além de extrair data e valor pelos elementos compatíveis identificados nos testes.

## Verificações executadas

- Backend: 75 testes passaram.
- OMEGA Bridge: 3 testes passaram.
- `compileall` de `backend/app` e `bridge`: passou.
- Sintaxe TS/TSX dos arquivos alterados (`CertificadosPage.tsx`, `NfsePage.tsx`, `certificados.ts`, `nfse.ts`): passou por `transpileModule` do TypeScript.
- Integridade do ZIP final: verificada separadamente.

## Limitações que permanecem

- O build completo Vite/TypeScript (`npm run build`) não foi executado: as dependências npm não puderam ser instaladas integralmente neste ambiente. A verificação TS/TSX mencionada acima confirma parsing/transpilação sintática, não substitui o typecheck completo.
- Não houve validação contra o ADN real com certificado de contribuinte.
- Não houve teste físico de cartão/leitor A3 e middleware no Windows.
- A emissão, cancelamento e substituição de NFS-e municipal continuam dependentes da identificação e implementação do provedor/padrão fiscal aplicável.
- A revisão ampla de segurança/autorização permanece para a etapa do MVP, conforme o escopo de trabalho definido.

## Atualização

Copie os arquivos de código do pacote para a pasta de projeto atual. Preserve `backend/.env`, `backend/omega.db` e `storage`. Não substitua esses itens pelos conteúdos do pacote.
