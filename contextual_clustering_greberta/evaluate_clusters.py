"""
Evaluation of the GreBerta Homer clusters.

Everything here is intrinsic: it uses only the cached lemma vectors and the
lemma strings themselves. No external lexicon is consulted, so nothing here can
score "semantic correctness" directly -- what it can do is quantify

  1. separation      -- are the clusters real structure or a partition of noise?
  2. agreement       -- do two unrelated algorithms find the same groups?
  3. stability       -- do the groups survive reseeding and resampling?
  4. form confound   -- how many clusters are shared morphology, not shared meaning?
  5. frequency       -- is cluster membership just a frequency effect?

Run:  $env:PYTHONIOENCODING='utf-8'; py "evaluate_clusters.py"
"""

import os
import re
import sys
import json
import unicodedata
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "greberta_clusters_output")
REPORT = os.path.join(OUT, "evaluation.txt")

SEED = 42
rng = np.random.default_rng(SEED)
lines = []


def say(text=""):
    print(text)
    lines.append(text)


# --------------------------------------------------------------------------- #
# load what the clustering run produced
# --------------------------------------------------------------------------- #
from greberta_contextual_clusters import (  # noqa: E402
    remove_top_pcs, l2, MIN_FREQ, FUNCTION_WORDS, ARTIFACTS,
    DROP_TOP_PCS, UMAP_DIM, UMAP_NEIGHBORS, HDBSCAN_MIN_SIZE,
)

z = np.load(os.path.join(OUT, "lemma_vectors.npz"), allow_pickle=True)
all_lemmas, matrix, all_freqs = list(z["lemmas"]), z["matrix"], z["freqs"]
freq_of = dict(zip(all_lemmas, all_freqs.tolist()))

keep = [i for i, l in enumerate(all_lemmas)
        if freq_of[l] >= MIN_FREQ and l not in FUNCTION_WORDS
        and l not in ARTIFACTS and any(ch.isalpha() for ch in l)]
lemmas = [all_lemmas[i] for i in keep]
vectors = l2(remove_top_pcs(matrix[keep], DROP_TOP_PCS)).astype(np.float32)
freqs = np.array([freq_of[l] for l in lemmas])

result = pd.read_csv(os.path.join(OUT, "lemma_clusters.csv"), encoding="utf-8-sig")
assert list(result["lemma"]) == lemmas, "cached vectors and cluster csv disagree"

label_cols = ["hdbscan", "ward_40", "ward_80", "ward_150"]
labels = {c: result[c].values for c in label_cols}

say(f"{len(lemmas)} lemmas, {vectors.shape[1]}d, freq range {freqs.min()}-{freqs.max()}")


# --------------------------------------------------------------------------- #
# 1. separation
# --------------------------------------------------------------------------- #
from sklearn.metrics import (  # noqa: E402
    silhouette_score, calinski_harabasz_score, davies_bouldin_score,
    adjusted_rand_score, adjusted_mutual_info_score,
)

say("\n" + "=" * 72)
say("1. SEPARATION  (measured in the 768d vector space, not the UMAP space,")
say("   so HDBSCAN gets no home-field advantage from having clustered there)")
say("=" * 72)
say(f"{'partition':<12} {'k':>5} {'n':>6} {'silhouette':>11} {'random':>8} {'CH':>8} {'DB':>6}")

sep_rows = {}
for col in label_cols:
    lab = labels[col]
    mask = lab >= 0
    x, y = vectors[mask], lab[mask]
    if len(set(y)) < 2:
        continue
    sil = silhouette_score(x, y, metric="cosine")
    shuffled = rng.permutation(y)
    sil_rand = silhouette_score(x, shuffled, metric="cosine")
    ch = calinski_harabasz_score(x, y)
    db = davies_bouldin_score(x, y)
    sep_rows[col] = dict(k=len(set(y)), n=int(mask.sum()), silhouette=float(sil),
                         random=float(sil_rand), ch=float(ch), db=float(db))
    say(f"{col:<12} {len(set(y)):>5} {int(mask.sum()):>6} {sil:>11.3f} "
        f"{sil_rand:>8.3f} {ch:>8.1f} {db:>6.2f}")

say("\nSilhouette on high-dimensional embedding spaces is always low in absolute")
say("terms; what matters is the gap to the shuffled-label baseline.")


# --------------------------------------------------------------------------- #
# 2. agreement between independent algorithms
# --------------------------------------------------------------------------- #
say("\n" + "=" * 72)
say("2. AGREEMENT  (HDBSCAN clusters in 15d UMAP space; Ward clusters directly")
say("   on cosine distance in 768d. Agreement means the groups are in the data,")
say("   not in the algorithm.)")
say("=" * 72)

core = labels["hdbscan"] >= 0
for col in ["ward_40", "ward_80", "ward_150"]:
    ari = adjusted_rand_score(labels["hdbscan"][core], labels[col][core])
    ami = adjusted_mutual_info_score(labels["hdbscan"][core], labels[col][core])
    say(f"hdbscan vs {col:<9} ARI={ari:.3f}  AMI={ami:.3f}   (on the {core.sum()} non-noise lemmas)")


# --------------------------------------------------------------------------- #
# 3. stability
# --------------------------------------------------------------------------- #
say("\n" + "=" * 72)
say("3. STABILITY")
say("=" * 72)

import umap  # noqa: E402
from sklearn.cluster import HDBSCAN, AgglomerativeClustering  # noqa: E402

say("\n(a) HDBSCAN under different UMAP seeds -- pairwise ARI:")
runs = []
for seed in [1, 7, 13, 21]:
    emb = umap.UMAP(n_components=UMAP_DIM, n_neighbors=UMAP_NEIGHBORS, min_dist=0.0,
                    metric="cosine", random_state=seed).fit_transform(vectors)
    runs.append(HDBSCAN(min_cluster_size=HDBSCAN_MIN_SIZE, min_samples=1,
                        cluster_selection_method="leaf").fit_predict(emb))
    say(f"    seed {seed}: {len(set(runs[-1])) - 1} clusters, "
        f"{int((runs[-1] == -1).sum())} noise")
pairs = [adjusted_rand_score(runs[i], runs[j])
         for i in range(len(runs)) for j in range(i + 1, len(runs))]
say(f"    mean pairwise ARI = {np.mean(pairs):.3f}  (min {min(pairs):.3f}, max {max(pairs):.3f})")
say(f"    vs the shipped run: ARI = "
    f"{np.mean([adjusted_rand_score(labels['hdbscan'], r) for r in runs]):.3f}")

say("\n(b) Ward-80 under 90% lemma subsampling -- ARI on the shared lemmas:")
base = labels["ward_80"]
sub_scores = []
for trial in range(8):
    idx = rng.choice(len(lemmas), size=int(0.9 * len(lemmas)), replace=False)
    sub = AgglomerativeClustering(n_clusters=80, metric="cosine",
                                  linkage="average").fit_predict(vectors[idx])
    sub_scores.append(adjusted_rand_score(base[idx], sub))
say(f"    mean ARI = {np.mean(sub_scores):.3f}  (min {min(sub_scores):.3f}, "
    f"max {max(sub_scores):.3f})")


# --------------------------------------------------------------------------- #
# 4. form confound: how much of a cluster is shared morphology?
# --------------------------------------------------------------------------- #
say("\n" + "=" * 72)
say("4. FORM CONFOUND  (the thing I flagged qualitatively -- now counted)")
say("=" * 72)

COMBINING = re.compile(r"[̀-ͯ᷀-᷿]")


def bare(word):
    """strip accents/breathings so ἐυ- and εὐ- compare equal"""
    return COMBINING.sub("", unicodedata.normalize("NFD", word)).lower()


bare_lemmas = [bare(l) for l in lemmas]


def form_scores(members):
    """fraction of a cluster sharing its most common 3-char prefix / 3-char suffix"""
    b = [bare_lemmas[i] for i in members]
    pre = Counter(w[:3] for w in b if len(w) >= 4)
    suf = Counter(w[-3:] for w in b if len(w) >= 4)
    n = max(len(b), 1)
    p = pre.most_common(1)[0] if pre else ("", 0)
    s = suf.most_common(1)[0] if suf else ("", 0)
    return p[1] / n, p[0], s[1] / n, s[0]


# null distribution from random clusters of matched size
null_pre, null_suf = defaultdict(list), defaultdict(list)
for size in sorted({len(g) for g in pd.Series(labels["hdbscan"]).groupby(labels["hdbscan"]).groups.values()}):
    if size < 2:
        continue
    for _ in range(60):
        members = rng.choice(len(lemmas), size=min(size, len(lemmas)), replace=False)
        fp, _, fs, _ = form_scores(members)
        null_pre[size].append(fp)
        null_suf[size].append(fs)


def null_q(table, size, q=95):
    sizes = sorted(table)
    nearest = min(sizes, key=lambda s: abs(s - size))
    return float(np.percentile(table[nearest], q))


rows = []
for col in label_cols:
    lab = labels[col]
    flagged = total = 0
    detail = []
    for gid in sorted(set(lab)):
        if gid < 0:
            continue
        members = np.where(lab == gid)[0]
        if len(members) < 3:
            continue
        fp, pre, fs, suf = form_scores(members)
        total += 1
        is_form = (fp >= 0.5 and fp > null_q(null_pre, len(members))) or \
                  (fs >= 0.6 and fs > null_q(null_suf, len(members)))
        if is_form:
            flagged += 1
            detail.append((col, gid, len(members), fp, pre, fs, suf))
    rows.append((col, flagged, total))
    say(f"{col:<12} {flagged:>3}/{total:<4} clusters ({flagged / max(total,1):.0%}) are "
        f"form-driven: dominated by a shared prefix or ending beyond chance")
    if col == "hdbscan":
        detail.sort(key=lambda r: -max(r[3], r[5]))
        say("    worst offenders:")
        for _, gid, n, fp, pre, fs, suf in detail[:10]:
            members = np.where(labels[col] == gid)[0]
            sample = "  ".join(lemmas[i] for i in members[:6])
            tag = f"prefix '{pre}' {fp:.0%}" if fp >= fs else f"ending '{suf}' {fs:.0%}"
            say(f"      cluster {gid:>3} (n={n:>2}, {tag}): {sample}")

say("\nNote: a shared 3-char ENDING is often just part of speech (-ω verbs, -ος")
say("nouns), and semantic fields are usually within one part of speech anyway,")
say("so the ending flag over-counts. The prefix flag (ευ-, αμφι-, α-privative)")
say("is the one that marks a genuinely non-semantic cluster.")


# --------------------------------------------------------------------------- #
# 5. frequency confound
# --------------------------------------------------------------------------- #
say("\n" + "=" * 72)
say("5. FREQUENCY CONFOUND  (is a cluster just a frequency band?)")
say("=" * 72)

logf = np.log10(freqs)
deciles = pd.qcut(logf, 10, labels=False, duplicates="drop")
for col in label_cols:
    lab = labels[col]
    mask = lab >= 0
    ami = adjusted_mutual_info_score(lab[mask], deciles[mask])
    within = np.mean([logf[mask][lab[mask] == g].std()
                      for g in set(lab[mask]) if (lab[mask] == g).sum() > 1])
    say(f"{col:<12} AMI(cluster, freq-decile) = {ami:.3f}   "
        f"mean within-cluster sd of log10 freq = {within:.2f} "
        f"(corpus-wide sd = {logf.std():.2f})")
say("\nAMI near 0 and within-cluster spread near the corpus-wide spread mean the")
say("clusters are not frequency bands.")


# --------------------------------------------------------------------------- #
# 6. per-cluster quality ranking
# --------------------------------------------------------------------------- #
say("\n" + "=" * 72)
say("6. WHICH CLUSTERS TO TRUST  (HDBSCAN, ranked by centroid coherence,")
say("   excluding those flagged as form-driven)")
say("=" * 72)

lab = labels["hdbscan"]
scored = []
for gid in sorted(set(lab)):
    if gid < 0:
        continue
    members = np.where(lab == gid)[0]
    if len(members) < 3:
        continue
    centroid = l2(vectors[members].mean(0, keepdims=True))[0]
    coh = float(np.mean(vectors[members] @ centroid))
    fp, pre, fs, suf = form_scores(members)
    is_form = (fp >= 0.5 and fp > null_q(null_pre, len(members))) or \
              (fs >= 0.6 and fs > null_q(null_suf, len(members)))
    scored.append((coh, gid, len(members), is_form, members))

clean = [s for s in scored if not s[3]]
clean.sort(key=lambda s: -s[0])
say(f"\n{len(clean)} of {len(scored)} clusters survive the form filter. Top 12 by coherence:")
for coh, gid, n, _, members in clean[:12]:
    sample = "  ".join(lemmas[i] for i in members[:9])
    say(f"  [{coh:.3f}] cluster {gid:>3} (n={n:>2}): {sample}")
say("\nBottom 8 by coherence (the ones to distrust):")
for coh, gid, n, _, members in clean[-8:]:
    sample = "  ".join(lemmas[i] for i in members[:9])
    say(f"  [{coh:.3f}] cluster {gid:>3} (n={n:>2}): {sample}")

cohs = np.array([s[0] for s in scored])
say(f"\ncoherence distribution: median {np.median(cohs):.3f}, "
    f"10th pct {np.percentile(cohs,10):.3f}, 90th pct {np.percentile(cohs,90):.3f}")


# --------------------------------------------------------------------------- #
say("\n" + "=" * 72)
say("COVERAGE")
say("=" * 72)
noise = int((labels["hdbscan"] == -1).sum())
say(f"HDBSCAN leaves {noise}/{len(lemmas)} lemmas ({noise/len(lemmas):.0%}) unassigned.")
say(f"Those unassigned lemmas carry {freqs[labels['hdbscan'] == -1].sum():,} of "
    f"{freqs.sum():,} tokens ({freqs[labels['hdbscan']==-1].sum()/freqs.sum():.0%}).")
say("Ward partitions everything by construction, so nothing is lost there.")

with open(REPORT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
say(f"\nwritten to {REPORT}")
