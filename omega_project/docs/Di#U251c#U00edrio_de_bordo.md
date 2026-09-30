DIÁRIO DE BORDO — DESENVOLVIMENTO DA PLATAFORMA ÔMEGA
Página 01 — Identificação do Projeto
PLATAFORMA ÔMEGA

Sistema de Gestão Empresarial

Tipo de projeto: Desenvolvimento de software
Arquitetura: Monólito modular
Frontend: React + TypeScript + Vite
Backend: Python + FastAPI
Banco de dados: SQLite
Persistência: SQLAlchemy
Migrações: Alembic

Objetivo

Desenvolver a Plataforma ÔMEGA como um Dossiê Empresarial Digital Permanente, centralizando as informações das empresas atendidas pelo escritório e permitindo o acompanhamento de:

Cadastro empresarial;
Situação cadastral;
Certidões;
Pendências;
Documentos;
Automações;
Histórico;
Auditoria;
Evolução da situação empresarial.

O princípio fundamental do sistema será:

“A situação atual é importante, mas o histórico é permanente.”

Página 02 — Origem do Projeto

O desenvolvimento da Plataforma ÔMEGA parte da análise dos documentos de requisitos empresariais e do Documento Mestre de Desenvolvimento.

A decisão tomada nesta etapa foi reconstruir a plataforma do zero, utilizando os documentos existentes como referência funcional e arquitetural.

O objetivo não é simplesmente reproduzir uma interface existente, mas transformar os requisitos documentados em uma aplicação estruturada, modular e preparada para evolução.

Os documentos definem como áreas iniciais:

Dashboard;
Empresas;
Certidões;
Automação.

Outros módulos serão incorporados posteriormente conforme o roadmap do projeto.

Diretriz

O sistema deverá evitar:

funcionalidades inventadas;
endpoints inexistentes;
dados falsamente apresentados como reais;
exclusão de histórico;
sobrescrita de documentos;
alterações acidentais do regime tributário;
exclusão de empresas.
Página 03 — Decisão Arquitetural
Arquitetura escolhida

Foi adotada uma arquitetura de monólito modular.

A escolha busca manter o sistema organizado sem introduzir, neste momento, a complexidade de uma arquitetura de microsserviços.

A estrutura conceitual será:

┌─────────────────────────────┐
│          FRONTEND           │
│      React / TypeScript     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│            API              │
│          FastAPI            │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      REGRAS DE NEGÓCIO      │
│          SERVICES           │
└──────────────┬──────────────┘
               │
       ┌───────┴────────┐
       ▼                ▼
┌─────────────┐  ┌─────────────┐
│INTEGRAÇÕES  │  │ PERSISTÊNCIA│
│             │  │             │
│ BrasilAPI   │  │ SQLAlchemy  │
│ SEFAZ       │  │ SQLite      │
│ Playwright  │  │             │
└─────────────┘  └─────────────┘

Essa separação foi definida para que uma alteração em uma integração externa não obrigue a reconstrução do restante do sistema. O Documento Mestre estabelece essa separação entre apresentação, API, regras de negócio, integrações/robôs e persistência.

Página 04 — Primeira Decisão do Backend
Banco de dados

Foi decidido utilizar SQLite nesta etapa de desenvolvimento.

Motivos
facilidade de instalação;
não exige servidor de banco separado;
adequado para desenvolvimento inicial;
facilita testes;
permite desenvolver toda a estrutura relacional antes da migração para outro banco, caso necessária.
Configuração inicial
DATABASE_URL=sqlite:///./omega.db

O banco será acessado através do SQLAlchemy.

Regra

O código da aplicação não deverá depender diretamente de comandos específicos do SQLite sempre que isso puder ser evitado.

A camada de persistência deverá ficar isolada para permitir evolução futura.

Página 05 — Primeiras Entidades

Antes de criar dezenas de endpoints, foi definida a necessidade de estruturar as principais entidades do sistema.

Entidades principais
USUÁRIOS
PERFIS
PERMISSÕES

EMPRESAS
EMPRESA_HISTÓRICOS
SÓCIOS

CERTIDÕES
CERTIDÃO_HISTÓRICOS
PENDÊNCIAS

AUTOMAÇÕES
AUTOMAÇÃO_EXECUÇÕES

DOCUMENTOS
DOCUMENTO_VERSÕES

AUDITORIA
INTEGRAÇÕES

A definição está alinhada ao dicionário de dados do Documento Mestre, que estabelece Empresa, Certidão, Pendência, Automação, Execução, Documento e Auditoria como entidades principais.

Página 06 — Primeiro Módulo: Empresas

Foi definido que o primeiro módulo efetivamente construído será EMPRESAS.

Motivo:

A empresa é a entidade central da plataforma.

A relação conceitual será:

EMPRESA
   │
   ├── Dados cadastrais
   ├── Endereço
   ├── Atividades
   ├── Escritório
   ├── Sócios
   │
   ├── Certidões
   │      └── Histórico
   │
   ├── Pendências
   │
   ├── Documentos
   │      └── Versões
   │
   ├── Automações
   │      └── Execuções
   │
   └── Histórico

O cadastro empresarial deve contemplar identificação, atividade, endereço, contato, informações do escritório e informações de controle/sincronização.

Página 07 — Cadastro Rápido

Foi registrada a regra de negócio do Cadastro Rápido.

Informações fornecidas pelo usuário
CNPJ
Inscrição Estadual
Inscrição Municipal
E-mail
NIRE
Regime Tributário
Data de Entrada

Após o fornecimento do CNPJ, o sistema deverá buscar os dados cadastrais disponíveis:

Razão Social
Nome Fantasia
Endereço
Data de Abertura
CNAE Principal
Capital Social

O requisito também estabelece que os dados retornados devem ser apresentados para revisão antes do salvamento definitivo.

Fluxo definido
Usuário
   ↓
Informa CNPJ
   ↓
Buscar dados cadastrais
   ↓
Integração CNPJ
   ↓
Dados encontrados
   ↓
Usuário revisa
   ↓
Salvar empresa
   ↓
Registrar origem + histórico
Página 08 — Proteção do Regime Tributário

Foi registrada como regra crítica de negócio a proteção do regime tributário.

Durante uma alteração cadastral normal:

Regime Tributário
[ Simples Nacional ] 🔒

O usuário não poderá simplesmente modificar o regime.

Para iniciar uma alteração, deverá marcar:

☐ Alterar regime tributário

Somente então serão liberados:

Novo regime
Mês da alteração
Ano da alteração

Essa regra deverá ser implementada no backend, e não apenas na interface.

O motivo é simples:

Se a proteção existir somente no frontend, uma requisição direta à API poderia alterar o regime sem passar pela regra de negócio.

Os requisitos determinam explicitamente esse fluxo protegido.

Página 09 — Inativação da Empresa

Outra regra registrada:

Empresa nunca deve ser excluída para representar sua saída do escritório.

O fluxo será:

Inativar empresa
       ↓
Solicitar data de saída
       ↓
Confirmar
       ↓
Empresa = INATIVA
       ↓
Registrar data de saída
       ↓
Registrar histórico
       ↓
Preservar todos os dados anteriores

A data de saída será obrigatória.

O requisito determina expressamente que a empresa não deve ser excluída e que a inativação deve solicitar a data de saída.

Página 10 — Princípio de Histórico

Foi definida uma regra estrutural para o banco:

Não sobrescrever informações históricas importantes.

Exemplo:

Empresa
   │
   ├── Cadastro inicial
   │
   ├── Alteração cadastral
   │
   ├── Alteração de regime
   │
   ├── Inativação
   │
   └── Reativação

Cada alteração relevante deverá permitir identificar:

O QUE aconteceu
QUANDO aconteceu
QUEM realizou
QUAL era o valor anterior
QUAL passou a ser o novo valor

O mesmo princípio será utilizado para certidões e documentos.

Para certidões, uma nova consulta deverá gerar um novo registro histórico, em vez de simplesmente substituir o documento anterior. O Documento Mestre estabelece expressamente que certidões não devem ter seu histórico sobrescrito.

📌 Registro de encerramento da primeira fase

Decisões tomadas:

 Projeto reconstruído do zero;
 Requisitos documentados como fonte funcional;
 Arquitetura de monólito modular;
 FastAPI definido para API;
 SQLite definido para primeira implementação;
 Empresas definido como primeiro módulo;
 Histórico permanente definido como princípio estrutural;
 Regime tributário protegido;
 Inativação sem exclusão;
 Cadastro rápido definido;
 Integrações isoladas da regra de negócio.
Próxima entrada do Diário de Bordo

“Modelagem do banco de dados — tabela EMPRESAS”

