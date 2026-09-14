CORRECAO - PERSISTENCIA PERMANENTE DAS CERTIDOES

IMPORTANTE: esta versao NAO inclui backend/omega.db justamente para impedir que uma
instalacao nova sobrescreva a base de dados existente.

O backend cria/migra as tabelas automaticamente na inicializacao.

CORRECOES:
1. Toda consulta estadual cria/atualiza a fotografia atual em certidoes.
2. Toda consulta gera uma linha permanente em consultas_certidoes e certidoes_historico.
3. O historico permanente e append-only: UPDATE/DELETE sao bloqueados por triggers.
4. PDFs sao salvos com nome unico e hash SHA-256.
5. O banco gera backup permanente apos cada consulta registrada.
6. Bancos antigos que possuem consultas mas nao possuem a linha atual em certidoes sao
   reconstruidos automaticamente a partir da ultima consulta.
7. A tela de Certidoes carrega os registros persistidos ao entrar novamente na area.
8. A empresa selecionada fica gravada no navegador e e restaurada ao voltar para Certidoes.
9. Sem empresa selecionada, a tela mostra todas as certidoes atuais persistidas.

INSTALACAO:
- Substitua os arquivos do projeto pelos arquivos desta versao.
- NAO apague nem substitua backend/omega.db.
- NAO apague a pasta storage/ se ela ja possuir PDFs/backup.
- Reinicie o backend uma vez para executar a migracao.
- Atualize o frontend com recarregamento forcado do navegador.

MÓDULO ADICIONAL — CERTIDÃO NARRATIVA DE DÉBITO FISCAL SEFAZ-PE
===============================================================

Foi integrado ao módulo de Certidões um segundo fluxo real da SEFAZ-PE que exige navegação visual com PyAutoGUI e seleção de certificado digital.

Fluxo preservado:
Chrome -> SSO SEFAZ-PE -> Gov.br -> certificado digital -> CNPJ -> consulta -> página final do documento.

Após a etapa final já existente no script original, o agente copia o conteúdo textual que está sendo exibido no Chrome, analisa apenas expressões explícitas e envia o resultado para a Plataforma ÔMEGA.

Novo endpoint:
POST /api/v1/certidoes/narrativa/consultar/{empresa_id}

Novo tipo de certidão:
Narrativa de Débito Fiscal - SEFAZ

Novo tipo de automação:
CONSULTA_CERTIDAO_NARRATIVA

Configuração opcional do certificado digital:
SEFAZ_CERTIFICADO_NOME=OMEGA CONTABILIDADE

IMPORTANTE:
- A automação visual exige Windows com sessão gráfica ativa, Chrome aberto pelo usuário/ambiente e certificado digital disponível.
- O backend não usa PyAutoGUI em importação; o módulo é carregado somente quando a automação é realmente executada. Isso permite testes e execução da API em ambientes sem display.
- O texto lido é preservado na consulta e no histórico em `texto_extraido`.
- A classificação é conservadora: Negativa -> REGULAR; Positiva com efeitos -> POSITIVA COM EFEITOS DE NEGATIVA; Positiva -> IRREGULAR; texto ambíguo -> AGUARDANDO_INTERVENCAO.

CERTIDAO FEDERAL - RFB/PGFN
===========================
Foi acrescentado o módulo de consulta da Certidão Federal no portal:
https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj

Endpoint:
POST /api/v1/certidoes/federal/consultar/{empresa_id}

A tela de Certidões ganhou o botão "Consultar Federal".
A automação usa Playwright em janela visível, informa o CNPJ da empresa selecionada, aguarda o processamento, lê o conteúdo apresentado e tenta localizar/baixar o documento. O resultado é classificado conservadoramente entre REGULAR, NEGATIVA, POSITIVA COM EFEITOS DE NEGATIVA, IRREGULAR e AGUARDANDO_INTERVENCAO/NAO DISPONIVEL.

Cada consulta é persistida em certidoes, consultas_certidoes e certidoes_historico, com execução em execucoes_automacao. PDF, quando obtido, é armazenado em storage/certidoes/federal/{CNPJ}/{ANO}/.

IMPORTANTE: os seletores e o fluxo do portal da Receita Federal precisam ser homologados no Windows, porque a navegação real e eventuais mudanças do portal não puderam ser executadas neste ambiente. Em caso de mudança do layout, o módulo guarda leitura textual e retorna AGUARDANDO_INTERVENCAO em vez de inventar um resultado.
