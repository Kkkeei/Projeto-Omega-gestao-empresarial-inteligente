# Checklist simples de teste — atualização ÔMEGA

## Preparação
- [ ] Fazer backup do código atual.
- [ ] Confirmar que o .env, backend/omega.db e storage não serão substituídos.
- [ ] Reiniciar o backend e confirmar que inicia sem traceback.

## Dashboard
- [ ] Abrir o painel sem erro.
- [ ] Conferir os números de empresas, pendências, certidões e automações com os dados existentes.
- [ ] Clicar nos cartões e confirmar que cada um abre o módulo correto.
- [ ] Redimensionar a tela; confirmar que os ícones e cartões permanecem alinhados.

## Certidões
- [ ] Selecionar uma empresa.
- [ ] Confirmar que há apenas um botão principal para emitir a certidão selecionada.
- [ ] Testar consulta em ambiente autorizado e conferir histórico/PDF quando disponível.

## Certificados
- [ ] Entrar como administrador e verificar que as ações administrativas continuam disponíveis.
- [ ] Entrar como usuário comum e abrir um certificado A1.
- [ ] Confirmar que a aba/ação para revelar senha não aparece para usuário comum.
- [ ] Tentar chamar diretamente o endpoint de senha com usuário comum e confirmar HTTP 403.
- [ ] Entrar como administrador, visualizar a senha e conferir o evento de auditoria.
- [ ] Confirmar que usuário comum não consegue baixar o certificado A1 nem baixar a senha em TXT.
- [ ] Confirmar que o PIN do A3 não é mostrado nem armazenado.

## Regressão
- [ ] Testar login/logout.
- [ ] Abrir cadastro de empresa e documentação.
- [ ] Abrir e baixar um documento já existente.
- [ ] Conferir console do navegador e logs do backend.
