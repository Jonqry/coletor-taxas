# coletor-taxas

## O problema

Meu simulador de financiamento imobiliário (React + TypeScript) usa taxas de referência digitadas à mão (`taxasReferencia.ts`). Quando o governo ou o Banco Central mudam um número, o simulador fica desatualizado e eu só descubro por acaso.

Este coletor confere três fontes oficiais toda semana e abre uma issue quando algo muda:

| Fonte | O que coleta | Ferramenta |
|---|---|---|
| API SGS do Banco Central | TR mensal (7811), meta Selic (432), IPCA mensal (433) | Requests |
| gov.br/cidades, página "MCMV – Linha Financiada" | Tabela de faixas de renda e juros do Minha Casa, Minha Vida | BeautifulSoup |
| bcb.gov.br, "Taxas de juros" | Taxa anual de financiamento imobiliário (mercado, pós-fixado em TR) por banco | Playwright |

O resultado fica em `dados.json`. A cada execução, o script mostra a diferença em relação à coleta anterior.

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python coletor.py        # coleta, salva dados.json e mostra o que mudou
python -m pytest         # testes com HTML/JSON salvos, sem internet
```

No GitHub, o workflow `.github/workflows/coleta.yml` roda toda segunda-feira (ou manualmente em *Actions → Run workflow*). Ele commita o `dados.json` e abre uma issue com a lista de mudanças.

## Decisão técnica: o Playwright só renderiza, quem lê é uma função pura

A página de taxas do BCB é feita em Angular. Sem JavaScript, ela mostra apenas "Essa pagina depende do javascript para abrir". O Playwright abre a página, espera a tabela aparecer e devolve o HTML renderizado. Quem extrai os dados é `parse_txjuros`, que usa BeautifulSoup e recebe uma string.

Por causa dessa separação, os testes usam um trecho real do HTML renderizado, salvo em `tests/fixtures`, e rodam sem navegador e sem internet. Se o site mudar o layout, só a função de parse quebra, e o teste mostra exatamente onde.

O BCB também publica esses dados numa API OData (Olinda). Num sistema de produção, eu usaria a API. Aqui, usei a página de propósito para praticar automação de navegador numa fonte oficial que de fato depende de JavaScript.

Antes de escrever o código, conferi o `robots.txt` de cada site. As requisições usam um User-Agent identificado e um intervalo de 2 s entre elas.
