# -*- coding: utf-8 -*-
"""
wsi_cluster.py — Stage-WSI step 2: per-lemma Word Sense Induction.

For each content lemma, its GreBERTa occurrence vectors (from step 1) are
clustered into SENSES. A lemma used one way stays one sense; a polysemous lemma
splits into several, each with its own centroid, example citations and the Greek
words that keep it company. This is the disambiguated unit that step 3 clusters
into semantic fields.

Per lemma
  - freq < MIN_SENSE_OCC        -> one sense (the mean vector); too few tokens to
                                   induce senses reliably.
  - otherwise                   -> average-linkage agglomerative clustering on
                                   COSINE distance with a fixed distance threshold;
                                   tiny clusters are absorbed into the nearest
                                   surviving sense, at most MAX_SENSES are kept, and
                                   a split whose cosine silhouette < MIN_SILHOUETTE
                                   is collapsed back to one sense (guards against
                                   over-splitting Homer's formulaic repetition).

Outputs (word_sense_induction/wsi_output/)
  senses.csv          lemma, sense_id, n_occ, n_senses_lemma, silhouette,
                      gloss, gloss_source, top_context_lemmas, example_citations
  sense_centroids.npy (S, H) float32 unit vectors, aligned row-for-row to senses.csv

Run:   py word_sense_induction/wsi_cluster.py
Dependencies: numpy, pandas, scikit-learn  (reuses the gloss module for LSJ + stops)
"""

import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score

import wsi_common as C

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MIN_SENSE_OCC  = 10      # fewer occurrences than this -> a single sense
DIST_THRESHOLD = 0.55    # cosine-distance cut for average linkage
MAX_SENSES     = 6       # cap on senses per lemma
MIN_SENSE_SIZE = 3       # smaller clusters are absorbed into the nearest sense
MIN_SILHOUETTE = 0.05    # weaker splits collapse back to one sense
TOP_CONTEXT    = 12      # co-occurring lemmas reported per sense
N_EXAMPLES     = 5       # example citations per sense


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def consolidate(V, labels):
    """Absorb clusters smaller than MIN_SENSE_SIZE and cap at MAX_SENSES by
    reassigning their points to the nearest surviving centroid (cosine)."""
    sizes = Counter(labels)
    kept = [lab for lab, n in sizes.items() if n >= MIN_SENSE_SIZE]
    if len(kept) > MAX_SENSES:
        kept = [lab for lab, _ in sizes.most_common()][:MAX_SENSES]
    if len(kept) <= 1:
        return np.zeros(len(labels), dtype=int)
    cents = {lab: _unit(V[labels == lab].mean(0)) for lab in kept}
    kept_labs = list(cents)
    M = np.vstack([cents[l] for l in kept_labs])         # (k, H) unit
    sims = V @ M.T                                        # (n, k) cosine
    nearest = np.asarray(kept_labs)[sims.argmax(1)]
    # renumber to 0..k-1 in descending size order
    order = [lab for lab, _ in Counter(nearest).most_common()]
    remap = {lab: i for i, lab in enumerate(order)}
    return np.asarray([remap[l] for l in nearest], dtype=int)


def induce_senses(V):
    """(labels, silhouette) for one lemma's occurrence matrix V (unit rows)."""
    n = len(V)
    if n < MIN_SENSE_OCC:
        return np.zeros(n, dtype=int), float("nan")
    labels = AgglomerativeClustering(
        n_clusters=None, distance_threshold=DIST_THRESHOLD,
        metric="cosine", linkage="average").fit_predict(V)
    labels = consolidate(V, labels)
    if len(set(labels)) < 2:
        return np.zeros(n, dtype=int), float("nan")
    sil = silhouette_score(V, labels, metric="cosine")
    if sil < MIN_SILHOUETTE:                              # too weak -> one sense
        return np.zeros(n, dtype=int), float("nan")
    return labels, float(sil)


def build_sentence_lemmas(df):
    """(work, sentence_id) -> Counter(lemma) over all embedded content tokens."""
    sent = defaultdict(Counter)
    for work, sid, lemma in zip(df["work"], df["sentence_id"], df["lemma"]):
        sent[(work, sid)][lemma] += 1
    return sent


def citation(r):
    return f"{r['work']} {r['book']}.{r['line']}"


def main():
    if not C.OCC_VECTORS.exists():
        sys.exit("Run embed_occurrences.py first (occ_vectors.npy missing).")
    print("Loading occurrence vectors + index ...")
    arr = np.load(C.OCC_VECTORS)
    df = pd.read_csv(C.OCC_INDEX, encoding="utf-8")
    print(f"   {arr.shape[0]:,} occurrences, dim {arr.shape[1]}, "
          f"{df['lemma'].nunique():,} lemmas")

    print("Loading reusable gloss module (LSJ glosses + stoplist) ...")
    gloss = C.load_gloss()
    stops = gloss.build_stoplist()
    lsj, lsj_rel, _ = gloss.load_lsj()
    gloss_cache = {}

    def lemma_gloss(lemma):
        if lemma not in gloss_cache:
            gloss_cache[lemma] = gloss.lemma_gloss(lemma, lsj, lsj_rel, {})
        return gloss_cache[lemma]

    sent_lemmas = build_sentence_lemmas(df)
    rows_by_lemma = df.groupby("lemma").indices          # lemma -> row positions

    print(f"Inducing senses (freq>={MIN_SENSE_OCC} eligible to split) ...")
    sense_rows, centroids = [], []
    n_poly = 0
    # process most frequent lemmas first (nicer output ordering)
    order = df["lemma"].value_counts().index
    for li, lemma in enumerate(order):
        if lemma in stops:
            continue
        idx = rows_by_lemma[lemma]
        V = arr[idx]
        labels, sil = induce_senses(V)
        n_senses = len(set(labels))
        if n_senses > 1:
            n_poly += 1
        g, gsrc = lemma_gloss(lemma)
        for s in range(n_senses):
            members = idx[labels == s]
            Vs = arr[members]
            cent = _unit(Vs.mean(0))
            sims = Vs @ cent
            best = members[np.argsort(-sims)][:N_EXAMPLES]
            examples = "; ".join(citation(df.iloc[b]) for b in best)
            ctx = Counter()
            for m in members:
                r = df.iloc[m]
                ctx.update(sent_lemmas[(r["work"], r["sentence_id"])])
            for drop in list(ctx):
                if drop == lemma or drop in stops:
                    ctx.pop(drop, None)
            top_ctx = " ".join(w for w, _ in ctx.most_common(TOP_CONTEXT))
            centroids.append(cent.astype(np.float32))
            sense_rows.append({
                "lemma": lemma, "sense_id": s, "n_occ": int(len(members)),
                "n_senses_lemma": n_senses,
                "silhouette": round(sil, 4) if sil == sil else "",
                "gloss": g, "gloss_source": gsrc,
                "top_context_lemmas": top_ctx, "example_citations": examples,
            })
        if (li + 1) % 500 == 0:
            print(f"   {li + 1:,} lemmas processed, {len(sense_rows):,} senses")

    senses = pd.DataFrame(sense_rows)
    cent_arr = np.vstack(centroids)
    senses.to_csv(C.SENSES_CSV, index=False, encoding="utf-8")
    np.save(C.SENSE_CENTROIDS, cent_arr)

    n_lemmas = senses["lemma"].nunique()
    print(f"\nSaved {len(senses):,} senses over {n_lemmas:,} lemmas "
          f"-> {C.SENSES_CSV.name}")
    print(f"Saved centroids {cent_arr.shape} -> {C.SENSE_CENTROIDS.name}")
    print(f"Polysemous lemmas (>=2 senses): {n_poly:,} "
          f"({n_poly / max(n_lemmas, 1):.1%})")
    dist = senses.groupby("lemma")["sense_id"].max().add(1).value_counts().sort_index()
    print("Senses-per-lemma distribution:")
    for k, v in dist.items():
        print(f"   {k} sense(s): {v:,} lemmas")


if __name__ == "__main__":
    main()
