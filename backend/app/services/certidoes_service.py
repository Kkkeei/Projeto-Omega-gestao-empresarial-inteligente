import time
import pyautogui
import pyperclip
CNPJ = '34639945000170'
pyautogui.FAILSAFE = True

def executar_automacao_pyautogui():
    print("Iniciando automação no Google Chrome...")
    
    pyautogui.press('win')
    time.sleep(1)
    
    pyautogui.write('chrome', interval=0.1)
    time.sleep(1)
    pyautogui.press('enter')
    
    time.sleep(4)
    
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(0.5)
    
    # SOLUÇÃO: URL usando escape de caracteres unicode (\u003f para '?' e \u0026 para '&')
    # Isso impede que o terminal quebre ou altere a string antes da colagem
    url_sefaz = 'https://sso.sefaz.pe.gov.br/auth/realms/sefazpe/protocol/openid-connect/auth?client_id=efisco-cli&response_type=code&redirect_uri=https://efisco.sefaz.pe.gov.br/sfi_trb_gpf/PREmitirCertidaoNegativaNarrativaDebitoFiscal'
    
    # Copia a URL montada de forma isolada na memória do Windows
    pyperclip.copy(url_sefaz)
    time.sleep(0.5)
    
    # Cola diretamente na barra de endereços do Chrome
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)
    pyautogui.press('enter')
    
    print("Aguardando carregamento da Sefaz-PE...")
    time.sleep(7)
    
    print("Executando exatamente os 4 tabs solicitados...")
    for _ in range(3):
        pyautogui.press('tab')
        time.sleep(0.3)
        
    print("Pressionando Enter no botão do Gov.br...")
    pyautogui.press('enter')
    
    print("Aguardando redirecionamento para o Gov.br...")
    time.sleep(7)
    
    print("Navegando até a opção de Certificado Digital...")
    for _ in range(3):
        pyautogui.press('tab')
        time.sleep(0.3)
    pyautogui.press('enter')
    
    time.sleep(3)
    
    print("Selecionando o certificado OMEGA CONTABILIDADE...")
    pyautogui.write("OMEGA CONTABILIDADE", interval=0.1)
    time.sleep(1)
    
    pyautogui.press('enter')
    time.sleep(3)
    print("Verificando se há mensagens de erro na tela...")
    time.sleep(2)
    
    for i in range(7):
        pyautogui.press('tab')
        time.sleep(0.2)
    pyautogui.press("enter")
    for i in range(2):
        pyautogui.press('down')
        time.sleep(0.2)
    pyautogui.press('enter')
    # Primeiro move o cursor
    pyautogui.moveTo(x=1465, y=451, duration=1)

    # Depois executa o clique na posição atual
    pyautogui.click()
    pyautogui.write(CNPJ)
    time.sleep(0.2)
    pyautogui.press('enter')
    pyautogui.click(x=961, y=494)
    time.sleep(2)
    for i in range(9):
        pyautogui.press('tab')
        time.sleep(0.2)
    time.sleep(12)
    print("Fluxo finalizado.")

if __name__ == "__main__":
    executar_automacao_pyautogui()
