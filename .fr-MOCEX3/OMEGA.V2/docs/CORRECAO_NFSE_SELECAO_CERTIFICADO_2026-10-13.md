# Correção — seleção de titular e carregamento de certificado na NFS-e

## Alterações

- A página NFS-e não seleciona automaticamente a primeira empresa ao abrir.
- Ao alternar entre Pessoa Jurídica e Pessoa Física, o titular volta a ficar sem seleção até o usuário escolher explicitamente.
- O contexto, os documentos e o certificado somente são carregados depois que um titular é selecionado.
- O serviço NFS-e continua consultando os certificados cadastrados no módulo Certificados do ÔMEGA; não foi criada uma segunda tabela nem um armazenamento duplicado.
- Certificados A1 ativos com validade válida podem ser selecionados mesmo se um cadastro legado não tiver `thumbprint_sha256`. O A1 é usado a partir do PFX protegido, e o material real é carregado/validado ao montar a conexão mTLS.
- Certificados A3 continuam exigindo thumbprint SHA-256 válido porque o Bridge precisa comparar a identidade do cartão/token com o cadastro do ÔMEGA.

## Validação

- Backend: 76 testes aprovados.
- OMEGA Bridge: 3 testes aprovados.
- A instalação npm não foi concluída neste ambiente por timeout; por isso, o build completo do frontend não foi declarado como aprovado.

## Implantação

Preserve `backend/.env`, `backend/omega.db` e o diretório de storage existentes. Reinicie backend e frontend após copiar o código. Abra NFS-e, escolha PJ/PF e selecione o titular para carregar documentos e certificado.
