# Documentação da Plataforma ÔMEGA

Este diretório reúne documentação técnica, funcional e operacional do projeto. O README principal apresenta o produto e como executá-lo; aqui ficam os detalhes necessários para desenvolver, manter e operar cada parte.

## Comece por aqui

- [Auditoria do repositório — 2026-11-15](STATUS_AUDITORIA_2026-11-15.md) | Estado verificado das branches, CI, conflitos e pendências de segurança.

| Documento | Para que serve |
|---|---|
| [Arquitetura](ARQUITETURA.md) | Organização geral, camadas e integrações. |
| [Organização do repositório](ORGANIZACAO_REPOSITORIO.md) | Estrutura atual, estrutura-alvo e plano de reorganização. |
| [Requisitos do MVP](REQUISITOS_MVP.md) | Escopo funcional documentado. |
| [Roadmap](ROADMAP.md) | Sequência de evolução planejada. |

## Guias por domínio

### Certificados e automações
- [Certificados A1/A3](CERTIFICADOS_A1_A3.md)
- [Guia A3 no Windows](GUIA_A3_WINDOWS.md)
- [Instalação do ÔMEGA A3](INSTALACAO_OMEGA_A3_WINDOWS.md)
- [Operação Windows](OPERACAO_WINDOWS.md)

### Contábil
- [Contrato do backend Contábil](CONTABIL_BACKEND_CONTRACT.md)

### Documentação / Dossiê Digital
- [Guia do usuário](GUIA_USUARIO_DOCUMENTACAO.md)
- [Especificações da aba Documentação](especificacoes_documentacao/)

### Banco de dados
- [Scripts SQL](sql/)

## Auditorias, entregas e histórico

A pasta contém relatórios de auditoria, correções, entregas e diários de bordo produzidos durante o desenvolvimento. Esses documentos são registros históricos, não necessariamente instruções atuais.

Ao criar novos registros:
1. Use nomes claros com data ISO, por exemplo `AAAA-MM-DD-assunto.md`.
2. Identifique o estado do código/branch ao qual o registro se refere.
3. Separe fatos verificados, problemas conhecidos e próximos passos.
4. Atualize este índice quando um documento for importante para consulta recorrente.

## Convenções

- Mantenha a documentação em português, com nomes de arquivos sem acentos e sem caracteres especiais.
- Não duplique instruções de instalação: mantenha o procedimento geral no README principal e os detalhes específicos junto do componente.
- Atualize documentos quando decisões técnicas forem alteradas.
- Não coloque credenciais, certificados, dados de clientes ou documentos fiscais reais na documentação.
