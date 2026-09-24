# Documentação — Pastas editáveis e layout em abas

Alterações aplicadas exclusivamente ao módulo `Documentação`.

## Layout
- As pastas principais agora aparecem como abas horizontais, seguindo a referência visual enviada.
- A pasta selecionada fica branca/destacada; as demais ficam em tom cinza suave.
- O contador de documentos fica junto ao nome da pasta.
- Abaixo das abas, a pasta selecionada possui ações de editar e arquivar.
- O botão `Nova pasta` fica acima da estrutura das pastas.

## Comportamento
- Todas as pastas principais ativas da empresa aparecem na tela, inclusive pastas criadas pelo usuário.
- `Nova pasta` cria uma pasta que permanece visível após o recarregamento.
- `Editar pasta` permite alterar nome e descrição.
- O nome não pode duplicar outra pasta ativa da mesma empresa.
- A exclusão continua sendo lógica/arquivamento, preservando histórico.
- As pastas padrão iniciais continuam sendo criadas para empresas que ainda não possuam nenhuma pasta.
- O sistema deixou de arquivar automaticamente pastas personalizadas.

## API
- `PUT /api/v1/documentacao/categorias/{categoria_id}` para edição.
- `GET /api/v1/documentacao/empresas/{empresa_id}/categorias` retorna todas as pastas principais ativas da empresa.

## Segurança de dados
Nenhuma alteração foi feita na estrutura das outras áreas da plataforma. Arquivos de banco (`omega.db`, WAL e SHM) não fazem parte do pacote de atualização.
