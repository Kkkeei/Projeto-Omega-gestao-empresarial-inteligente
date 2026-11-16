# Fechamento — Lançamentos e Conferências

Data: 10/11/2026

## Alterações concluídas nesta etapa

- O painel geral mantém cards por regime, pesquisa por razão social/nome fantasia/CNPJ, filtro por responsável e lista em ordem alfabética.
- O cálculo do progresso considera somente movimentações lançadas e conferidas como concluídas; movimentações não aplicáveis são retiradas do denominador.
- A situação prioriza atraso quando há ao menos uma movimentação vencida e não concluída; empresas sem movimentações recebem situação e indicador neutros.
- Movimentações lançadas aguardando conferência usam o indicador azul.
- A integração com Documentação permanece vinculada por documento de origem, sem duplicar movimentações.
- Documentos inativados continuam visíveis nas competências abrangidas pelo período final, preservando o histórico anterior.
- Alterações de nome e categoria no cadastro de documentação são refletidas na movimentação derivada.
- Empresas sem responsável ficam disponíveis na carteira compartilhada para usuários autenticados, inclusive no painel de Documentação e em Lançamentos e Conferências. Quando uma empresa recebe uma atribuição ativa, ela passa a ficar visível e acessível somente ao responsável e aos administradores. A gestão de atribuições e a consulta da lista global de empresas continuam restritas a administradores.
- A navegação principal foi agrupada em Geral, Contábil, Fiscal, Gestão e Documentos e Administração.
- Os seletores de competência receberam controles de mês anterior/próximo. O cadastro de nova documentação inicia na competência imediatamente anterior à atual.
- O botão “Voltar ao painel” foi separado do título da página individual.

## Testes executados

- `tests/test_contabil_lancamentos_conferencias.py`: 13 testes aprovados.
- Verificação sintática Python dos arquivos `service.py`, `repository.py` e `routes.py`: aprovada.
- Verificação sintática TSX dos arquivos alterados: aprovada.

## Limitação da validação de frontend

O build integral `npm run build` não pôde ser concluído porque a instalação das dependências (`npm ci`) excedeu o tempo disponível e o modo offline não encontrou todos os pacotes no cache. Portanto, não declarar o build integral do Vite como aprovado até executá-lo em ambiente com as dependências instaladas.

## Observação sobre a suíte geral

A execução de toda a suíte backend apresentou 91 testes aprovados e 8 falhas em testes de BrasilAPI, Certificados Digitais e NFS-e. Essas falhas estão fora dos arquivos e do escopo desta aba; devem ser tratadas em suas respectivas etapas.

## Segurança do pacote

O ZIP de entrega não contém `storage`, bancos de dados, `.env` reais, `.venv`, `node_modules`, caches nem `.git`. Os arquivos de exemplo `.env.example` podem permanecer no pacote.
