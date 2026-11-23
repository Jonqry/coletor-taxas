"""Confere taxas de referência em fontes oficiais e mostra o que mudou desde a última coleta."""
import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

USER_AGENT = "coletor-taxas/1.0 (projeto de portfolio; +https://github.com/Jonqry/coletor-taxas)"
INTERVALO = 2  # segundos entre requisições
ARQUIVO = Path(__file__).parent / "dados.json"

SERIES_SGS = {"tr_mensal": 7811, "selic_meta": 432, "ipca_mensal": 433}
URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados/ultimos/1?formato=json"
URL_MCMV = (
    "https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/"
    "habitacao/programa-minha-casa-minha-vida/mcmv-fgts"
)
# Financiamento imobiliário com taxas de mercado, pós-fixado em TR, pessoa física
URL_BCB_TXJUROS = "https://www.bcb.gov.br/estatisticas/reporttxjuros?codigoSegmento=1&codigoModalidade=903201"


def parse_sgs(dados):
    return dados[-1]["valor"]


def parse_mcmv(html):
    tabela = BeautifulSoup(html, "html.parser").select_one("#content-core table")
    if tabela is None:
        raise ValueError("Tabela de juros não encontrada na página do MCMV")
    linhas = []
    for tr in tabela.find_all("tr"):
        celulas = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all("td")]
        celulas = [c for c in celulas if c]
        if celulas:
            linhas.append(" | ".join(celulas))
    return linhas


def parse_txjuros(html):
    soup = BeautifulSoup(html, "html.parser")
    linhas = soup.select("table tbody tr")
    if not linhas:
        raise ValueError("Tabela de taxas não encontrada na página do BCB")
    periodo = next(p for p in soup.find_all("p") if p.get_text().startswith("Período:"))
    taxas = {}
    for tr in linhas:
        _, _, instituicao, _, ao_ano = [td.get_text(strip=True) for td in tr.find_all("td")]
        taxas[instituicao] = ao_ano
    return {"periodo": periodo.strong.get_text(strip=True), "taxas_aa": taxas}


def diferencas(antes, depois, prefixo=""):
    """Linhas legíveis com o que mudou entre duas coletas."""
    linhas = []
    for chave in sorted(antes.keys() | depois.keys()):
        a, d, nome = antes.get(chave), depois.get(chave), prefixo + chave
        if a == d:
            continue
        if isinstance(a, dict) and isinstance(d, dict):
            linhas += diferencas(a, d, nome + ".")
        elif isinstance(a, list) and isinstance(d, list):
            linhas += [f"{nome}: - {x}" for x in a if x not in d]
            linhas += [f"{nome}: + {x}" for x in d if x not in a]
        else:
            linhas.append(f"{nome}: {a} -> {d}")
    return linhas


def _get(sessao, url):
    time.sleep(INTERVALO)
    resposta = sessao.get(url, timeout=30)
    resposta.raise_for_status()
    return resposta


def _html_renderizado(url):
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(user_agent=USER_AGENT)
        pagina.goto(url)
        pagina.wait_for_selector("table tbody tr")
        html = pagina.content()
        navegador.close()
    return html


def coletar():
    with requests.Session() as sessao:
        sessao.headers["User-Agent"] = USER_AGENT
        sgs = {nome: parse_sgs(_get(sessao, URL_SGS.format(codigo)).json()) for nome, codigo in SERIES_SGS.items()}
        mcmv = parse_mcmv(_get(sessao, URL_MCMV).text)
    time.sleep(INTERVALO)
    txjuros = parse_txjuros(_html_renderizado(URL_BCB_TXJUROS))
    return {"sgs": sgs, "mcmv_tabela_juros": mcmv, "bcb_financiamento_tr": txjuros}


def main():
    anterior = json.loads(ARQUIVO.read_text("utf-8")) if ARQUIVO.exists() else {}
    atual = coletar()
    ARQUIVO.write_text(json.dumps(atual, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("\n".join(diferencas(anterior, atual)) or "Nada mudou.")


if __name__ == "__main__":
    main()
