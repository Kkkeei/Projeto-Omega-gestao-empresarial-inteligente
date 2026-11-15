# Plataforma ÔMEGA
### Gestão empresarial, contábil, fiscal e automação em um só ambiente

<p align="center">
  <strong>Gestão · Integração · Automação · Inteligência operacional</strong>
</p>

<p align="center">
  Plataforma modular em desenvolvimento para centralizar rotinas empresariais, contábeis e fiscais, documentos, certidões e processos automatizados.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/SQLite-database-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
</p>

---

## Visão geral

A **Plataforma ÔMEGA** é um sistema de gestão empresarial com arquitetura modular. O objetivo é reunir, em uma aplicação integrada, informações e rotinas que normalmente ficam distribuídas entre planilhas, portais, documentos e sistemas diferentes.

O projeto separa a interface web, a API, os módulos de negócio, as automações e o serviço local necessário para operações com certificados digitais A3.

> **Estado do projeto:** em desenvolvimento ativo. Os módulos possuem diferentes níveis de implementação; a presença de uma área na interface ou na estrutura do código não significa, por si só, que todas as funcionalidades estejam concluídas ou prontas para produção.

## Áreas funcionais

| Área | Responsabilidade |
|---|---|
| **Empresas** | Cadastro e consulta de dados empresariais e integração cadastral. |
| **Dashboard** | Visão consolidada de informações e atividades. |
| **Certidões** | Consultas, documentos emitidos, situação e histórico. |
| **Certificados digitais** | Gestão de certificados A1/A3 e integração com o serviço local. |
| **Impostos** | Organização de informações e rotinas fiscais. |
| **NFS-e** | Integração e gerenciamento de documentos fiscais de serviço. |
| **Contábil** | Estrutura de apoio às rotinas e lançamentos contábeis. |
| **Faturamento** | Recursos de faturamento e importação/organização de informações. |
| **Dossiê Digital** | Organização documental por empresa, categoria e versão. |
| **Pendências e automações** | Acompanhamento de tarefas e execução de processos automatizados. |

Consulte o [índice da documentação](docs/README.md) para encontrar especificações, guias operacionais, decisões técnicas e registros de evolução.

## Tecnologias e componentes

### Aplicação web
- React 18
- TypeScript
- Vite
- React Router
- Lucide React

### API e serviços
- Python
- FastAPI
- Pydantic
- HTTPX
- SQLite (banco utilizado atualmente)

### Automação e documentos
- Playwright
- PyAutoGUI
- OpenPyXL
- pypdf / PyMuPDF
- ReportLab
- Tesseract / pytesseract

### Serviço local de certificado A3
O diretório `bridge/` contém o OMEGA Bridge, serviço executado no computador do usuário para interagir com cartão/token A3. A chave privada permanece no dispositivo; o Bridge faz a comunicação local necessária para a operação.

## Arquitetura do repositório

O projeto está organizado como um monólito modular, separado em componentes:

```text
Projeto-Omega/
├── backend/          # API, regras de negócio, persistência e testes
├── frontend/         # Aplicação React + TypeScript
├── bridge/           # Serviço local para certificados A3
├── docs/             # Arquitetura, requisitos, guias e histórico técnico
├── dados/            # Dados auxiliares; revisar conteúdo antes de compartilhar
├── scripts/          # Scripts de apoio na raiz
├── docker-compose.yml
├── .gitignore
└── README.md
```

### Fluxo simplificado

```text
Navegador
   │
   ▼
Frontend React / TypeScript
   │ HTTP (API versionada)
   ▼
Backend FastAPI
   ├── Rotas /api/v1
   ├── Módulos de negócio
   ├── Serviços e integrações
   ├── Banco SQLite
   └── Armazenamento de documentos
          ▲
          │ comunicação local quando necessário
     OMEGA Bridge (Windows / A3)
```

As rotas HTTP ficam em `backend/app/api/v1/`; as regras e funcionalidades de cada domínio ficam em `backend/app/modules/` e nos serviços compartilhados. No frontend, as páginas por domínio ficam em `frontend/src/modules/`.

Para a proposta detalhada de organização, consulte [Organização do repositório](docs/ORGANIZACAO_REPOSITORIO.md).

## Executar localmente

### Requisitos

- Python compatível com as dependências do backend
- Node.js e npm
- Git
- (Opcional) Docker e Docker Compose
- (Opcional) Windows, driver do fabricante e leitor/cartão para testar o Bridge A3

### 1. Clonar o projeto

```bash
git clone https://github.com/Kkkeei/Projeto-Omega-gestao-empresarial-inteligente.git
cd Projeto-Omega-gestao-empresarial-inteligente
```

### 2. Configurar o backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Revise o arquivo `.env` antes de iniciar. Defina chaves e credenciais próprias para o ambiente local; não compartilhe o arquivo e nunca coloque segredos no Git.

Inicie a API:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json

### 3. Configurar o frontend

Em outro terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Acesse http://127.0.0.1:5173. Confira `VITE_API_URL` no arquivo `frontend/.env` para apontar para a API em execução.

Para validar a compilação:

```bash
npm run build
```

### 4. Executar com Docker Compose (opcional)

Na raiz do repositório:

```bash
docker compose up --build
```

A configuração atual publica a API na porta 8000 e o frontend na porta 5173. Revise variáveis, volumes e credenciais antes de usar em qualquer ambiente compartilhado ou de produção.

### 5. Executar testes do backend

```bash
cd backend
pytest
```

Os testes de automação que dependem de navegador, sistema operacional, certificado, leitor ou serviços externos podem exigir configuração adicional.

## Documentação

| Documento | Conteúdo |
|---|---|
| [Índice da documentação](docs/README.md) | Catálogo organizado dos documentos existentes. |
| [Arquitetura](docs/ARQUITETURA.md) | Visão arquitetural e separação de camadas. |
| [Organização do repositório](docs/ORGANIZACAO_REPOSITORIO.md) | Estrutura atual, estrutura-alvo e plano de limpeza. |
| [Roadmap](docs/ROADMAP.md) | Etapas e evolução planejada. |
| [Requisitos do MVP](docs/REQUISITOS_MVP.md) | Escopo funcional documentado. |
| [Certificados A1/A3](docs/CERTIFICADOS_A1_A3.md) | Conceitos e integração de certificados. |
| [Guia do Bridge A3](bridge/README.md) | Instalação, operação e segurança do serviço local. |

## Segurança e dados

- Não versionar arquivos `.env`, tokens, senhas, chaves privadas, certificados A1, PINs ou credenciais.
- Não versionar banco de dados local, documentos de clientes, PDFs fiscais, backups ou arquivos de armazenamento.
- Usar dados fictícios ou anonimizados em exemplos, testes e capturas de tela.
- O Bridge A3 deve permanecer local, não deve ser exposto publicamente e deve aceitar somente origens confiáveis.
- Antes de publicar ou manter o repositório público, revisar arquivos de `dados/`, anexos e histórico do Git para identificar informações reais de clientes.

Consulte a [Política de segurança](SECURITY.md) para orientações de reporte e proteção de dados.

## Diretrizes de contribuição

1. Criar uma branch específica para cada funcionalidade ou correção.
2. Evitar desenvolver diretamente na `main`.
3. Manter alterações de frontend, backend e contratos de API coerentes.
4. Adicionar ou atualizar testes quando houver mudança de comportamento.
5. Atualizar a documentação do módulo afetado.
6. Abrir Pull Request com resumo, testes executados e riscos conhecidos.
7. Não incluir arquivos temporários, backups locais ou dados reais de clientes.

Sugestão de nomes de branch: `feat/nome-da-funcionalidade`, `fix/descricao-do-problema`, `docs/assunto`.

## Status

**Projeto em desenvolvimento.** Este repositório representa o código-fonte e a documentação de trabalho da Plataforma ÔMEGA. Não deve ser considerado uma distribuição pronta para produção sem homologação funcional, revisão de segurança, política de backup e configuração do ambiente de implantação.

---

<p align="center">
  <strong>PLATAFORMA ÔMEGA</strong><br>
  Gestão empresarial com integração e automação.
</p>
