# Organização do repositório ÔMEGA

Este documento descreve a organização encontrada no repositório e propõe uma estrutura-alvo. A proposta é evolutiva: **não mover diretórios de código em massa sem revisar imports, rotas, Docker, scripts e caminhos de armazenamento**.

## 1. Estrutura atual observada

```text
/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Endpoints HTTP agrupados por domínio
│   │   ├── core/             # Configuração e componentes centrais
│   │   ├── db/               # Conexão e inicialização do banco
│   │   ├── models/           # Modelos compartilhados
│   │   ├── modules/          # Domínios e regras de negócio
│   │   ├── schemas/          # Schemas compartilhados
│   │   └── services/         # Serviços transversais e integrações
│   ├── assets/               # Recursos usados pelo backend
│   ├── scripts/              # Scripts administrativos/importação
│   ├── tests/                # Testes automatizados
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── public/               # Arquivos públicos e recursos estáticos
│   └── src/
│       ├── app/              # Composição principal da aplicação
│       ├── auth/             # Contexto e proteção de autenticação
│       ├── components/       # Componentes compartilhados
│       └── modules/          # Telas por domínio
├── bridge/                   # Serviço local Windows para certificado A3
├── dados/                    # Dados auxiliares (revisar sensibilidade)
├── docs/                     # Documentação técnica e histórica
├── scripts/                  # Scripts de apoio na raiz
├── docker-compose.yml
├── .gitignore
└── README.md
```

## 2. Estrutura-alvo recomendada

A estrutura abaixo é uma organização desejada para evoluir aos poucos. Ela não significa que todos esses diretórios já existam ou que todos os módulos estejam concluídos.

```text
/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
├── backend/
│   ├── app/
│   │   ├── api/v1/                 # Apenas camada HTTP e composição de rotas
│   │   ├── core/                   # Configuração, segurança, logging
│   │   ├── db/                     # Conexão, sessão e migrations (quando adotadas)
│   │   ├── modules/
│   │   │   ├── empresas/
│   │   │   ├── certidoes/
│   │   │   ├── certificados/
│   │   │   ├── impostos/
│   │   │   ├── nfse/
│   │   │   ├── contabil/
│   │   │   ├── faturamento/
│   │   │   ├── documentacao/
│   │   │   └── pendencias/
│   │   ├── integrations/           # Clientes/adaptadores de serviços externos
│   │   └── shared/                 # Utilitários realmente transversais
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── scripts/
│   ├── assets/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── public/
│   └── src/
│       ├── app/                    # Router, providers e bootstrap
│       ├── components/
│       │   ├── layout/
│       │   └── ui/
│       ├── modules/
│       │   └── <dominio>/
│       │       ├── components/
│       │       ├── pages/
│       │       ├── services/
│       │       ├── types/
│       │       └── index.ts
│       ├── services/               # Cliente HTTP e serviços compartilhados
│       ├── hooks/
│       ├── types/
│       └── styles/
├── bridge/
│   ├── app.py
│   ├── scripts/
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
├── docs/
│   ├── architecture/
│   ├── modules/
│   ├── operations/
│   ├── decisions/
│   ├── history/
│   └── README.md
├── scripts/                        # Tarefas de manutenção do repositório
├── storage/                        # Apenas local/volume; não versionar
├── .env.example                    # Somente se houver configuração de raiz
├── .gitignore
├── docker-compose.yml
├── CONTRIBUTING.md
├── SECURITY.md
└── README.md
```

## 3. Regras para manter a organização

### Backend
- `api/v1/` deve receber e validar requisições, chamar os serviços do domínio e devolver respostas HTTP.
- `modules/<dominio>/` deve concentrar regras, schemas, repositórios e serviços específicos daquele domínio.
- `core/` fica reservado a configurações e componentes centrais, não a regras de negócio.
- `services/` na raiz de `app` deve conter somente serviços compartilhados por vários domínios. Ao tocar um módulo, avaliar se seu serviço pertence ao próprio módulo.
- Não duplicar modelos ou schemas: definir claramente o que é compartilhado e o que pertence ao domínio.
- Preservar separação entre **Dossiê Digital/Documentação** e **Contábil**. São áreas distintas.

### Frontend
- `modules/<dominio>/` concentra páginas e componentes próprios da funcionalidade.
- Componentes genéricos ficam em `components/ui` ou `components/layout`.
- Chamadas HTTP devem usar um cliente centralizado; evitar URLs da API espalhadas pelos componentes.
- Tipos compartilhados devem ficar em local comum; tipos exclusivos ficam junto ao módulo.

### Bridge A3
- Continuar como componente separado do backend e do frontend: ele depende do computador do usuário, leitor/cartão e middleware do fabricante.
- Não mover o Bridge para dentro do backend nem tentar executá-lo no servidor.
- Manter instruções específicas de Windows, instalação, token, origens permitidas e driver.

### Documentação
- `docs/README.md` é o índice oficial.
- Documentos de arquitetura e decisões devem ser mantidos atualizados quando a estrutura mudar.
- Relatórios pontuais e diários de bordo devem ficar em histórico, com nomes padronizados e datas ISO (`AAAA-MM-DD`).
- Não usar o README principal como diário de desenvolvimento.

## 4. Organização sugerida para `docs/`

| Pasta | Conteúdo |
|---|---|
| `architecture/` | Visão geral, camadas, banco, integrações e diagramas. |
| `modules/` | Contratos, fluxos e regras de cada módulo. |
| `operations/` | Instalação, configuração, backup, deploy e suporte. |
| `decisions/` | ADRs: decisões técnicas e motivos. |
| `history/` | Auditorias, entregas datadas e diários de bordo relevantes. |
| `sql/` | Scripts SQL versionados e revisados. |

A migração dos arquivos existentes deve ser feita por grupos, corrigindo links relativos e mantendo um índice de documentos antigos.

## 5. Limpeza prioritária identificada

Na árvore atual do GitHub foram observados itens que merecem revisão:

1. **Backups dentro do código:** há arquivos `.bak` e `.backup_*` ao lado de módulos ativos. Confirmar que não são usados; depois removê-los do repositório e manter backups fora do Git.
2. **Artefatos de teste:** `backend/.coverage` está versionado e deve ser gerado localmente/na CI, não mantido como fonte.
3. **Cache TypeScript:** `frontend/tsconfig.tsbuildinfo` está versionado; avaliar removê-lo e ignorar `*.tsbuildinfo`.
4. **Diários com codificação inconsistente:** existem nomes de arquivos de diário de bordo com caracteres corrompidos/duplicados. Fazer inventário, preservar conteúdo e consolidar antes de renomear ou excluir.
5. **Dados auxiliares:** `dados/CADASTRO.xlsx` está no repositório público. Verificar imediatamente se contém nomes, CNPJ, saldos, dados de clientes ou outras informações reais. Se contiver, remover do Git, substituir por exemplo fictício e avaliar o histórico Git; apagar o arquivo atual não apaga versões anteriores.
6. **ZIP do Bridge duplicado:** há pacote do Bridge em mais de um caminho público dentro do frontend. Definir um local oficial para distribuição e manter apenas uma cópia versionada, após conferir os links usados pela interface.
7. **Documentação desatualizada:** revisar READMEs de backend/frontend para que não descrevam decisões antigas incompatíveis com a implementação atual.

## 6. Plano seguro de reorganização

### Etapa 1 — Documentação e segurança
- Atualizar README principal e criar índice de documentação.
- Auditar `dados/`, arquivos públicos, anexos e histórico para remover dados reais/segredos.
- Completar `.gitignore` para caches, coberturas, temporários e backups.

### Etapa 2 — Higienização sem alterar arquitetura
- Remover artefatos gerados e backups somente após confirmar que não são necessários.
- Padronizar nomes/codificação dos documentos históricos.
- Consolidar pacotes duplicados do Bridge, ajustando referências.

### Etapa 3 — Padronização dos módulos
- Definir um padrão de módulo no backend e frontend.
- Migrar um domínio por vez, com testes e revisão de imports.
- Não misturar refatoração estrutural com mudanças grandes de regra de negócio.

### Etapa 4 — Qualidade e entrega
- Separar testes unitários, integração e ponta a ponta progressivamente.
- Criar CI para build do frontend e testes do backend.
- Criar templates de Pull Request e Issues.
- Documentar processo de release, backup e implantação.

## 7. Convenção de commits e branches

Branches:
- `feat/<assunto>` — funcionalidade
- `fix/<assunto>` — correção
- `refactor/<assunto>` — refatoração
- `docs/<assunto>` — documentação
- `chore/<assunto>` — manutenção

Commits curtos e objetivos, preferencialmente no padrão:
- `feat(contabil): adiciona estrutura de lançamentos`
- `fix(nfse): corrige sincronização de documentos`
- `docs(repo): organiza documentação principal`

## 8. Critério para considerar a reorganização concluída

- README e índice apontam para documentos existentes.
- Nenhum segredo, certificado, banco local ou dado real de cliente está versionado.
- Não existem cópias de backup misturadas ao código ativo.
- Backend e frontend compilam/testam após cada migração.
- O Bridge A3 continua instalável e executável no computador do usuário.
- As mudanças de estrutura possuem commits pequenos e rastreáveis.
