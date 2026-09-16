# Robustez das automações visuais

- Federal/RFB e Narrativa/SEFAZ usam uma instância Chrome dedicada com perfil temporário.
- Essa instância é fechada em `finally` mesmo quando há exceção.
- O encerramento usa `taskkill /T /F` somente no PID raiz criado pela automação e sua árvore de processos.
- O perfil temporário é removido ao final.
- CNPJ inválido, Chrome ausente, clipboard indisponível, timeout, erro de foco, falha de download e falha de classificação retornam `ERRO_TECNICO` sem bloquear o banco.
- A automação não retorna `AGUARDANDO_INTERVENCAO`.
- O lock da Central detecta processo morto no mesmo host e remove lock órfão.
- A certidão estadual via Playwright já fecha página, contexto e Playwright em `finally`.

Não existe garantia matemática de zero erro: mudanças externas de portais, indisponibilidade de rede, certificado inválido ou alterações visuais podem gerar falha. O objetivo deste endurecimento é garantir que essas situações sejam tratadas, registradas e limpem o navegador/lock sem derrubar a plataforma.

- Federal e Narrativa fazem até OMEGA_PYAUTOGUI_RETRIES tentativas técnicas (padrão 2), sempre com navegador novo e limpeza no finally.
- PDFs temporários da Receita são removidos após a persistência.
- Falhas fiscais (IRREGULAR/POSITIVA etc.) não são tratadas como erro técnico nem repetidas desnecessariamente.
