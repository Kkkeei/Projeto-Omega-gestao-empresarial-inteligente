# Correção — Visualização/Download das Declarações de Faturamento

## Problema
A rota de PDF da declaração está protegida pela autenticação do router global da API. Abrir diretamente no navegador uma URL como:

`/api/v1/declaracoes-faturamento/{id}/visualizar`

não envia o cabeçalho `Authorization: Bearer ...`, por isso o backend responde `401 - Autenticação necessária.`

## Correção
O frontend do Faturamento agora busca o PDF com `fetch`, envia o token armazenado em `omega_access_token` e só então cria uma URL `blob:` para visualizar ou baixar o arquivo.

Foi corrigido:
- geração de declaração de 12 meses;
- geração de declaração anual;
- geração de declaração personalizada;
- botão Baixar no histórico de declarações;
- visualização da declaração sem abrir a URL protegida diretamente.

O backend permanece protegido; não foi necessário tornar os PDFs públicos.
