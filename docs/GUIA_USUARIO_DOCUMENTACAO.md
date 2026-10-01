# Guia do Usuário — Aba Documentação

## 1. Objetivo

A aba **Documentação** organiza os documentos de cada empresa em uma estrutura de pastas e subpastas, com upload, visualização, download e histórico de versões.

A navegação foi organizada no padrão de um explorador de arquivos:

```text
Empresa
└── Documentação
    ├── Societário
    │   ├── Contratos
    │   └── Alterações
    ├── Pessoal (Sócio)
    └── IRPF
```

## 2. Entrar na documentação de uma empresa

1. Abra **Documentação** no menu do ÔMEGA.
2. Use os filtros por regime, situação ou pesquisa.
3. Pesquise por razão social, nome fantasia ou CNPJ.
4. Clique na empresa desejada.

A tela da empresa apresenta a estrutura documental completa.

## 3. Entender a tela

A tela possui quatro áreas principais:

### Árvore de pastas

Fica no lado esquerdo e mostra a hierarquia da empresa.

- **Raiz da documentação** retorna ao nível inicial.
- A seta ao lado de uma pasta expande ou recolhe as subpastas.
- Clique no nome de uma pasta para abri-la.

### Barra de navegação

No topo da área de conteúdo existem:

- Voltar;
- Subir uma pasta;
- Ir para a raiz;
- Atualizar.

Também existe o **caminho de navegação (breadcrumb)**, por exemplo:

```text
Documentação > Societário > Contratos
```

Clique em qualquer etapa do caminho para retornar diretamente àquele nível.

### Conteúdo da pasta

O painel central mostra:

- subpastas;
- documentos;
- tipo;
- quantidade de documentos ou versões;
- última atualização;
- ações disponíveis.

### Pesquisa

A caixa **Pesquisar nesta pasta...** filtra o conteúdo do nível atual.

## 4. Criar uma pasta

No topo da tela, clique em **Nova pasta**.

Na raiz, será criada uma pasta principal.

Dentro de outra pasta, o mesmo botão cria uma **subpasta**.

Exemplo:

```text
Societário
└── Contratos
```

Ao criar `Contratos` estando dentro de `Societário`, o ÔMEGA registra a relação pai/filho no banco e também garante a criação do diretório físico da categoria no armazenamento do servidor.

## 5. Criar uma subpasta

1. Entre na pasta que será a pasta pai.
2. Clique em **Nova pasta**.
3. Confirme o local exibido no formulário.
4. Informe o nome.
5. Opcionalmente, informe uma descrição.
6. Clique em **Criar subpasta**.

A pasta aparece imediatamente na árvore e no conteúdo da pasta atual.

## 6. Renomear uma pasta

Quando estiver dentro de uma pasta, use o botão de edição no bloco de contexto da pasta.

O sistema impede nomes duplicados dentro do mesmo nível.

Renomear uma pasta não altera o caminho físico dos arquivos. O armazenamento usa identificadores estáveis da categoria para preservar referências existentes.

## 7. Arquivar uma pasta

Use o botão de arquivar da pasta atual.

O arquivamento é lógico: a pasta deixa de aparecer na estrutura ativa, mas o histórico permanece preservado.

Ao arquivar uma pasta que possui subpastas, as subpastas e documentos ativos vinculados também são arquivados.

## 8. Enviar um documento

1. Entre na pasta de destino.
2. Clique em **Upload** ou na área de upload.
3. Informe o nome do documento.
4. Selecione o arquivo ou arraste-o para a área.
5. Opcionalmente, registre uma observação.
6. Clique em **Enviar documento**.

O limite padrão é de **25 MB**, configurável pelo ambiente do backend.

O sistema registra a versão inicial como **Versão 1**.

## 9. Arrastar arquivos

A área de upload aceita arrastar o arquivo diretamente para a pasta atual.

Também existe sempre a alternativa de clicar e selecionar o arquivo, portanto o funcionamento não depende exclusivamente de arrastar e soltar.

## 10. Visualizar e baixar

Na linha do documento, existem ações para:

- visualizar;
- baixar;
- consultar histórico;
- arquivar.

A visualização e o download passam pela API autenticada do ÔMEGA. O arquivo não é servido diretamente pelo frontend.

## 11. Histórico de versões

Clique no botão de histórico do documento.

O sistema apresenta as versões existentes em ordem decrescente:

```text
Versão 3
Versão 2
Versão 1
```

Criar uma nova versão não apaga a versão anterior.

## 12. Adicionar nova versão

Dentro do histórico do documento:

1. selecione um novo arquivo;
2. envie o arquivo;
3. o sistema cria a próxima versão automaticamente.

Exemplo:

```text
Versão 1 → arquivo original
Versão 2 → arquivo atualizado
Versão 3 → nova atualização
```

## 13. Boas práticas de organização

Prefira nomes objetivos e consistentes:

```text
Contrato Social 2026
Alteração Contratual 03 2026
Alvará 2026
CND Federal 09 2026
Procuração 2026
```

Para estruturas maiores, utilize subpastas:

```text
Societário
├── Contratos
├── Alterações
└── Atas
```

## 14. O que não fazer

Não mova ou renomeie manualmente os diretórios de armazenamento do servidor.

Não exclua arquivos diretamente do storage para “limpar” documentos pela interface.

Use o próprio ÔMEGA para arquivar documentos e pastas.

## 15. Fluxo recomendado

```text
Selecionar empresa
      ↓
Entrar na pasta
      ↓
Criar subpasta, se necessário
      ↓
Enviar documento
      ↓
Conferir documento
      ↓
Visualizar / baixar
      ↓
Criar nova versão quando necessário
      ↓
Arquivar quando deixar de ser ativo
```

## 16. Resultado esperado

Ao final, a documentação da empresa deve permitir localizar qualquer arquivo sem depender de uma lista única e desorganizada.

Exemplo:

```text
PINGMEL COMÉRCIO LTDA.
│
└── Documentação
    │
    ├── Societário
    │   ├── Contratos
    │   │   └── Contrato Social 2026.pdf
    │   └── Alterações
    │       └── Alteração 03 2026.pdf
    │
    ├── Pessoal (Sócio)
    │   └── João Silva
    │       └── Documento Pessoal.pdf
    │
    └── IRPF
        └── Declaração 2025.pdf
```

## 17. Observação sobre armazenamento

A hierarquia exibida ao usuário é mantida pelo cadastro de categorias. O armazenamento físico utiliza IDs estáveis de empresa e categoria. Isso permite renomear uma pasta sem quebrar os caminhos dos documentos.

## Nova pasta x Subpasta

- **Nova pasta:** sempre cria a pasta no diretório principal da Documentação, independentemente de onde o usuário estiver navegando.
- **Subpasta:** cria uma pasta dentro da pasta atualmente aberta.
- **Subpasta no diretório principal:** quando o usuário estiver na raiz da Documentação, o botão **Subpasta** também criará a pasta no diretório principal, pois não existe uma pasta pai selecionada.
