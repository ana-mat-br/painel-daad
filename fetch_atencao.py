"""Triagem de periódicos por SINAIS DE INDEXAÇÃO (não é lista de 'predatórios').

NÃO existe lista aberta e autoritativa de periódicos predatórios. A Beall's List saiu do
ar em 2017 (pressão jurídica) e a referência curada atual (Cabells) é paga. Rotular uma
revista como 'predatória' é uma ACUSAÇÃO — erro de classificação é injusto e difamatório.

Por isso este coletor INVERTE a lógica: em vez de acusar, mede SINAIS DE CURADORIA que a
revista possui, todos com dados abertos. Quem reúne sinais é 'Indexada'; quem não reúne
NENHUM cai em 'Verificar' (provável periódico nacional fora dessas bases) ou, se ainda por
cima cobra APC, em 'Atenção' — uma fila de CHECAGEM MANUAL, jamais um veredito.

Sinais de curadoria (qualquer um basta para 'Indexada'):
  - in_doaj            : revista no DOAJ (o DOAJ expulsa predatórios — sinal forte)
  - quartil Scimago    : indexada na Scopus com quartil SJR (Q1–Q4)
  - estrato estilo-Qualis : percentil de área (CiteScore-análogo aberto)

Critérios EXPLÍCITOS de classificação (por periódico, nível ISSN):
  Indexada   : tem >= 1 sinal de curadoria
  Atenção    : 0 sinais  E  cobra APC (apc_usd > 0 em algum trabalho)
  Verificar  : 0 sinais  E  não cobra APC

A tabela carrega TODOS os sinais + citação média (um periódico muito citado é claramente
legítimo, mesmo sem match nas bases — falso-positivo por ISSN divergente) para que o
julgamento seja humano e transparente.

Gera data/atencao_periodicos.csv. Sem rede: só cruza arquivos já em data/.
Uso:  python fetch_atencao.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

OUT = Path(__file__).parent / "data"


def _norm(s) -> str:
    return str(s).replace("-", "").upper()


def main() -> None:
    raw = pd.read_parquet(OUT / "uftm_works_raw.parquet")
    sq = pd.read_csv(OUT / "scimago_quartis.csv")
    qe_path = OUT / "qualis_estilo.csv"
    qe = pd.read_csv(qe_path) if qe_path.exists() else pd.DataFrame(columns=["issn"])

    # universo: artigos em periódico identificável (com ISSN e nome de fonte)
    f = raw[(raw.get("type") == "article")
            & raw["issn_l"].notna() & raw["source"].notna()].copy()
    f["issn"] = f["issn_l"].map(_norm)

    tem_sci = set(sq["issn"].map(_norm))
    tem_qe = set(qe["issn"].map(_norm)) if len(qe) else set()

    g = (f.groupby(["source", "issn"]).agg(
        n=("issn", "size"),
        doaj=("in_doaj", lambda s: bool((s == True).any())),  # noqa: E712
        apc=("apc_usd", lambda s: bool((s.fillna(0) > 0).any())),
        retratacoes=("is_retracted", lambda s: int((s == True).sum())),  # noqa: E712
        citacao_media=("cited_by", "mean"),
    ).reset_index())

    g["scimago"] = g["issn"].isin(tem_sci)
    g["qualis_estilo"] = g["issn"].isin(tem_qe)
    g["sinais_curadoria"] = g[["doaj", "scimago", "qualis_estilo"]].sum(axis=1)
    g["citacao_media"] = g["citacao_media"].round(1)

    def classe(r):
        if r["sinais_curadoria"] >= 1:
            return "Indexada"
        return "Atenção" if r["apc"] else "Verificar"

    g["classe"] = g.apply(classe, axis=1)
    g = g.sort_values(["classe", "n"], ascending=[True, False])

    cols = ["source", "issn", "n", "classe", "sinais_curadoria",
            "doaj", "scimago", "qualis_estilo", "apc",
            "retratacoes", "citacao_media"]
    g[cols].to_csv(OUT / "atencao_periodicos.csv", index=False)
    print(f"atencao_periodicos: {len(g)} periódicos — "
          f"{g['classe'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
