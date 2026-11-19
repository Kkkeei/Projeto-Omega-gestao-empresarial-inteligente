# Plataforma ÔMEGA

**Sistema de Gestão Empresarial**

A Plataforma ÔMEGA é um sistema modular de gestão empresarial voltado à centralização de informações e à automação de rotinas contábeis, fiscais e administrativas.

O projeto reúne módulos de gestão de empresas, documentação, certidões, faturamento, impostos, pendências, certificados digitais e documentos fiscais eletrônicos.

> **Status:** projeto em evolução. A disponibilidade de cada módulo depende da configuração do ambiente e das integrações externas. Este repositório contém o código-fonte; não contém banco operacional, documentos de clientes, certificados ou configurações privadas.

## Funcionalidades

| Módulo | Descrição |
|---|---|
| Dashboard | Visão consolidada de informações e atividades. |
| Empresas | Cadastro e gerenciamento de empresas. |
| Certidões | Consultas e acompanhamento de regularidade fiscal e trabalhista, conforme integrações habilitadas. |
| Documentação | Organização de documentos vinculados às empresas. |
| Faturamento | Rotinas e informações de faturamento. |
| Impostos | Organização e acompanhamento de informações tributárias. |
| Pendências | Centralização de itens que exigem acompanhamento. |
| Certificados digitais | Fluxos de gerenciamento de certificados A1 e A3. |
| NFS-e | Consulta e processamento de documentos fiscais de serviços, conforme provedor e configuração. |
| OMEGA A3 Bridge | Serviço local para comunicação com dispositivos A3 em Windows compatível. |

As funcionalidades fiscais e as consultas externas precisam ser validadas no ambiente de homologação/produção correspondente. A presença de um módulo não significa que todas as integrações estejam habilitadas.

## Arquitetura

| Camada | Tecnologia |
|---|---|
| Backend | Python + FastAPI |
| Frontend | React + TypeScript + Vite |
| Persistência | SQLite no ambiente atualmente documentado |
| Automação | Playwright |
| Bridge A3 | Serviço local para Windows |
| Versionamento | Git + GitHub |

Estrutura principal:

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── modules/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   └── package.json
├── bridge/
├── docs/
├── scripts/
├── docker-compose.yml
└── README.md
```

## Requisitos

- Python compatível com as dependências listadas em `backend/requirements.txt`.
- Node.js e npm compatíveis com o projeto Vite.
- Git.
- Dependências de sistema necessárias às bibliotecas utilizadas.
- Acesso à rede para instalar dependências e utilizar integrações externas.

## Executar localmente

### 1. Obter o código

```bash
git clone https://github.com/Kkkeei/Projeto-Omega-gestao-empresarial-inteligente.git
cd Projeto-Omega-gestao-empresarial-inteligente
```

### 2. Configurar e iniciar o backend

```bash
cd backend
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Crie a configuração local a partir do exemplo:

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edite o `.env` e substitua todos os valores de exemplo, especialmente senha administrativa, segredo JWT e chave mestra de certificados. Não reutilize credenciais de desenvolvimento em produção.

Inicie a API:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Documentação interativa da API: http://127.0.0.1:8000/docs

### 3. Configurar e iniciar o frontend

Em outro terminal, na raiz do repositório:

```bash
cd frontend
npm install
```

Crie o arquivo local de ambiente:

Linux/macOS:

```bash
cp .env.example .env.local
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env.local
```

Por padrão, o exemplo aponta para a API em `http://localhost:8000`. Ajuste `VITE_API_URL` se o backend estiver em outro endereço.

Inicie o Vite:

```bash
npm run dev -- --host 127.0.0.1
```

Acesse http://127.0.0.1:5173.

### 4. Build de produção do frontend

```bash
cd frontend
npm run build
```

O build executa a verificação TypeScript (`tsc -b`) e gera os arquivos de produção em `frontend/dist`. A publicação desses arquivos exige um servidor web configurado e a API deve estar disponível por HTTPS em ambiente público.

## Testes

Backend:

```bash
cd backend
python -m pytest
```

Frontend:

```bash
cd frontend
npm run build
```

Execute os testes no ambiente configurado. A existência de testes automatizados não garante cobertura integral nem valida a disponibilidade de serviços externos.

## Demonstração pública

Para uma exposição, utilize uma implantação separada do servidor operacional:

1. Crie uma instância de demonstração com banco SQLite novo e dados inteiramente fictícios.
2. Não copie `omega.db`, `storage/`, backups, XMLs fiscais, documentos, certificados ou arquivos de configuração do servidor real.
3. Crie credenciais exclusivas para a demonstração e desative contas e senhas padrão.
4. Desabilite rotinas automáticas, sincronizações e integrações fiscais reais que não sejam necessárias à apresentação.
5. Configure HTTPS, CORS restrito ao domínio da demonstração, autenticação e limites de acesso.
6. Teste login, navegação, operações principais, persistência e logs antes de divulgar o endereço.

O repositório não declara um endereço público de demonstração nem um deploy ativo. A hospedagem precisa ser configurada e validada separadamente. Não use o servidor operacional como ambiente de exposição.

## Segurança e dados

O sistema pode processar dados empresariais, documentos fiscais e certificados digitais. Portanto:

- Nunca versione arquivos `.env`, senhas, tokens, chaves privadas ou certificados.
- Nunca publique bancos de dados, backups, XMLs fiscais ou documentos de clientes.
- Mantenha `storage/` fora do Git e em volume persistente protegido.
- Use dados fictícios em demonstrações e testes.
- Restrinja CORS, autenticação, portas e permissões de arquivos.
- Utilize HTTPS e segredos fortes em qualquer ambiente acessível pela internet.
- Faça backup do banco e do armazenamento antes de atualizações.
- Não exponha o OMEGA A3 Bridge à internet; ele deve permanecer local à máquina que utiliza o cartão/token.

Se uma credencial real tiver sido publicada anteriormente, remova-a do código e do histórico e faça sua rotação/revogação. Apagar um arquivo em um commit posterior não invalida uma credencial exposta.

## Banco de dados e armazenamento

O banco SQLite e a pasta `storage/` são recursos de execução, não arquivos de distribuição. Devem ser criados e mantidos no ambiente de implantação, com permissões e backups próprios. Nunca substitua os dados de um servidor operacional durante uma atualização de código.

## Certificados A1/A3 e NFS-e

O certificado A1 utiliza arquivo protegido e credenciais configuradas localmente. O certificado A3 pode exigir cartão/token físico, leitor e middleware do fabricante na máquina do usuário.

O OMEGA A3 Bridge permite a comunicação local com dispositivos A3 compatíveis. A chave privada permanece no dispositivo. Consulte `bridge/README.md` para os procedimentos do Bridge.

As rotinas de NFS-e dependem do provedor, dos documentos XML, das credenciais e da disponibilidade dos serviços externos. Valide em homologação antes de qualquer operação real.

## Documentação adicional

- `backend/README.md`: informações e execução do backend.
- `frontend/README.md`: informações do frontend.
- `bridge/README.md`: instalação e segurança do Bridge A3.
- `docs/`: documentação técnica e operacional complementar.

## Aviso

A Plataforma ÔMEGA está em evolução contínua. A versão do código, o ambiente instalado e as integrações habilitadas determinam o comportamento efetivamente disponível. Operações contábeis, tributárias e fiscais devem ser conferidas pelo profissional responsável.

---

**Plataforma ÔMEGA — Gestão Empresarial**
