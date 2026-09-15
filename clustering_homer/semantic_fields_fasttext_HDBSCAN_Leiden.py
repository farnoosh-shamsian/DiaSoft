# -*- coding: utf-8 -*-
"""
Discover candidate semantic fields in Homer (Iliad + Odyssey) by clustering
lemma embeddings — fully unsupervised.

Pipeline
    1. Load lemmatized sentences from the two alignment CSVs
       (the "Lemmas" column: space-separated lemmas per sentence).
    2. Train FastText embeddings on the joint corpus (both epics share one
       embedding space, so clusters draw evidence from ~200k tokens).
    3. Restrict to content lemmas (frequency >= MIN_FREQ, minus a stoplist of
       function words and treebank artifacts).
    4. Cluster the lemma vectors two ways:
         a) HDBSCAN  — density-based, allows "noise" (unassigned lemmas)
         b) Leiden   — community detection on a cosine kNN graph,
                       every lemma is assigned to a community
    5. Compare the two partitions (sizes, silhouette, ARI/AMI agreement)
       and write human-readable cluster listings = candidate semantic fields.
    6. (Optional) Label each cluster with a short English gloss via the
       Groq API — set the GROQ_API_KEY environment variable to enable.

Outputs (in OUTPUT_DIR):
    lemma_clusters.csv       lemma, frequency, HDBSCAN label, Leiden label
    clusters_hdbscan.txt     one block per HDBSCAN cluster, members sorted
                             by centrality (distance to cluster centroid)
    clusters_leiden.txt      same for Leiden
    comparison_report.txt    the head-to-head comparison
    homer_fasttext.model     the trained embedding model (reusable later)

Dependencies:  pip install gensim python-igraph pandas scikit-learn
"""

import csv
import json
import os
import re
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import igraph as ig
from gensim.models import FastText
from sklearn.cluster import HDBSCAN
from sklearn.metrics import adjusted_rand_score, adjusted_mutual_info_score, silhouette_score
from sklearn.metrics.pairwise import cosine_distances
from sklearn.neighbors import NearestNeighbors

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
HERE       = Path(__file__).parent            # "clustering_homer"
REPO       = HERE.parent
CSV_FILES  = [REPO / "homer_corpus" / "iliad_alignments.csv",
              REPO / "homer_corpus" / "odyssey_alignments.csv"]
OUTPUT_DIR = HERE / "semantic_fields_output_HDBSCAN_Leiden"

SEED = 42

# --- FastText ---------------------------------------------------------------
VECTOR_SIZE = 100     # embedding dimensionality
WINDOW      = 5       # context window (sentences average ~13 lemmas)
MIN_COUNT   = 3       # lemmas rarer than this are ignored during training
EPOCHS      = 80      # small corpus (~200k tokens) -> many epochs
MIN_N, MAX_N = 3, 6   # character n-gram range (subword units)

# --- Clustering vocabulary ---------------------------------------------------
MIN_FREQ = 5          # only cluster lemmas occurring at least this often

# --- HDBSCAN -----------------------------------------------------------------
HDBSCAN_MIN_CLUSTER_SIZE = 6
HDBSCAN_MIN_SAMPLES      = 3
HDBSCAN_SELECTION        = "leaf"   # "leaf" = many fine clusters (good for
                                    # semantic fields); "eom" = fewer, coarser

# --- Leiden ------------------------------------------------------------------
KNN_K             = 15     # neighbours per lemma in the similarity graph
LEIDEN_RESOLUTION = 3.0    # higher -> more, finer communities
LEIDEN_SWEEP      = [0.5, 1.0, 2.0, 3.0, 5.0]   # reported for orientation

# --- Optional LLM labelling of clusters (off unless key is present) ----------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")   # or paste your key here
GROQ_MODEL   = "llama-3.3-70b-versatile"

# Treebank annotation artifacts: English words typed in beta-code Greek letters
ARTIFACTS = {"θυοτε", "οτηερ", "υνκνοων", "ηψπηεν"}   # quote, other, unknown, hyphen

# Function words excluded from clustering (they are kept for training, where
# they provide context, but they are not candidate semantic-field members).
# Edit freely — e.g. remove adverbs of place/time if you want a "deixis" field.
STOPLIST = {
    # article, pronouns, possessives
    "ὁ", "ὅς", "ὅδε", "οὗτος", "ἐκεῖνος", "κεῖνος", "αὐτός", "ἐγώ", "σύ",
    "ἕ", "μιν", "νιν", "σφεῖς", "τίς", "τις", "ὅστις", "ἐμός", "σός", "τεός",
    "ἑός", "ἡμέτερος", "ὑμέτερος", "σφέτερος", "ἀμός",
    # particles
    "δέ", "τε", "καί", "μέν", "γάρ", "ἄρα", "ἄρ", "ῥα", "δή", "γε", "πέρ",
    "τοι", "νυ", "κε", "κεν", "ἄν", "οὖν", "γοῦν", "αὖ", "αὖτε", "ἦ", "μήν",
    "μάν", "θην", "ἀτάρ", "αὐτάρ", "ὦ", "περ",
    # negations
    "οὐ", "μή", "οὐδέ", "μηδέ", "οὔτε", "μήτε", "οὐδείς", "μηδείς",
    # prepositions
    "ἐν", "εἰς", "ἐκ", "ἀπό", "ἐπί", "κατά", "παρά", "πρός", "προτί", "ποτί",
    "ὑπό", "ὑπέρ", "περί", "ἀμφί", "ἀνά", "διά", "μετά", "σύν", "ξύν",
    "ἀντί", "πρό",
    # conjunctions / subordinators
    "εἰ", "ὡς", "ὅτι", "ὅτι2", "ὅτε", "ἐπεί", "ἐπήν", "ἵνα", "ὄφρα", "ἤ",
    "ἠέ", "ἠδέ", "ἰδέ", "ἠμέν", "εἴτε", "ὅπως", "ὥστε", "ἕως", "πρίν",
    "ὁπότε", "ὁππότε", "εὖτε",
    # copula
    "εἰμί",
}

GREEK_LETTER = re.compile(r"[Ͱ-Ͽἀ-῿]")

# Polytonic Greek has two visually identical accent encodings (oxia vs tonos).
# NFC normalization canonicalizes them so stoplist lookups always match.
STOPLIST = {unicodedata.normalize("NFC", w) for w in STOPLIST}


# --------------------------------------------------------------------------
# 1. Load corpus
# --------------------------------------------------------------------------
def load_sentences(paths):
    """Return a list of lemma lists, one per sentence, from all CSVs.

    The header row is located by searching for a cell named 'Lemmas'
    (the Iliad file has a junk URL line above its header, and a duplicated
    empty column block after column 5 — both are handled here).
    """
    sentences = []
    for path in paths:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        header_idx = next(i for i, r in enumerate(rows) if "Lemmas" in r)
        lem_col = rows[header_idx].index("Lemmas")   # first Lemmas column
        n = 0
        for row in rows[header_idx + 1:]:
            if len(row) > lem_col and row[lem_col].strip():
                toks = [unicodedata.normalize("NFC", t)
                        for t in row[lem_col].split()]
                toks = [t for t in toks
                        if t not in ARTIFACTS and GREEK_LETTER.search(t)]
                if toks:
                    sentences.append(toks)
                    n += 1
        print(f"  {path.name}: {n} sentences")
    return sentences


# --------------------------------------------------------------------------
# 2. Train embeddings
# --------------------------------------------------------------------------
def train_fasttext(sentences):
    """Skip-gram FastText. workers=1 + fixed seed => fully reproducible."""
    model = FastText(
        sentences=sentences,
        vector_size=VECTOR_SIZE,
        window=WINDOW,
        min_count=MIN_COUNT,
        sg=1,                # skip-gram: better for small corpora / rare words
        negative=10,
        sample=1e-4,         # aggressive subsampling of δέ, καί, ...
        epochs=EPOCHS,
        min_n=MIN_N,
        max_n=MAX_N,
        seed=SEED,
        workers=1,
    )
    return model


# --------------------------------------------------------------------------
# 3. Clustering vocabulary + vectors
# --------------------------------------------------------------------------
def build_vocab(sentences, model):
    freq = Counter(t for s in sentences for t in s)
    vocab = [w for w, c in freq.most_common()
             if c >= MIN_FREQ and w not in STOPLIST and w in model.wv]
    vecs = np.vstack([model.wv[w] for w in vocab]).astype(np.float64)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)   # unit length
    return vocab, vecs, freq


# --------------------------------------------------------------------------
# 4a. HDBSCAN
# --------------------------------------------------------------------------
def run_hdbscan(vecs):
    dist = cosine_distances(vecs)
    np.clip(dist, 0.0, None, out=dist)
    np.fill_diagonal(dist, 0.0)
    clu = HDBSCAN(
        min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE,
        min_samples=HDBSCAN_MIN_SAMPLES,
        cluster_selection_method=HDBSCAN_SELECTION,
        metric="precomputed",
        copy=True,
    ).fit(dist)
    return clu.labels_


# --------------------------------------------------------------------------
# 4b. Leiden
# --------------------------------------------------------------------------
def build_knn_graph(vecs, k=KNN_K):
    """Undirected kNN graph; edge weight = cosine similarity."""
    nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine").fit(vecs)
    dist, idx = nn.kneighbors(vecs)
    edges, weights = {}, {}
    for i in range(len(vecs)):
        for d, j in zip(dist[i, 1:], idx[i, 1:]):        # skip self
            e = (min(i, j), max(i, j))
            w = max(1.0 - d, 1e-9)                        # similarity
            if e not in edges or w > weights[e]:
                edges[e] = e
                weights[e] = w
    g = ig.Graph(n=len(vecs), edges=list(edges.values()))
    g.es["weight"] = [weights[e] for e in edges.values()]
    return g


def run_leiden(graph, resolution=LEIDEN_RESOLUTION):
    part = graph.community_leiden(
        objective_function="modularity",
        weights="weight",
        resolution=resolution,
        n_iterations=-1,          # iterate until convergence
    )
    return np.asarray(part.membership), part.modularity


# --------------------------------------------------------------------------
# 5. Reporting helpers
# --------------------------------------------------------------------------
def cluster_members_by_centrality(vocab, vecs, labels):
    """{label: [(lemma, sim_to_centroid), ...]} sorted most-central first."""
    out = {}
    for lab in sorted(set(labels)):
        if lab == -1:
            continue
        idx = np.where(labels == lab)[0]
        centroid = vecs[idx].mean(axis=0)
        centroid /= np.linalg.norm(centroid)
        sims = vecs[idx] @ centroid
        order = np.argsort(-sims)
        out[lab] = [(vocab[idx[o]], float(sims[o])) for o in order]
    return out


def write_cluster_file(path, clusters, freq, labels_name, gloss=None):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {labels_name}: {len(clusters)} clusters "
                f"(members sorted by centrality; frequency in parentheses)\n\n")
        for lab, members in sorted(clusters.items(),
                                   key=lambda kv: -len(kv[1])):
            title = f"cluster {lab}  |  {len(members)} lemmas"
            if gloss and lab in gloss:
                title += f"  |  {gloss[lab]}"
            f.write(title + "\n")
            f.write("  " + "  ".join(f"{w}({freq[w]})" for w, _ in members)
                    + "\n\n")


def partition_stats(labels, vecs):
    labs = labels[labels != -1]
    sizes = np.bincount(labs) if len(labs) else np.array([0])
    sizes = sizes[sizes > 0]
    noise = int((labels == -1).sum())
    mask = labels != -1
    sil = (silhouette_score(vecs[mask], labels[mask], metric="cosine")
           if len(set(labels[mask])) > 1 else float("nan"))
    return {
        "clusters": len(sizes),
        "assigned": int(mask.sum()),
        "noise": noise,
        "size_min": int(sizes.min()),
        "size_median": float(np.median(sizes)),
        "size_max": int(sizes.max()),
        "silhouette_cosine": float(sil),
    }


# --------------------------------------------------------------------------
# 6. Optional: label clusters with Groq
# --------------------------------------------------------------------------
def groq_label(lemmas, api_key, model=GROQ_MODEL):
    """One short English label for a list of Ancient Greek lemmas."""
    prompt = (
        "These Ancient Greek lemmas were clustered together by word "
        "embeddings trained on Homer. Reply with ONLY a 2-5 word English "
        "label naming the semantic field they share (e.g. 'weapons and "
        "combat', 'kinship terms'). Lemmas: " + ", ".join(lemmas)
    )
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 20,
        }).encode(),
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["choices"][0]["message"]["content"].strip()


def label_all_clusters(clusters, api_key):
    import time
    gloss = {}
    for lab, members in clusters.items():
        try:
            gloss[lab] = groq_label([w for w, _ in members[:20]], api_key)
        except Exception as exc:                       # rate limit etc.
            print(f"  labelling cluster {lab} failed: {exc}")
        time.sleep(0.5)
    return gloss


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    rng = np.random.default_rng(SEED)

    print("1) Loading corpus ...")
    sentences = load_sentences(CSV_FILES)
    n_tokens = sum(len(s) for s in sentences)
    print(f"   total: {len(sentences)} sentences, {n_tokens} tokens")

    print("2) Training FastText ...")
    model = train_fasttext(sentences)
    model.save(str(OUTPUT_DIR / "homer_fasttext.model"))

    print("3) Building clustering vocabulary ...")
    vocab, vecs, freq = build_vocab(sentences, model)
    print(f"   {len(vocab)} content lemmas (freq >= {MIN_FREQ})")

    print("4) HDBSCAN ...")
    hdb_labels = run_hdbscan(vecs)
    hdb_stats = partition_stats(hdb_labels, vecs)
    print(f"   {hdb_stats['clusters']} clusters, "
          f"{hdb_stats['noise']} noise lemmas "
          f"({hdb_stats['noise']/len(vocab):.0%})")

    print("5) Leiden ...")
    graph = build_knn_graph(vecs)
    sweep_lines = []
    for res in LEIDEN_SWEEP:
        m, q = run_leiden(graph, res)
        n_c = len(set(m))
        sweep_lines.append(f"   resolution={res:<4}  ->  {n_c:4d} communities"
                           f"  (modularity {q:.3f})")
        print(sweep_lines[-1])
    lei_labels, lei_mod = run_leiden(graph, LEIDEN_RESOLUTION)
    lei_stats = partition_stats(lei_labels, vecs)
    print(f"   using resolution={LEIDEN_RESOLUTION}: "
          f"{lei_stats['clusters']} communities")

    # ---- agreement between the two partitions (on HDBSCAN-assigned lemmas)
    mask = hdb_labels != -1
    ari = adjusted_rand_score(hdb_labels[mask], lei_labels[mask])
    ami = adjusted_mutual_info_score(hdb_labels[mask], lei_labels[mask])

    print("6) Writing outputs ...")
    hdb_clusters = cluster_members_by_centrality(vocab, vecs, hdb_labels)
    lei_clusters = cluster_members_by_centrality(vocab, vecs, lei_labels)

    gloss_hdb = gloss_lei = None
    if GROQ_API_KEY:
        print("   labelling clusters via Groq ...")
        gloss_hdb = label_all_clusters(hdb_clusters, GROQ_API_KEY)
        gloss_lei = label_all_clusters(lei_clusters, GROQ_API_KEY)

    write_cluster_file(OUTPUT_DIR / "clusters_hdbscan.txt",
                       hdb_clusters, freq, "HDBSCAN", gloss_hdb)
    write_cluster_file(OUTPUT_DIR / "clusters_leiden.txt",
                       lei_clusters, freq, "Leiden", gloss_lei)

    pd.DataFrame({
        "lemma": vocab,
        "frequency": [freq[w] for w in vocab],
        "hdbscan_cluster": hdb_labels,        # -1 = noise
        "leiden_cluster": lei_labels,
    }).to_csv(OUTPUT_DIR / "lemma_clusters.csv", index=False,
              encoding="utf-8-sig")

    report = [
        "HDBSCAN vs Leiden — candidate semantic fields in Homer",
        "=" * 60,
        f"corpus: {len(sentences)} sentences, {n_tokens} tokens",
        f"clustered vocabulary: {len(vocab)} lemmas (freq >= {MIN_FREQ}, "
        f"function words excluded)",
        "",
        f"HDBSCAN (min_cluster_size={HDBSCAN_MIN_CLUSTER_SIZE}, "
        f"min_samples={HDBSCAN_MIN_SAMPLES}, {HDBSCAN_SELECTION}): "
        + json.dumps(hdb_stats, indent=2),
        "",
        f"Leiden (kNN k={KNN_K}, resolution={LEIDEN_RESOLUTION}, "
        f"modularity {lei_mod:.3f}): " + json.dumps(lei_stats, indent=2),
        "",
        "Leiden resolution sweep:",
        *sweep_lines,
        "",
        f"Agreement on the {int(mask.sum())} lemmas HDBSCAN assigned:",
        f"  adjusted Rand index        = {ari:.3f}",
        f"  adjusted mutual information = {ami:.3f}",
    ]
    (OUTPUT_DIR / "comparison_report.txt").write_text(
        "\n".join(report), encoding="utf-8")
    print("\n".join(report))
    print(f"\nDone. Outputs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
