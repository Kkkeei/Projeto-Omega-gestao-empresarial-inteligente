
def test_narrativa_fecha_chrome_se_falhar_no_inicio(monkeypatch):
    from app.services import sefaz_narrativa_pyautogui as mod
    class FakePG:
        pass
    class FakeSession:
        def __init__(self):
            self.closed = False
        def start(self):
            raise RuntimeError('chrome não abriu')
        def close(self):
            self.closed = True
    fake = FakeSession()
    monkeypatch.setattr(mod, '_get_pyautogui', lambda: FakePG())
    monkeypatch.setattr(mod, 'ChromeAutomationSession', lambda: fake)
    resultado = mod.executar_automacao_pyautogui('34639945000170')
    assert resultado['situacao'] == 'ERRO'
    assert resultado['status_processamento'] == 'ERRO_TECNICO'
    assert fake.closed is True


def test_receita_fecha_chrome_se_falhar_no_inicio(monkeypatch):
    from app.services import receita_federal_service as mod
    class FakeSession:
        def __init__(self):
            self.closed = False
        def start(self):
            raise RuntimeError('chrome não abriu')
        def close(self):
            self.closed = True
    fake = FakeSession()
    monkeypatch.setattr(mod, 'ChromeAutomationSession', lambda: fake)
    resultado = mod._executar_pyautogui('34639945000170')
    assert resultado['situacao'] == 'ERRO'
    assert resultado['status_processamento'] == 'ERRO_TECNICO'
    assert fake.closed is True
