# Plataforma ÔMEGA

**Sistema de Gestão Empresarial**

A Plataforma ÔMEGA é um sistema de gestão empresarial voltado à centralização de informações e à automação de rotinas contábeis, fiscais e administrativas. Sua arquitetura modular permite organizar funcionalidades independentes e integrar serviços necessários à operação empresarial.

O projeto reúne módulos de gestão de empresas, documentação, certidões, faturamento, impostos, pendências, certificados digitais e documentos fiscais eletrônicos.

## Visão geral

A plataforma tem como objetivo reduzir a fragmentação de processos operacionais, centralizar informações empresariais e oferecer uma base tecnológica para a evolução de rotinas de gestão e automação.

## Funcionalidades

| Módulo | Descrição |
|---|---|
| Dashboard | Apresentação consolidada de informações e atividades do sistema. |
| Empresas | Cadastro e gerenciamento de dados empresariais. |
| Certidões | Integração e acompanhamento de consultas de regularidade fiscal e trabalhista. |
| Documentação | Organização e gerenciamento de documentos vinculados às empresas. |
| Faturamento | Controle de informações e execução de rotinas de faturamento. |
| Impostos | Organização e acompanhamento de informações tributárias. |
| Pendências | Centralização de itens que necessitam de acompanhamento. |
| Certificados digitais | Gerenciamento de informações de certificados digitais A1 e A3. |
| NFS-e | Integração com documentos fiscais de serviços, consulta e processamento de XMLs e geração de documentos PDF, conforme as integrações implementadas. |
| OMEGA A3 Bridge | Componente local para comunicação com certificados A3 em ambiente Windows compatível. |

A disponibilidade das funcionalidades depende da configuração do ambiente, das credenciais, dos certificados e dos serviços externos integrados.

## Arquitetura e tecnologias

| Camada | Tecnologia |
|---|---|
| Backend | Python |
| Framework de API | FastAPI |
| Frontend | React |
| Linguagem do frontend | TypeScript |
| Ferramenta de build | Vite |
| Banco de dados | SQLite no ambiente atualmente documentado; PostgreSQL conforme configuração |
| Automação de navegador | Playwright |
| Controle de versão | Git |
| Repositório | GitHub |

### Organização do repositório

```text
OMEGA.V2/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── modules/
│   │   ├── schemas/
│   │   └── services/
│   ├── assets/
│   ├── scripts/
│   ├── tests/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── bridge/
├── docs/
├── scripts/
├── docker-compose.yml
└── README.md
```

## Requisitos

Para executar o projeto, o ambiente deve possuir:

- Python compatível com as dependências do backend.
- Node.js e npm compatíveis com o frontend.
- Git para operações com o repositório.
- Dependências de sistema exigidas pelas bibliotecas utilizadas.
- Acesso à rede para instalação de dependências e utilização das integrações externas.

As versões e dependências devem ser verificadas em `backend/requirements.txt`, `frontend/package.json` e `docker-compose.yml`.

## Instalação em ambiente Linux

### Backend

A partir do diretório raiz do projeto:

```bash
cd backend

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Configure as variáveis de ambiente necessárias antes de iniciar a aplicação. Utilize os arquivos `.env.example` disponíveis como referência, quando aplicável.

Não substitua arquivos `.env` existentes sem realizar uma cópia de segurança.

Para iniciar o backend em execução direta:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Em produção, utilize o mecanismo de execução e gerenciamento de serviços definido para o ambiente de implantação.

### Frontend

Em outro terminal:

```bash
cd frontend

npm install
npm run build
```

O comando de build gera os arquivos de produção. A publicação e a disponibilização desses arquivos dependem da configuração do servidor.

### Docker

O repositório contém arquivos de configuração Docker. Antes de iniciar os serviços, verifique as variáveis de ambiente, as portas, os volumes e os caminhos de persistência definidos na configuração.

## Segurança e proteção de dados

A aplicação pode lidar com informações empresariais, documentos fiscais e certificados digitais. Portanto, devem ser observadas as seguintes práticas:

- Não versionar senhas, tokens, chaves privadas ou arquivos `.env`.
- Não publicar certificados A1 nem suas senhas no repositório.
- Restringir o acesso a documentos e dados empresariais.
- Configurar autenticação, HTTPS, CORS e regras de rede adequadas à implantação.
- Evitar a exposição de informações confidenciais em logs.
- Realizar backups antes de atualizações ou alterações estruturais.
- Utilizar dados de teste durante o desenvolvimento sempre que possível.

### Banco de dados e armazenamento

O banco `backend/omega.db` e a pasta `storage`, quando utilizados pelo ambiente, podem conter dados essenciais à operação.

Esses recursos devem ser preservados durante atualizações. A substituição ou remoção deve ocorrer somente após a confirmação dos backups e do procedimento de migração aplicável.

Pacotes de código que excluam a pasta `storage` não incluem os documentos armazenados nela.

## Certificados digitais e NFS-e

A plataforma contempla fluxos relacionados a certificados digitais A1 e A3.

O certificado A1 é utilizado a partir de um arquivo protegido por senha. O certificado A3 pode exigir cartão ou token físico, leitor e drivers instalados na máquina em que ocorrerá a operação.

O OMEGA A3 Bridge foi concebido para apoiar a comunicação local com certificados A3 em ambiente Windows compatível. Esse componente não substitui a necessidade de acesso físico ao dispositivo e aos respectivos drivers.

As rotinas de NFS-e dependem do formato dos documentos XML, do provedor, das credenciais e da disponibilidade dos serviços externos. A geração de DANFSe e outros documentos PDF deve ser validada com arquivos de teste representativos antes da utilização operacional.

## Testes

O backend possui testes automatizados organizados em `backend/tests/`.

Com o ambiente virtual ativado, execute:

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

Antes de publicar uma atualização, recomenda-se validar:

1. Inicialização do backend e do frontend.
2. Autenticação e controle de acesso.
3. Cadastro e consulta de empresas.
4. Persistência dos dados.
5. Upload, consulta e download de documentos.
6. Operações dos módulos habilitados.
7. Fluxos de certificados digitais e NFS-e.
8. Logs e comportamento das integrações externas.

A existência de testes automatizados não garante, por si só, que todos os cenários estejam cobertos ou que os serviços externos estejam disponíveis.

## Atualização e implantação

Antes de atualizar o ambiente:

1. Realize backup do banco de dados.
2. Preserve o arquivo `.env` e as configurações locais.
3. Preserve certificados, XMLs e a pasta de armazenamento.
4. Confirme a versão do código que será implantada.
5. Instale as dependências necessárias.
6. Recompile o frontend quando houver alterações na interface.
7. Reinicie os serviços conforme a configuração do servidor.
8. Execute testes básicos e verifique os logs.

Comandos destrutivos de limpeza ou substituição não devem ser executados sem confirmar os caminhos envolvidos e a integridade dos backups.

## Documentação

A pasta `docs/` reúne materiais complementares sobre arquitetura, requisitos, módulos e procedimentos operacionais. Consulte também os arquivos README específicos do backend e do frontend.

## Considerações finais

A Plataforma ÔMEGA está em evolução contínua. A disponibilidade e o comportamento de cada módulo devem ser confirmados na versão instalada e no ambiente de execução correspondente.

As operações contábeis, tributárias e fiscais devem ser verificadas pelo profissional responsável, considerando a legislação aplicável e as regras dos serviços integrados.

---

**Plataforma ÔMEGA — Gestão Empresarial**
