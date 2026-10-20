# Auditoria inicial de UX e plano de melhorias — Plataforma ÔMEGA

**Status:** diagnóstico estático inicial do repositório.  
**Branch:** `chore/auditoria-ux-inicial`  
**Importante:** esta etapa não executou a aplicação nem alterou código de produção. As observações abaixo derivam da leitura dos arquivos no GitHub e precisam ser validadas em ambiente local.

## Objetivo

Aprimorar a experiência do usuário e a confiabilidade sem reescrever módulos que já funcionam. Preservar banco, `.env`, certificados, XMLs e `storage`. Toda mudança funcional deve passar por testes e revisão.

## Referências reais de design

- [Vercel — Web Interface Guidelines](https://vercel.com/design/guidelines): acessibilidade por teclado, foco visível, estados de carregamento/erro completos, mensagens que orientam a recuperação e confirmação para ações destrutivas.
- [Atlassian Design System — Empty State](https://atlassian.design/components/empty-state/): telas sem dados devem explicar a situação e oferecer a próxima ação útil.
- [Atlassian — Designing messages](https://atlassian.design/content/designing-messages/empty-state/): mensagens concisas, títulos claros e ações explícitas.
- [SaaSUI — Navigation UX Patterns](https://www.saasui.design/blog/saas-navigation-ux-patterns): padrões de navegação para produtos SaaS com múltiplos módulos.

Essas fontes são referências de princípios, não instruções para copiar integralmente a interface de outro produto.

## Achados iniciais do código

### 1. Dashboard — melhoria de fluxo e estados
Arquivo: `frontend/src/modules/dashboard/DashboardPage.tsx`

- Já existem cartões clicáveis para empresas, pendências e certidões, além de acesso rápido.
- O carregamento e erro usam componentes compartilhados, o que deve ser preservado.
- A atualização manual usa o mesmo fluxo de carregamento; validar visualmente se o usuário percebe que a atualização está em andamento e se o botão evita cliques repetidos.
- Os cartões de indicadores devem continuar ligados a destinos úteis e ter tratamento para dados indisponíveis, não apenas valores zero.
- Evolução sugerida: seção “Exige atenção” com tarefas acionáveis, prazo, empresa e link direto para resolver; adicionar somente indicadores com fonte de dados confiável.

### 2. Empresas — reduzir atrito sem refazer o módulo
Arquivo: `frontend/src/modules/empresas/EmpresasPage.tsx`

- Já há busca por razão social, nome fantasia, CNPJ e outros identificadores, filtros por regime/status, alternância tabela/cartões e exportação CSV.
- Próximo passo: validar se filtros e visualização são preservados ao abrir um registro e voltar; melhorar estado sem resultados, contagem de registros e feedback de exportação.
- Revisar a revogação do URL temporário do CSV e validar download em navegadores suportados.
- Não substituir a busca existente por uma segunda busca concorrente; considerar busca global apenas após mapear todos os módulos e permissões.

### 3. NFS-e — experiência e desempenho precisam de validação
Arquivo: `frontend/src/modules/nfse/NfsePage.tsx`

- A tela concentra fluxos de PJ/PF, integração A1/A3, documentos e exportação; precisa de teste de usabilidade por tarefa para não sobrecarregar o usuário.
- A função `listarTodasNfse` pagina em lotes de 500 e pode continuar até 100.000 offsets. Confirmar em quais ações é chamada e se há casos em que carrega todo o acervo desnecessariamente.
- Preferir paginação e filtros no servidor para grandes volumes, carregando somente os registros necessários à tela atual.
- Testar erros de rede, XML ausente, falha de PDF, consulta sem resultados, repetição de consulta e preservação de filtros.
- Não alterar geração de DANFSe antes de executar os testes existentes e reproduzir o erro com XML de teste.

### 4. Componentes de estado compartilhados
Arquivos: `frontend/src/components/ui/ErrorState.tsx` e `Loading.tsx`

- Há componentes reutilizáveis de erro e carregamento.
- Melhorias sugeridas: semântica acessível (`role="status"`/`aria-live` quando apropriado), foco e leitura por tecnologias assistivas, mensagens úteis e ação de recuperação específica.
- Não aplicar ARIA indiscriminadamente; verificar a estrutura final e os anúncios atuais para evitar mensagens duplicadas.

### 5. Testes e integração contínua
- O frontend define `npm run build` (`tsc -b && vite build`), mas não declara script de testes no `frontend/package.json`.
- Há testes de backend em `backend/tests/` e um script `scripts/qa_release.sh` que compila Python e executa testes do backend e da Bridge.
- A API do GitHub consultada não mostrou execuções de GitHub Actions; confirmar se workflows não existem ou se estão desabilitados.
- A auditoria anterior em `docs/AUDITORIA_FINAL_2026-10-08.md` registra 43 testes de backend e 3 da Bridge aprovados naquela execução e informa que o build do frontend não foi executado naquele ambiente. Isso é histórico, não prova o estado atual da branch.
- Não foi possível executar testes ou build somente pela leitura remota dos arquivos. É necessário executar no ambiente local com dependências instaladas e registrar o resultado atual.

## Prioridades

### P0 — Linha de base e segurança
1. Confirmar branch/commit e árvore de trabalho local.
2. Executar `scripts/qa_release.sh`.
3. Executar `npm ci` e `npm run build` em `frontend/`.
4. Registrar falhas preexistentes e testes que dependem de serviços externos.
5. Verificar autorização por usuário/empresa; a auditoria anterior aponta ausência de uma ACL explícita usuário–empresa. Validar o estado atual antes de liberar carteiras multiusuário.
6. Conferir se arquivos sensíveis (`.env`, banco operacional, certificados e XMLs) estão excluídos do Git e protegidos no armazenamento.

### P1 — UX consistente
1. Inventariar componentes visuais existentes antes de criar novos.
2. Padronizar estados de carregamento, vazio, erro, sucesso e falta de permissão.
3. Garantir foco visível, operação por teclado, rótulos acessíveis e status que não dependam apenas de cor.
4. Validar larguras de tela e tabelas com grande volume de dados.
5. Aplicar melhorias primeiro em Dashboard e Empresas como módulos-piloto.

### P2 — Operação orientada a tarefas
1. Melhorar “Exige atenção” no Dashboard com itens acionáveis e links para resolução.
2. Centralizar tarefas com empresa, competência, prazo, responsável, status e histórico, caso não exista entidade equivalente.
3. Preservar filtros e contexto ao navegar.
4. Criar busca global somente após definir fontes de dados e regras de autorização.

### P3 — NFS-e e documentos
1. Validar integridade entre registro no banco e XML existente no armazenamento.
2. Revisar paginação para evitar carregar todo o acervo no frontend.
3. Melhorar mensagens de erro com orientação de recuperação e identificador da operação.
4. Testar geração de PDF com XMLs representativos antes de mudar biblioteca ou layout.

## Plano de testes manual

- Login, sessão e permissões.
- Dashboard: carregar, atualizar, falha de API, indicadores sem dados e navegação pelos cartões.
- Empresas: buscar por CNPJ/nome, combinar filtros, alternar tabela/cartões, abrir e voltar, exportar CSV, cadastrar e editar.
- NFS-e: filtrar PJ/PF e empresa, listar acervo grande, consultar, importar, baixar XML/PDF e lidar com indisponibilidade externa.
- Documentação: upload, visualização, download, exclusão/arquivamento conforme permissões e arquivo ausente.
- Certificados: metadados A1/A3, permissões, mensagens de falha e proteção de segredos.
- Regressão: reiniciar backend e confirmar persistência de dados e arquivos.

## Critérios para aceitar mudanças

- Build do frontend e testes de backend/Bridge passam, ou falhas preexistentes ficam documentadas com evidência.
- Cada correção tem teste reproduzível.
- Nenhum arquivo de produção é substituído ou apagado.
- Não versionar `.env`, banco operacional, certificados, senhas, XMLs reais ou segredos.
- Mudanças de banco exigem plano de migração e backup.
- Mudanças visuais devem preservar a navegação e não quebrar telas menores.

## Próximo passo

Executar a linha de base no ambiente Linux onde o projeto e seus dados estão instalados. Depois, implementar uma melhoria pequena e verificável no módulo-piloto, revisar o diff e repetir os testes antes de expandir para outras telas.
