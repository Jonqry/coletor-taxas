import pytest
import requests

import coletor


def falha(sessao):
    raise requests.ConnectionError("Connection reset by peer")


def test_fonte_que_falha_mantem_valor_anterior_e_as_outras_seguem():
    anterior = {"sgs": {"selic_meta": "13.75"}, "mcmv_tabela_juros": ["Faixa 1 | 4,00%"]}
    fontes = {"sgs": lambda s: {"selic_meta": "14.00"}, "mcmv_tabela_juros": falha}

    atual, falhas = coletor.coletar(anterior, fontes)

    assert atual == {"sgs": {"selic_meta": "14.00"}, "mcmv_tabela_juros": ["Faixa 1 | 4,00%"]}
    assert len(falhas) == 1 and falhas[0].startswith("mcmv_tabela_juros:")


def test_todas_as_fontes_falhando_derruba_a_coleta():
    with pytest.raises(RuntimeError):
        coletor.coletar({}, {"sgs": falha, "mcmv_tabela_juros": falha})


def test_get_tenta_de_novo_quando_a_conexao_cai(monkeypatch):
    monkeypatch.setattr(coletor, "INTERVALO", 0)
    chamadas = []

    class Sessao:
        def get(self, url, timeout):
            chamadas.append(url)
            if len(chamadas) < 3:
                raise requests.ConnectionError("Connection reset by peer")
            resposta = requests.Response()
            resposta.status_code = 200
            return resposta

    assert coletor._get(Sessao(), "https://exemplo").status_code == 200
    assert len(chamadas) == 3
