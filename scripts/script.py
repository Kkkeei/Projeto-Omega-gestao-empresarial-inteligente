from playwright.sync_api import sync_playwright

class Automacao:
    def __init__(self):
        self.url = "https://servicos.receitafederal.gov.br/servico/certidoes/#/home/cnpj/"

    def abrir_page(self, cnpj):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto(self.url)
            page.fill('input[name="cnpj"]', cnpj)
            input("Pressione Enter para fechar...")
            browser.close()


if __name__ == "__main__":
    automacao = Automacao()
    cnpj = input("Digite seu CNPJ: ")
    automacao.abrir_page(cnpj)