# Contribuindo com a Plataforma ÔMEGA

## Fluxo de trabalho

1. Atualize sua branch local a partir de `main`.
2. Crie uma branch por tarefa.
3. Faça alterações pequenas e focadas.
4. Execute os testes/validações aplicáveis.
5. Atualize a documentação do módulo afetado.
6. Abra um Pull Request descrevendo o problema, a solução, os testes e os riscos.

## Padrão de branches

- `feat/<assunto>`
- `fix/<assunto>`
- `refactor/<assunto>`
- `docs/<assunto>`
- `chore/<assunto>`

## Mensagens de commit

Use mensagens curtas e descritivas, preferencialmente no formato:

- `feat(contabil): adiciona cadastro de lançamentos`
- `fix(nfse): corrige importação de documentos`
- `docs(repo): atualiza guia de arquitetura`

## Cuidados por camada

- Backend: mantenha rotas HTTP em `app/api/v1` e regras de domínio nos módulos/serviços adequados.
- Frontend: mantenha telas organizadas por domínio e reutilize componentes compartilhados.
- Bridge: preserve sua execução local no computador do usuário; não acople o leitor A3 ao servidor.
- Dados: não inclua dados reais de clientes, certificados, bancos locais, arquivos temporários ou segredos.

## Checklist do Pull Request

- [ ] A alteração tem escopo claro.
- [ ] Testes relevantes foram executados ou a limitação foi explicada.
- [ ] Frontend compila quando afetado.
- [ ] Documentação foi atualizada.
- [ ] Nenhum segredo ou dado real foi incluído.
- [ ] Migrações, contratos de API e compatibilidade entre camadas foram avaliados.
