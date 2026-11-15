# Auditoria de organização do repositório — 2026-11-15

## Escopo e regra de preservação

Auditoria realizada sobre o repositório público `Kkkeei/Projeto-Omega-gestao-empresarial-inteligente`. O trabalho preserva o banco SQLite operacional, certificados, arquivos `.env`, documentos fiscais e conteúdo de `storage/`. Nenhum dado operacional foi alterado.

## Estado da branch principal

- Branch padrão: `main`.
- HEAD verificado: `9cd15c01dd67e364a2c07e64876200da000bdd0f`.
- A branch contém documentação principal, índice de documentação, guia de organização, política de segurança e diretrizes de contribuição.
- A implementação Contábil está presente na `main`, incluindo backend, frontend e contrato/documentação correspondentes.
- A árvore versionada ainda contém artefatos que precisam de revisão, incluindo `backend/.coverage`, `frontend/tsconfig.app.tsbuildinfo`, arquivos de backup e `dados/CADASTRO.xlsx`.

## Candidata de consolidação funcional

Branch: `fix/omega-ci-candidate`

Commit validado: `20760909f99cba6349a22367111481498fafa45b`

Pull Request: https://github.com/Kkkeei/Projeto-Omega-gestao-empresarial-inteligente/pull/6

CI: https://github.com/Kkkeei/Projeto-Omega-gestao-empresarial-inteligente/actions/runs/43753872485

Resultado do CI no commit acima:
- Frontend TypeScript/Vite: aprovado.
- Compilação dos módulos Python: aprovada.
- Testes do backend: aprovados.
- Testes do Bridge: aprovados.

Correções feitas nessa branch:
1. Removida a chamada a `openRegisterModal` inexistente em `EmpresaImpostosPage.tsx`. O fluxo de anexar guia pertence à rota de detalhe mensal do tributo.
2. Atualizados os testes de `_adn_url` para refletir o contrato atual da integração ADN: consulta PJ inclui `cnpjConsulta`; consulta PF não inclui esse parâmetro.

## Divergência entre branches

A candidata deriva de `feat/omega-finalizacao-modulos` e ainda não está pronta para integrar diretamente à `main`.

Na comparação registrada:
- Candidata: 198 commits à frente e 36 commits atrás da `main`.
- O GitHub marcou o Pull Request #6 como `dirty`, indicando conflitos de integração.
- Existem alterações concorrentes em:
  - `README.md`
  - `backend/app/api/v1/routes.py`
  - `backend/app/db/database.py`
  - `frontend/src/app/App.tsx`
  - `frontend/src/components/layout/Layout.tsx`
  - `frontend/src/modules/impostos/ImpostoMensalPage.tsx`
  - `frontend/src/modules/nfse/NfsePage.tsx`

A `main` contém a fundação do módulo Contábil que não pode ser descartada. A candidata contém mudanças de NFS-e, DCTFWeb, Certidões, Certificados, autenticação e Impostos. A consolidação exige resolver os arquivos concorrentes preservando ambos os conjuntos de funcionalidades e repetir o CI sobre o resultado integrado.

**Não mesclar o PR #6 enquanto o estado de conflito permanecer.** A aprovação do CI da branch candidata não equivale à validação de uma versão integrada com a `main`.

## Pendências de segurança e higiene

1. Verificar se `dados/CADASTRO.xlsx` contém dados reais de empresas ou pessoas. O arquivo consta no repositório público. A regra no `.gitignore` não o remove do histórico nem deixa de versionar um arquivo já rastreado.
2. Revisar `backend/.coverage` e `frontend/tsconfig.app.tsbuildinfo`; são artefatos gerados e não fontes do sistema.
3. Inventariar os backups `.bak` e `.backup_*` antes de removê-los. Não apagar sem conferir conteúdo e referências.
4. Inventariar os diários de bordo com nomes/codificação inconsistentes. Preservar conteúdo e histórico antes de qualquer renomeação.
5. Avaliar a duplicidade dos pacotes ZIP do Bridge A3 em `frontend/public/` e `frontend/public/omega-a3/`, verificando referências antes de retirar uma cópia.

## Próxima sequência recomendada

1. Resolver a integração entre a candidata funcional e a `main`, preservando o módulo Contábil.
2. Executar novamente todo o CI no commit integrado.
3. Homologar os fluxos de NFS-e, Certidões, Certificados A1/A3, DCTFWeb, Impostos e Contábil.
4. Revisar dados potencialmente sensíveis e o histórico Git antes de qualquer limpeza destrutiva.
5. Somente então atualizar a `main` com a versão consolidada.
