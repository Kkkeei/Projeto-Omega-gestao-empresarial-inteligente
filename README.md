# ◈ PLATAFORMA ÔMEGA
### SISTEMA INTEGRADO DE GESTÃO EMPRESARIAL

<p align="center">
  <strong>Gestão • Integração • Automação</strong>
</p>

<p align="center">
  Uma plataforma desenvolvida para centralizar processos empresariais, contábeis, fiscais e administrativos em um único ambiente tecnológico.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-Backend-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-API-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/TypeScript-Linguagem-3178C6?style=for-the-badge&logo=typescript&logoColor=white" />
</p>

---

## ◈ SOBRE O PROJETO

A **Plataforma ÔMEGA** é um sistema de gestão empresarial concebido para integrar diferentes áreas operacionais em uma estrutura única, organizada e modular.

Seu desenvolvimento busca reduzir a fragmentação de processos, facilitar o gerenciamento de informações e automatizar atividades que fazem parte da rotina empresarial.

A arquitetura foi estruturada para permitir a expansão independente dos módulos, mantendo a integração entre as funcionalidades e a consistência dos dados.

---

## ◈ MÓDULOS DA PLATAFORMA

| Módulo | Descrição |
|:---|:---|
| **Contábil** | Gestão de documentos e rotinas contábeis. |
| **Fiscal** | Organização e suporte às atividades fiscais. |
| **NFS-e** | Consulta, integração e gerenciamento de documentos fiscais de serviços. |
| **Certificados Digitais** | Gerenciamento de certificados A1 e A3. |
| **Dossiê Digital** | Centralização e organização documental. |
| **Automações** | Execução de processos automatizados e integrações. |
| **Gestão Empresarial** | Centralização de informações e processos das empresas. |

<sub>Os módulos e respectivos recursos encontram-se em evolução contínua.</sub>

---

## ◈ TECNOLOGIAS

**Backend**
- Python
- FastAPI

**Frontend**
- React
- TypeScript
- Vite

**Banco de dados**
- SQLite

**Automação e integração**
- Playwright
- APIs e serviços externos

---

## ◈ ARQUITETURA

A aplicação utiliza uma estrutura separada entre frontend e backend, com comunicação por meio de API.

```text
OMEGA.V2/
│
├── backend/
│   ├── app/
│   │   └── modules/
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
└── README.md
```

**Organização arquitetural:**

- Separação entre interface e regras de negócio.
- Organização funcional por módulos.
- Comunicação entre camadas por API.
- Estrutura preparada para expansão.
- Integração com serviços e ferramentas externas.

---

## ◈ INSTALAÇÃO E EXECUÇÃO

### 1. Clonar o repositório

```bash
git clone URL_DO_REPOSITORIO
cd OMEGA.V2
```

### 2. Configurar o backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure as variáveis de ambiente necessárias e execute:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Documentação da API:

`http://localhost:8000/docs`

### 3. Configurar o frontend

Em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

Para gerar a versão de produção:

```bash
npm run build
```

---

## ◈ DIRETRIZES DE DESENVOLVIMENTO

A evolução da Plataforma ÔMEGA considera os seguintes princípios:

- **Modularidade:** funcionalidades organizadas por domínio.
- **Integração:** comunicação entre módulos e serviços.
- **Segurança:** proteção das informações e controle de acesso.
- **Automação:** redução de atividades manuais e repetitivas.
- **Manutenibilidade:** código organizado e evolução estruturada.
- **Escalabilidade:** preparação para novas funcionalidades e integrações.

---

## ◈ STATUS DO PROJETO

**Em desenvolvimento contínuo.**

Novos recursos, integrações e aprimoramentos são incorporados progressivamente à plataforma.

---

<p align="center">
  <strong>PLATAFORMA ÔMEGA</strong><br/>
  <sub>Sistema Integrado de Gestão Empresarial</sub><br/><br/>
  <em>Tecnologia, integração e eficiência na gestão.</em>
</p>
