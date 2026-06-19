"""Classifica as teses/dissertacoes da BDTD por ODS, replicando o MESMO processo do OpenAlex.

O OpenAlex marca cada trabalho com as ODS usando o classificador Aurora SDG — um modelo
mBERT multilabel (multilingue) aplicado ao titulo + resumo, com corte de score 0.4. As teses
da UFTM nao tem DOI e quase nao entram no OpenAlex, entao aqui rodamos o MESMO modelo aberto
(Zenodo 7304547, CC-BY 4.0) sobre o titulo + resumo de cada tese da BDTD.

Replica fielmente o pipeline de github.com/ourresearch/openalex-sdg-classifier (helpers.py):
sentencas com [CLS]/[SEP], tokenizer 'bert-base-multilingual-uncased', pad/truncate 512,
mascaras de atencao, e corte 0.4. Roda em container linux/amd64 (ver classify_bdtd_sdg.sh),
porque o stack pinado (tensorflow-cpu==2.9.3, transformers==4.9.2) nao instala em arm64/py3.14.

Entrada:  data/bdtd_uftm.csv  +  models/aurora_sdg_mbert.h5
Saida:    data/bdtd_sdg.csv   (id, sdg_id, sdg_name, score) — uma linha por (tese, ODS>=0.4)
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

import pandas as pd
import tensorflow as tf

tf.config.threading.set_intra_op_parallelism_threads(2)
from nltk import tokenize as nltk_tokenize
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from transformers import BertTokenizer, TFBertModel

ROOT = Path(__file__).parent
MODEL_PATH = ROOT / "models" / "aurora_sdg_mbert.h5"
IN_CSV = ROOT / "data" / "bdtd_uftm.csv"
OUT_CSV = ROOT / "data" / "bdtd_sdg.csv"

CUTOFF = 0.4   # mesmo limiar publicado do OpenAlex/Aurora
MAX_LEN = 512
BATCH = 8      # modesto, para caber na RAM da VM do Docker (Mac de 8 GB)

# Nomes oficiais das 17 ODS no classificador Aurora (iguais aos do helpers.py original)
GOAL_NAMES = {
    1: "No poverty", 2: "Zero hunger", 3: "Good health and well-being",
    4: "Quality Education", 5: "Gender equality", 6: "Clean water and sanitation",
    7: "Affordable and clean energy", 8: "Decent work and economic growth",
    9: "Industry, innovation and infrastructure", 10: "Reduced inequalities",
    11: "Sustainable cities and communities", 12: "Responsible consumption and production",
    13: "Climate action", 14: "Life below water", 15: "Life in Land",
    16: "Peace, Justice and strong institutions", 17: "Partnerships for the goals",
}


def _ensure_punkt():
    import nltk
    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)


def build_text(row) -> str:
    """Titulo + resumo — o mesmo insumo (title + abstract) que o OpenAlex da ao modelo."""
    titulo = str(row.get("titulo") or "").strip()
    resumo = str(row.get("resumo") or "").strip()
    txt = (titulo + ". " + resumo).strip()
    return txt if txt not in (".", "") else titulo


def tokenize_with_markers(text: str) -> str:
    """Adiciona [CLS] no inicio e [SEP] ao fim de cada sentenca (identico ao helpers.py)."""
    out = "[CLS] "
    for sentence in nltk_tokenize.sent_tokenize(text):
        out += sentence + " [SEP] "
    return out


def main():
    _ensure_punkt()
    tokenizer = BertTokenizer.from_pretrained("bert-base-multilingual-uncased")
    print(f"Carregando modelo Aurora SDG mBERT ({MODEL_PATH})...", flush=True)
    # compile=False: nao restaura o otimizador (economia decisiva de RAM na VM do Docker)
    model = load_model(str(MODEL_PATH),
                       custom_objects={"TFBertMainLayer": TFBertModel}, compile=False)

    df = pd.read_csv(IN_CSV)
    df = df[df["titulo"].notna()].reset_index(drop=True)
    print(f"Teses a classificar: {len(df)}", flush=True)

    rows = []
    for start in range(0, len(df), BATCH):
        chunk = df.iloc[start:start + BATCH]
        texts = [tokenize_with_markers(build_text(r)) for _, r in chunk.iterrows()]
        toks = [tokenizer.tokenize(t)[:MAX_LEN] for t in texts]
        ids = [tokenizer.convert_tokens_to_ids(t) for t in toks]
        padded = pad_sequences(ids, maxlen=MAX_LEN, dtype="long",
                               truncating="post", padding="post")
        masks = tf.cast(padded > 0, tf.int32)
        preds = model([tf.convert_to_tensor(padded), masks]).numpy()

        for (_, r), p in zip(chunk.iterrows(), preds):
            for i, score in enumerate(p):
                if float(score) >= CUTOFF:
                    n = i + 1
                    rows.append({"id": r["id"], "sdg_id": n,
                                 "sdg_name": GOAL_NAMES[n], "score": round(float(score), 4)})
        print(f"  {min(start + BATCH, len(df))}/{len(df)}", flush=True)

    out = pd.DataFrame(rows, columns=["id", "sdg_id", "sdg_name", "score"])
    out.to_csv(OUT_CSV, index=False)
    n_classif = out["id"].nunique()
    print(f"\nGravado {OUT_CSV} — {len(out)} marcacoes ODS em {n_classif} teses "
          f"({n_classif/max(len(df),1):.0%} com ao menos 1 ODS >= {CUTOFF}).", flush=True)


if __name__ == "__main__":
    main()
