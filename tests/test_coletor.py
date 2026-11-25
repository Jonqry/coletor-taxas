import json
from pathlib import Path

import coletor

FIXTURES = Path(__file__).parent / "fixtures"


def ler(nome):
    return (FIXTURES / nome).read_text("utf-8")


def test_parse_sgs_pega_o_valor_mais_recente():
    assert coletor.parse_sgs(json.loads(ler("sgs_432.json"))) == "13.75"


def test_parse_mcmv_le_faixas_e_taxas():
    linhas = coletor.parse_mcmv(ler("mcmv_fgts.html"))
    assert "Faixa 1 | até R$ 2.160,00 | 4,00% | 4,25% | 4,50% | 4,75%" in linhas
    assert "Faixa 3 | de R$ 5.000,01 a R$ 9.600,00 | 7,66% | 8,16%" in linhas
    assert "Classe Média | até R$ 13.000,00 | 10,00%" in linhas


def test_parse_txjuros_le_tabela_renderizada():
    dados = coletor.parse_txjuros(ler("bcb_txjuros_903201.html"))
    assert dados["periodo"] == "01/10/2026 a 31/10/2026"
    assert len(dados["taxas_aa"]) == 12
    assert dados["taxas_aa"]["CAIXA ECONOMICA FEDERAL"] == "11,97"


def test_diferencas():
    antes = {"sgs": {"selic_meta": "13.75"}, "mcmv": ["Faixa 1 | 4,00%"]}
    depois = {"sgs": {"selic_meta": "13.50", "tr_mensal": "0.1196"}, "mcmv": ["Faixa 1 | 4,25%"]}
    assert coletor.diferencas(antes, depois) == [
        "mcmv: - Faixa 1 | 4,00%",
        "mcmv: + Faixa 1 | 4,25%",
        "sgs.selic_meta: 13.75 -> 13.50",
        "sgs.tr_mensal: None -> 0.1196",
    ]
    assert coletor.diferencas(antes, antes) == []


def test_main_salva_json_e_mostra_mudancas(tmp_path, monkeypatch, capsys):
    arquivo = tmp_path / "dados.json"
    arquivo.write_text(json.dumps({"sgs": {"selic_meta": "13.75"}}), "utf-8")
    monkeypatch.setattr(coletor, "ARQUIVO", arquivo)
    monkeypatch.setattr(coletor, "coletar", lambda anterior: ({"sgs": {"selic_meta": "13.50"}}, []))

    coletor.main()

    assert json.loads(arquivo.read_text("utf-8")) == {"sgs": {"selic_meta": "13.50"}}
    assert capsys.readouterr().out == "sgs.selic_meta: 13.75 -> 13.50\n"
