# Arquitetura ÔMEGA

## Monólito modular
A solução adota monólito modular, mantendo módulos independentes e baixo acoplamento.

### Domínios previstos
- Identidade e acesso
- Empresas
- Documentos
- Certidões
- Contabilidade
- Faturamento
- Licitações
- Dossiês
- Notificações
- Auditoria
- Dashboard
- Integrações
- Infraestrutura

## Camadas
Presentation → API → Application/Domain → Infrastructure → PostgreSQL/Storage/Integrações.

## Histórico
Certidão é entidade histórica. Cada consulta é uma linha nova. Documentos futuros usarão versões imutáveis.

## Integrações
Prioridade: API oficial → Web Service → automação oficial permitida → consulta assistida → manual.
