# Implementação UX e qualidade — acompanhamento

## Alterações desta entrega

- Dashboard: atualização manual passa a expor estado de carregamento, bloquear cliques repetidos e preservar os últimos indicadores quando uma atualização falha.
- Erros compartilhados: `ErrorState` passa a anunciar falhas de forma acessível com `role="alert"` e `aria-live="assertive"`.
- CI: workflow para compilar/testar backend e Bridge e executar type-check/build do frontend em pull requests e pushes relevantes.

## Próximas etapas funcionais

Estas etapas exigem implementação incremental e validação com dados de teste reais do projeto, sem substituir `.env`, `backend/omega.db`, certificados, XMLs ou `storage`:

1. Empresas: feedback de exportação, preservação de filtros ao navegar e estados vazios consistentes.
2. Documentação: auditar upload, download, arquivamento, permissões e integridade entre metadados e arquivo físico.
3. Certificados: validar validade, metadados A1/A3, avisos de vencimento e trilha de auditoria sem registrar senhas em logs.
4. NFS-e: revisar paginação para evitar leitura integral do acervo, conferir idempotência da importação e reconciliar registros com XMLs/PDFs no armazenamento.
5. Dashboard/pendências: central de ações com origem, empresa, prazo e link de resolução, usando apenas dados já disponíveis e autorizados.
6. Busca global e ficha 360º: implementar após mapear rotas, entidades e regras de autorização para evitar vazamento entre empresas.

## Critérios de aceite

- Build e testes automatizados aprovados, ou falhas preexistentes documentadas com logs.
- Nenhuma mudança destrutiva em banco ou armazenamento.
- Alterações de esquema de banco somente com migração e plano de rollback.
- Nenhum segredo, certificado ou documento real adicionado ao Git.
- Revisão manual dos fluxos de tela em desktop e largura reduzida.

## Limitação desta entrega

O workflow foi adicionado, mas ainda precisa de uma execução real no GitHub Actions. A inspeção remota do repositório não executa o código local nem confirma disponibilidade de serviços externos.
