from app.modules.dctfweb.service import _status_obrigacao


def test_sem_registro_permanece_pendente():
    assert _status_obrigacao(None, False) == ("PENDENTE", False)


def test_valor_informado_sem_guia_nao_libera():
    assert _status_obrigacao("A_PAGAR", True, False) == ("PENDENTE", False)
    assert _status_obrigacao("A_VENCER", True, False) == ("PENDENTE", False)
    assert _status_obrigacao("EM_ATRASO", True, False) == ("PENDENTE", False)
    assert _status_obrigacao("PAGO", True, False) == ("PENDENTE", False)


def test_guia_confirmada_finaliza_obrigacao():
    assert _status_obrigacao("A_PAGAR", True, True) == ("VALOR_INFORMADO", True)
    assert _status_obrigacao("PAGO", True, True) == ("PAGO", True)


def test_credor_e_sem_movimentacao_finalizam_sem_guia():
    assert _status_obrigacao("CREDOR", True, False) == ("CREDOR", True)
    assert _status_obrigacao("SEM_MOVIMENTACAO", True, False) == ("SEM_MOVIMENTACAO", True)
    assert _status_obrigacao("SEM_MOVIMENTO", True, False) == ("SEM_MOVIMENTACAO", True)


def test_status_desconhecido_nao_libera():
    assert _status_obrigacao("STATUS_NOVO", True, True) == ("VALOR_INFORMADO", True)
