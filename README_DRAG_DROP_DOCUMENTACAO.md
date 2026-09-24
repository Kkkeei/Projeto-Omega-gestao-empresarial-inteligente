# Drag & Drop — Documentação ÔMEGA

Implementado na tela de documentação da empresa.

## Comportamento

- A área de conteúdo da pasta aceita arquivos arrastados do Windows Explorer.
- Ao arrastar, a área destaca visualmente e informa a pasta de destino.
- Ao soltar, o arquivo é carregado no formulário de `Adicionar documento`.
- O nome do documento é preenchido automaticamente a partir do nome do arquivo, sem a extensão.
- O usuário pode revisar o nome e informar observação antes de enviar.
- O upload utiliza o mesmo endpoint existente do botão `Adicionar documento`.
- A empresa e a pasta selecionada são enviadas pelo fluxo existente; o backend valida que a pasta pertence à empresa.
- Limite no frontend: 25 MB. O backend já possui validação do mesmo limite.
- A área continua funcionando mesmo quando já existem documentos: fica compacta e acima da lista.

## Arquivos alterados

- `frontend/src/modules/documentacao/EmpresaDocumentacaoPage.tsx`
- `frontend/src/styles.css`

Nenhuma alteração no banco de dados foi feita por esta implementação.

## Instalação

Substitua os dois arquivos acima no projeto atual e reinicie/recompile o frontend.

Exemplo:

```powershell
cd C:\Users\Administrador.SRV\Desktop\OMEGA\frontend
npm install
npm run build
```

Se o projeto estiver sendo executado pelo Vite em modo desenvolvimento, basta reiniciar o processo do frontend após substituir os arquivos.
