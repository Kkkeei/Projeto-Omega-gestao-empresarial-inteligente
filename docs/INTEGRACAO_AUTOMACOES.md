# Preparação para integrar automações do ÔMEGA

## O que você deve me entregar
Para cada automação, envie um ZIP ou pasta com:
- código-fonte completo;
- requirements.txt ou lista de dependências;
- comando que você usa hoje para executá-la;
- portal/URL inicial e objetivo;
- dados de entrada necessários (CNPJ, UF, competência etc.);
- forma de autenticação (pública, login, certificado A1/A3, CAPTCHA);
- arquivos e dados que ela gera;
- exemplos de entrada/saída com dados fictícios ou anonimizados;
- erros conhecidos e como você identifica sucesso, pendência ou falha.

Não envie senhas, tokens, cookies, certificados privados, PINs ou dados reais de clientes. Envie somente os nomes das variáveis necessárias, nunca seus valores secretos.

## Contrato de adaptação
A integração deve adaptar cada rotina a uma função explícita, sem executar nada durante o import do módulo:

```python
def executar(contexto: dict) -> dict:
    return {
        "status": "SUCESSO",  # SUCESSO, PENDENCIA ou ERRO
        "mensagem": "Resumo sem dados sensíveis",
        "arquivos": [
            {"caminho": "/caminho/resultado.pdf", "tipo": "PDF", "nome": "resultado.pdf"}
        ],
        "dados": {}
    }
```

O contrato é uma proposta inicial; o código que você enviar será analisado e adaptado antes de ser ligado ao sistema.

## Como será feita a integração
1. Revisar o código, dependências e riscos.
2. Criar adaptador compatível com o módulo de automações.
3. Executar a rotina em worker separado da API, sem bloquear as requisições.
4. Registrar status, início/fim, duração, mensagem e histórico no banco.
5. Guardar PDF/XML na estrutura de armazenamento do ÔMEGA e persistir metadados.
6. Implementar timeout, retentativas limitadas, prevenção de duplicidade e limpeza temporária.
7. Testar em homologação com dados fictícios.
8. Só habilitar agendamento após teste manual aprovado.

## Regras de segurança e operação
- Não colocar segredos no código nem nos logs.
- Não contornar CAPTCHA, MFA ou controles de segurança dos portais.
- Usar Playwright headless quando permitido e suportado pelo portal.
- Certificado A3 deve ser utilizado pela bridge local do usuário quando necessário; não presumir que o cartão esteja acessível no servidor.
- Nunca sobrescrever banco, .env, certificados ou documentos existentes durante atualização.
- Uma automação não é considerada pronta até o teste real e a conferência do arquivo produzido.

## Estrutura sugerida para entrega
```
automacao-nome/
  README.md
  requirements.txt
  src/
    main.py
  tests/
  exemplos/
    entrada_ficticia.json
    saida_ficticia.json
```

Se a automação já estiver funcionando, não reescreva antes de enviar: entregue a versão atual e o comando exato que você usa para executá-la. Isso ajuda a preservar a lógica que já funciona.
