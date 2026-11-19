# Atualização ÔMEGA — 09/10/2026

## Documentação
- O botão de subpasta fica desabilitado na raiz; é necessário entrar em uma pasta antes de criar uma subpasta.
- Erros de criação são exibidos no formulário em vez de ficarem somente como rejeições de promessa no navegador.
- Falhas ao criar o diretório físico de documentos retornam uma mensagem operacional clara.
- A árvore mantém a hierarquia lógica no banco e o armazenamento físico por IDs estáveis, preservando os caminhos usados pelos documentos existentes.
- Foram ampliados os testes de hierarquia para incluir uma pasta de terceiro nível.

## Consulta BrasilAPI
- Respostas JSON inválidas e payloads de erro do provedor são convertidos em erros controlados.
- A consulta externa não devolve detalhes internos do backend ao cliente.
- Indisponibilidade/limite do provedor retorna HTTP 502/429, em vez de um erro interno 500 sem tratamento.

## Interface e atalhos
- Refinamento visual de espaçamento, foco de teclado, tabelas, botões, painéis e área de Documentação.
- Navegação rápida com `Ctrl+K` (ou `Cmd+K` no macOS), busca por módulo e abertura com `Enter`.
- `?` abre a ajuda de atalhos.
- `Alt+1` até `Alt+8` abre os módulos principais pela ordem do menu.
- Na documentação de uma empresa: `Alt+Shift+F` pesquisa; `Alt+Shift+N` cria subpasta; `Alt+Shift+U` abre upload; `Alt+↑` sobe para a pasta pai; `Esc` fecha modais.
- Corrigida a importação ausente de `apiFetchBlob` no serviço de Certidões, identificada durante a validação estática do frontend.

## Validação
- Backend: `46 passed` na suíte completa.
- Sintaxe/transpilação TypeScript dos arquivos modificados: aprovada.
- Build completo React/Vite: não concluído porque as dependências npm não estavam disponíveis localmente; a instalação offline falhou por pacote ausente no cache. Executar `npm ci` em ambiente com acesso ao registry e, depois, `npm run build`.

Nenhuma alteração foi aplicada ao banco operacional `backend/omega.db`. A suíte utiliza o banco isolado `.test_runtime`.
