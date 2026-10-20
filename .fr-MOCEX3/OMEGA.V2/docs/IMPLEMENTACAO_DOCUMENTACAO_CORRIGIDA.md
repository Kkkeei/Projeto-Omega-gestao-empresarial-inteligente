# Implementação — Aba Documentação Corrigida

## Objetivo

Corrigir a navegação, criação de subpastas e consistência entre banco de dados, armazenamento físico e interface da aba Documentação.

## Problemas identificados

1. A API aceitava `categoria_pai_id`, porém a interface sempre enviava `null` ao criar uma pasta.
2. A listagem de categorias retornava apenas pastas raiz.
3. A interface usava abas horizontais para pastas, dificultando a navegação em vários níveis.
4. A edição de pasta era limitada às pastas principais.
5. O arquivamento tratava apenas os documentos diretamente ligados à pasta, sem percorrer subpastas.
6. A criação de uma pasta no banco não garantia a existência imediata do diretório físico correspondente.
7. Visualização e download não registravam auditoria específica de acesso.
8. A estrutura de armazenamento e a árvore lógica não estavam claramente alinhadas na experiência do usuário.

## Correções aplicadas

### Backend

- Listagem da árvore completa de categorias ativas.
- Contagem de subpastas por categoria.
- Criação de subpastas com validação da pasta pai.
- Prevenção de nomes duplicados dentro do mesmo nível.
- Criação automática do diretório físico da categoria.
- Reparação automática de diretórios ausentes ao carregar a documentação.
- Edição de pastas em qualquer nível da árvore.
- Arquivamento recursivo de uma pasta, incluindo subpastas e documentos ativos.
- Preservação do histórico por arquivamento lógico.
- Auditoria específica para visualização e download.
- Caminho físico baseado em IDs estáveis.

### Frontend

A interface foi reorganizada no padrão de explorador de arquivos:

```text
┌───────────────────────────────────────────────┐
│ Voltar / ← / ↑ / Início / Atualizar          │
│ Documentação > Societário > Contratos         │
├─────────────────┬─────────────────────────────┤
│ Árvore          │ Conteúdo da pasta            │
│                 │                              │
│ Societário      │ 📁 Atas                      │
│  ├ Contratos    │ 📄 Contrato Social.pdf       │
│  └ Alterações   │ 📄 Alteração 03.pdf          │
│                 │                              │
└─────────────────┴─────────────────────────────┘
```

Recursos adicionados:

- árvore lateral;
- breadcrumb;
- voltar;
- subir um nível;
- voltar à raiz;
- atualização;
- pesquisa no nível atual;
- criação de pasta e subpasta no local atual;
- upload no local atual;
- drag-and-drop com alternativa por clique;
- edição de pastas em qualquer nível;
- histórico de versões;
- ações por documento.

## Referências de usabilidade

A navegação usa breadcrumb porque esse padrão ajuda o usuário a saber onde está e a saltar diretamente para níveis anteriores de uma hierarquia de pastas. A Microsoft documenta esse padrão especificamente para cenários de sistema de arquivos e navegação profunda.

A navegação também possui árvore lateral e comandos de voltar/subir, aproximando o comportamento de um explorador de arquivos tradicional.

O drag-and-drop permanece disponível, mas não é a única forma de executar o upload. Essa alternativa segue a orientação de acessibilidade de oferecer uma forma simples de operar a mesma função sem arrastar.

## Critério de conclusão

A aba deve ser considerada corrigida somente quando:

```text
[ ] Criar pasta raiz
[ ] Criar subpasta
[ ] Navegar para subpasta
[ ] Voltar
[ ] Subir nível
[ ] Breadcrumb
[ ] Renomear pasta raiz
[ ] Renomear subpasta
[ ] Upload
[ ] Upload por arraste
[ ] Upload por seleção
[ ] Visualizar
[ ] Baixar
[ ] Nova versão
[ ] Arquivar documento
[ ] Arquivar pasta com subpastas
[ ] Histórico preservado
[ ] Diretório físico criado
[ ] Auditoria de ações
[ ] Teste automatizado do backend
[ ] Build frontend validado no ambiente com dependências instaladas
```

## Ajuste complementar

Os botões de criação foram separados por finalidade, mantendo o restante da navegação:

- **Nova pasta:** criação exclusivamente na raiz da Documentação.
- **Subpasta:** criação dentro da pasta atualmente aberta.
- **Na raiz:** o botão Subpasta cria uma nova pasta na própria raiz.
