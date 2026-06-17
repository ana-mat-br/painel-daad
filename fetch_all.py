"""Orquestrador da coleta do Painel DAAD.

Roda TODOS os coletores em sequência, no mesmo snapshot do OpenAlex, evitando que os
arquivos em data/ fiquem dessincronizados (cada um de uma foto diferente da base).
Carimba a data da coleta em data/coletado_em.txt (mostrada na aba Transparência).

Uso:  python fetch_all.py
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import fetch_uftm_ods
import fetch_observatorio
import fetch_scimago
import fetch_colaboracao
import fetch_lens
import fetch_aguin_patentes
import fetch_citescore
import fetch_bdtd
import fetch_atencao

OUT = Path(__file__).parent / "data"


def main() -> None:
    print(">> 1/9 works da UFTM (fetch_uftm_ods)")
    fetch_uftm_ods.main()

    print(">> 2/9 comparação, temas e pesquisadores (fetch_observatorio)")
    fetch_observatorio.main()

    print(">> 3/9 quartis Scimago (fetch_scimago)")
    try:
        fetch_scimago.main()
    except Exception as e:  # mantém o arquivo anterior se o download falhar
        print(f"   Scimago falhou, mantém dados anteriores: {e}")

    print(">> 4/9 rede de coautoria (fetch_colaboracao)")
    fetch_colaboracao.main()

    print(">> 5/9 CiteScore-análogo das revistas (OpenAlex)")
    try:
        fetch_citescore.main()
    except Exception as e:
        print(f"   CiteScore-análogo pulado (mantém dados anteriores): {e}")

    print(">> 6/9 patentes The Lens (fetch_lens — precisa de LENS_TOKEN)")
    try:
        fetch_lens.main()
    except Exception as e:
        print(f"   Lens pulado (sem token ou erro): {e}")

    print(">> 7/9 portfólio de patentes da UFTM (AGUIN)")
    try:
        fetch_aguin_patentes.main()
    except Exception as e:
        print(f"   AGUIN pulado (mantém dados anteriores): {e}")

    print(">> 8/9 teses e dissertações da UFTM (BDTD/IBICT)")
    try:
        fetch_bdtd.main()
    except Exception as e:
        print(f"   BDTD pulado (mantém dados anteriores): {e}")

    print(">> 9/9 triagem de periódicos por sinais de indexação (fetch_atencao)")
    try:
        fetch_atencao.main()
    except Exception as e:
        print(f"   Triagem pulada (mantém dados anteriores): {e}")

    data = dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y-%m-%d")
    (OUT / "coletado_em.txt").write_text(data, encoding="utf-8")
    print(f"OK — coleta sincronizada concluída ({data}).")


if __name__ == "__main__":
    main()
