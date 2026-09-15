#End-to-end unsupervised semantic-field discovery for Homer (Iliad + Odyssey)following the workflow: lemmatized corpus -> CLTK normalization/verification -> fastText embeddings -> UMAP + HDBSCAN clustering (Leiden community detection as a cross-check) -> automatic cluster labelling via the Ancient Greek WordNet (CHS Harvard) semantic fields.

import csv
import json
import re
import sys
import threading
import unicodedata
import urllib.parse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import igraph as ig
import umap
from gensim.models import FastText
from sklearn.cluster import HDBSCAN
from sklearn.metrics import (adjusted_rand_score, adjusted_mutual_info_score,
                             silhouette_score)
from sklearn.neighbors import NearestNeighbors

# --- CLTK: Greek-specific normalization + stopwords -------------------------
from cltk.alphabet.text_normalization import cltk_normalize
from cltk.stops.grc import STOPS as CLTK_GRC_STOPS

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Configuration
HERE       = Path(__file__).parent            # "clustering_homer"
REPO       = HERE.parent
CSV_FILES  = [REPO / "homer_corpus" / "iliad_alignments.csv",
              REPO / "homer_corpus" / "odyssey_alignments.csv"]
OUTPUT_DIR = HERE / "cltk_pipeline_output"

SEED = 42

# fastText
VECTOR_SIZE  = 100
WINDOW       = 5
MIN_COUNT    = 3
EPOCHS       = 80
MIN_N, MAX_N = 3, 6

# clustering vocabulary
MIN_FREQ = 5           

# UMAP (reduce before density clustering, per the standard recipe)
UMAP_DIMS       = 25
UMAP_NEIGHBORS  = 15
UMAP_MIN_DIST   = 0.0     

# HDBSCAN
HDB_MIN_CLUSTER_SIZE = 6
HDB_MIN_SAMPLES      = 3
HDB_SELECTION        = "leaf"   
# Leiden cross-check
KNN_K             = 15
LEIDEN_RESOLUTION = 3.0

# Ancient Greek WordNet API
AGWN_BASE    = "https://greekwordnet.chs.harvard.edu/api/lemmas/"
AGWN_THREADS = 8
AGWN_TIMEOUT = 30
AGWN_CACHE   = "agwn_cache.json"
LABEL_TOP_SEMFIELDS = 3      

# Treebank annotation artifacts: English words typed in Greek letters
ARTIFACTS = {"θυοτε", "οτηερ", "υνκνοων", "ηψπηεν"}

# Homeric / epic function words missing from CLTK's (Attic-oriented) list.
HOMERIC_STOPS = {
    "ὁ", "ὅς", "ὅδε", "οὗτος", "ἐκεῖνος", "κεῖνος", "αὐτός", "ἐγώ", "σύ",
    "ἕ", "μιν", "νιν", "σφεῖς", "τίς", "τις", "ὅστις", "ἐμός", "σός", "τεός",
    "ἑός", "ἡμέτερος", "ὑμέτερος", "σφέτερος", "ἀμός",
    "δέ", "τε", "καί", "μέν", "γάρ", "ἄρα", "ἄρ", "ῥα", "δή", "γε", "πέρ",
    "τοι", "νυ", "κε", "κεν", "ἄν", "οὖν", "γοῦν", "αὖ", "αὖτε", "ἦ", "μήν",
    "μάν", "θην", "ἀτάρ", "αὐτάρ", "ὦ", "περ",
    "οὐ", "μή", "οὐδέ", "μηδέ", "οὔτε", "μήτε", "οὐδείς", "μηδείς",
    "ἐν", "εἰς", "ἐκ", "ἀπό", "ἐπί", "κατά", "παρά", "πρός", "προτί", "ποτί",
    "ὑπό", "ὑπέρ", "περί", "ἀμφί", "ἀνά", "διά", "μετά", "σύν", "ξύν",
    "ἀντί", "πρό",
    "εἰ", "ὡς", "ὅτι", "ὅτι2", "ὅτε", "ἐπεί", "ἐπήν", "ἵνα", "ὄφρα", "ἤ",
    "ἠέ", "ἠδέ", "ἰδέ", "ἠμέν", "εἴτε", "ὅπως", "ὥστε", "ἕως", "πρίν",
    "ὁπότε", "ὁππότε", "εὖτε",
    "εἰμί",
}

GREEK_LETTER = re.compile(r"[Ͱ-Ͽἀ-῿]")


# 1+2. Load corpus with CLTK normalization
def normalize_lemma(tok: str) -> str:
    return cltk_normalize(tok.strip())


def load_sentences(paths):
    sentences, n_changed, n_dropped = [], 0, 0
    for path in paths:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        header_idx = next(i for i, r in enumerate(rows) if "Lemmas" in r)
        lem_cols = [i for i, c in enumerate(rows[header_idx])
                    if c.strip() == "Lemmas"]
        n = 0
        for row in rows[header_idx + 1:]:
            raw = ""
            for col in reversed(lem_cols):        # last Lemmas column wins
                if len(row) > col and row[col].strip():
                    raw = row[col]
                    break
            if not raw:
                continue
            toks = []
            for t in raw.split():
                norm = normalize_lemma(t)
                if norm != t:
                    n_changed += 1
                if norm in ARTIFACTS or not GREEK_LETTER.search(norm):
                    n_dropped += 1
                    continue
                toks.append(norm)
            if toks:
                sentences.append(toks)
                n += 1
        print(f"  {path.name}: {n} sentences")
    return sentences, n_changed, n_dropped


def build_stoplist():
    stops = {cltk_normalize(w) for w in CLTK_GRC_STOPS}
    stops |= {cltk_normalize(w) for w in HOMERIC_STOPS}
    return stops


# 3. fastText embeddings
def train_fasttext(sentences):
    return FastText(
        sentences=sentences,
        vector_size=VECTOR_SIZE, window=WINDOW, min_count=MIN_COUNT,
        sg=1, negative=10, sample=1e-4, epochs=EPOCHS,
        min_n=MIN_N, max_n=MAX_N,
        seed=SEED, workers=1,          # workers=1 => reproducible
    )


def build_vocab(sentences, model, stoplist):
    freq = Counter(t for s in sentences for t in s)
    vocab = [w for w, c in freq.most_common()
             if c >= MIN_FREQ and w not in stoplist and w in model.wv]
    vecs = np.vstack([model.wv[w] for w in vocab]).astype(np.float64)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    return vocab, vecs, freq


# 4. UMAP + HDBSCAN
def run_umap_hdbscan(vecs):
    reducer = umap.UMAP(
        n_components=UMAP_DIMS, n_neighbors=UMAP_NEIGHBORS,
        min_dist=UMAP_MIN_DIST, metric="cosine", random_state=SEED,
    )
    reduced = reducer.fit_transform(vecs)
    labels = HDBSCAN(
        min_cluster_size=HDB_MIN_CLUSTER_SIZE,
        min_samples=HDB_MIN_SAMPLES,
        cluster_selection_method=HDB_SELECTION,
    ).fit(reduced).labels_
    return labels, reduced


# 5. Leiden cross-check
def run_leiden(vecs, k=KNN_K, resolution=LEIDEN_RESOLUTION):
    nn = NearestNeighbors(n_neighbors=k + 1, metric="cosine").fit(vecs)
    dist, idx = nn.kneighbors(vecs)
    edges, weights = {}, {}
    for i in range(len(vecs)):
        for d, j in zip(dist[i, 1:], idx[i, 1:]):
            e = (min(i, j), max(i, j))
            w = max(1.0 - d, 1e-9)
            if e not in edges or w > weights[e]:
                edges[e] = e
                weights[e] = w
    g = ig.Graph(n=len(vecs), edges=list(edges.values()))
    g.es["weight"] = [weights[e] for e in edges.values()]
    part = g.community_leiden(objective_function="modularity",
                              weights="weight", resolution=resolution,
                              n_iterations=-1)
    return np.asarray(part.membership), part.modularity


# 6. Ancient Greek WordNet lookup + cluster labelling
_thread_local = threading.local()


def _session():
    if not hasattr(_thread_local, "s"):
        _thread_local.s = requests.Session()
    return _thread_local.s


def agwn_fetch(lemma):
    url = AGWN_BASE + urllib.parse.quote(lemma) + "/synsets/"
    for attempt in (1, 2):
        try:
            r = _session().get(url, timeout=AGWN_TIMEOUT)
            if r.status_code != 200:
                continue
            data = r.json()
            semfields, gloss = [], ""
            for res in data.get("results", []):
                syns = res.get("synsets") or {}
                for sense_type, lst in syns.items():
                    for syn in lst or []:
                        for sf in syn.get("semfield") or []:
                            name = sf.get("english")
                            if name:
                                semfields.append(name)
                        if not gloss and sense_type == "literal":
                            gloss = syn.get("gloss") or ""
            return {"found": bool(data.get("results")),
                    "semfields": semfields, "gloss": gloss[:120]}
        except Exception:
            if attempt == 2:
                return {"found": False, "semfields": [], "gloss": "",
                        "error": True}
    return {"found": False, "semfields": [], "gloss": "", "error": True}


def agwn_lookup_all(lemmas, cache_path):
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}          # partial/corrupt cache: refetch everything
    todo = [w for w in lemmas if w not in cache]
    print(f"   AGWN: {len(lemmas) - len(todo)} cached, {len(todo)} to fetch")
    if todo:
        done = 0
        with ThreadPoolExecutor(max_workers=AGWN_THREADS) as ex:
            futures = {ex.submit(agwn_fetch, w): w for w in todo}
            for fut in as_completed(futures):
                cache[futures[fut]] = fut.result()
                done += 1
                if done % 250 == 0:
                    print(f"   AGWN: {done}/{len(todo)} fetched")
                    cache_path.write_text(
                        json.dumps(cache, ensure_ascii=False),
                        encoding="utf-8")
        cache_path.write_text(json.dumps(cache, ensure_ascii=False),
                              encoding="utf-8")
    n_err = sum(1 for w in lemmas if cache.get(w, {}).get("error"))
    if n_err:
        print(f"   AGWN: WARNING — {n_err} lookups failed (network); "
              f"labels are partial")
    return cache


def label_clusters(clusters, agwn):
    labels, coverage = {}, {}
    for lab, members in clusters.items():
        votes = Counter()
        n_found = 0
        for w, _ in members:
            info = agwn.get(w, {})
            if info.get("found"):
                n_found += 1
            for sf in set(info.get("semfields", [])):
                votes[sf] += 1
        top = [f"{sf} ({c})" for sf, c in votes.most_common(LABEL_TOP_SEMFIELDS)
               if c >= 2]
        labels[lab] = "; ".join(top) if top else "(no shared semfield)"
        coverage[lab] = n_found / len(members) if members else 0.0
    return labels, coverage


# Reporting
def members_by_centrality(vocab, vecs, labels):
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


def write_cluster_file(path, clusters, freq, name, labels, coverage):
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {name}: {len(clusters)} clusters — label = Ancient Greek "
                f"WordNet semfields shared by members (votes in parens);\n"
                f"# coverage = share of members found in AGWN; member "
                f"frequency in parens; members sorted by centrality\n\n")
        for lab, members in sorted(clusters.items(), key=lambda kv: -len(kv[1])):
            f.write(f"cluster {lab}  |  {len(members)} lemmas  |  "
                    f"AGWN coverage {coverage[lab]:.0%}\n")
            f.write(f"  label: {labels[lab]}\n")
            f.write("  " + "  ".join(f"{w}({freq[w]})" for w, _ in members)
                    + "\n\n")


def partition_stats(labels, vecs):
    mask = labels != -1
    labs = labels[mask]
    sizes = np.bincount(labs) if len(labs) else np.array([0])
    sizes = sizes[sizes > 0]
    sil = (silhouette_score(vecs[mask], labels[mask], metric="cosine")
           if len(set(labels[mask])) > 1 else float("nan"))
    return {"clusters": len(sizes), "assigned": int(mask.sum()),
            "noise": int((~mask).sum()), "size_min": int(sizes.min()),
            "size_median": float(np.median(sizes)),
            "size_max": int(sizes.max()), "silhouette_cosine": float(sil)}


# Main
def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("1) Loading corpus (CLTK normalization) ...")
    sentences, n_changed, n_dropped = load_sentences(CSV_FILES)
    n_tokens = sum(len(s) for s in sentences)
    print(f"   {len(sentences)} sentences, {n_tokens} tokens; "
          f"{n_changed} tokens re-normalized, {n_dropped} artifacts dropped")

    stoplist = build_stoplist()
    print(f"   stoplist: {len(stoplist)} function words "
          f"(CLTK grc STOPS + Homeric supplement)")

    print("2) Training fastText ...")
    model = train_fasttext(sentences)
    model.save(str(OUTPUT_DIR / "homer_fasttext_cltk.model"))

    print("3) Building clustering vocabulary ...")
    vocab, vecs, freq = build_vocab(sentences, model, stoplist)
    print(f"   {len(vocab)} content lemmas (freq >= {MIN_FREQ})")

    print("4) UMAP + HDBSCAN ...")
    hdb_labels, reduced = run_umap_hdbscan(vecs)
    hdb_stats = partition_stats(hdb_labels, vecs)
    print(f"   {hdb_stats['clusters']} clusters, {hdb_stats['noise']} noise "
          f"({hdb_stats['noise'] / len(vocab):.0%})")

    print("5) Leiden cross-check ...")
    lei_labels, lei_mod = run_leiden(vecs)
    lei_stats = partition_stats(lei_labels, vecs)
    print(f"   {lei_stats['clusters']} communities (modularity {lei_mod:.3f})")

    mask = hdb_labels != -1
    ari = adjusted_rand_score(hdb_labels[mask], lei_labels[mask])
    ami = adjusted_mutual_info_score(hdb_labels[mask], lei_labels[mask])
    print(f"   agreement on HDBSCAN-assigned lemmas: "
          f"ARI={ari:.3f}, AMI={ami:.3f}")

    print("6) Ancient Greek WordNet lookup + labelling ...")
    # shared AGWN response cache (also used by the gloss-embedding pipeline)
    agwn = agwn_lookup_all(vocab,
                           REPO / "cluster_gloss_embeddings" / AGWN_CACHE)
    n_found = sum(1 for w in vocab if agwn.get(w, {}).get("found"))
    print(f"   {n_found}/{len(vocab)} lemmas found in AGWN "
          f"({n_found / len(vocab):.0%})")

    hdb_clusters = members_by_centrality(vocab, vecs, hdb_labels)
    lei_clusters = members_by_centrality(vocab, vecs, lei_labels)
    hdb_names, hdb_cov = label_clusters(hdb_clusters, agwn)
    lei_names, lei_cov = label_clusters(lei_clusters, agwn)

    print("7) Writing outputs ...")
    write_cluster_file(OUTPUT_DIR / "clusters_hdbscan_labeled.txt",
                       hdb_clusters, freq, "UMAP+HDBSCAN", hdb_names, hdb_cov)
    write_cluster_file(OUTPUT_DIR / "clusters_leiden_labeled.txt",
                       lei_clusters, freq, "Leiden", lei_names, lei_cov)

    pd.DataFrame({
        "lemma": vocab,
        "frequency": [freq[w] for w in vocab],
        "hdbscan_cluster": hdb_labels,
        "hdbscan_label": [hdb_names.get(l, "") if l != -1 else "(noise)"
                          for l in hdb_labels],
        "leiden_cluster": lei_labels,
        "leiden_label": [lei_names.get(l, "") for l in lei_labels],
        "in_agwn": [bool(agwn.get(w, {}).get("found")) for w in vocab],
        "agwn_semfields": ["; ".join(sorted(set(
            agwn.get(w, {}).get("semfields", [])))) for w in vocab],
        "agwn_gloss": [agwn.get(w, {}).get("gloss", "") for w in vocab],
    }).to_csv(OUTPUT_DIR / "cltk_lemma_clusters.csv", index=False,
              encoding="utf-8-sig")

    report = [
        "CLTK semantic pipeline — Homer (Iliad + Odyssey)",
        "=" * 60,
        f"corpus: {len(sentences)} sentences, {n_tokens} tokens",
        f"CLTK normalization: {n_changed} tokens re-normalized, "
        f"{n_dropped} artifacts/non-Greek dropped",
        f"stoplist: {len(stoplist)} entries (CLTK grc STOPS + Homeric)",
        f"clustered vocabulary: {len(vocab)} lemmas (freq >= {MIN_FREQ})",
        "",
        f"fastText: dim={VECTOR_SIZE}, window={WINDOW}, epochs={EPOCHS}, "
        f"sg=1, min_n..max_n={MIN_N}..{MAX_N}",
        f"UMAP: dims={UMAP_DIMS}, neighbors={UMAP_NEIGHBORS}, "
        f"min_dist={UMAP_MIN_DIST}, metric=cosine",
        "",
        "UMAP+HDBSCAN: " + json.dumps(hdb_stats, indent=2),
        "",
        f"Leiden (k={KNN_K}, resolution={LEIDEN_RESOLUTION}, "
        f"modularity {lei_mod:.3f}): " + json.dumps(lei_stats, indent=2),
        "",
        f"Agreement on the {int(mask.sum())} HDBSCAN-assigned lemmas:",
        f"  adjusted Rand index         = {ari:.3f}",
        f"  adjusted mutual information = {ami:.3f}",
        "",
        f"Ancient Greek WordNet: {n_found}/{len(vocab)} lemmas found "
        f"({n_found / len(vocab):.0%} coverage)",
    ]
    (OUTPUT_DIR / "cltk_report.txt").write_text("\n".join(report),
                                                encoding="utf-8")
    print("\n".join(report))
    print(f"\nDone. Outputs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
