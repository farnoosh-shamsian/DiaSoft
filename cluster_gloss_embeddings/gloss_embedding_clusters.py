# Emergent semantic fields for Homer via gloss embeddings clustering
# all-MiniLM-L6-v2 sentence embeddings of the glosses (the same model as the LSJ social-relations experiments, already in the local HF cache)
#-> two complementary clusterings:
#a) UMAP + HDBSCAN     : flat fields, number of clusters found automatically, outliers allowed
#b) Ward hierarchical  : a dendrogram over the same vectors, cut at several granularities (K in WARD_CUTS) — the nested taxonomy of the vocabulary
# Every cluster is auto-named by c-TF-IDF over its members' glosses (the label is derived from the data, not supplied).

import argparse
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

import requests

import numpy as np
import pandas as pd
import umap
from scipy.cluster.hierarchy import linkage, fcluster
from sentence_transformers import SentenceTransformer
from sklearn.cluster import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer

from cltk.alphabet.text_normalization import cltk_normalize
from cltk.stops.grc import STOPS as CLTK_GRC_STOPS

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Configuration

HERE       = Path(__file__).parent          
REPO       = HERE.parent
CSV_FILES  = [REPO / "homer_corpus" / "iliad_alignments.csv",
              REPO / "homer_corpus" / "odyssey_alignments.csv"]
LSJ_CEX    = REPO / "lsj_semantic_search" / "lsj_chicago.cex"
AGWN_CACHE = HERE / "agwn_cache.json"       

SEED       = 42
MIN_FREQ   = 5              
MODEL_NAME = "all-MiniLM-L6-v2"

# MAX_SENSES takes first N English senses per LSJ entry. 4 should cover most Homeric senses.

MAX_SENSES      = 4         
MAX_GLOSS_WORDS = 60

UMAP_DIMS      = 15
UMAP_NEIGHBORS = 15
HDB_MIN_CLUSTER_SIZE = 8
HDB_MIN_SAMPLES      = 3
HDB_SELECTION        = "leaf"

WARD_CUTS = [12, 25, 50, 100, 150, 200, 250]   
LABEL_TERMS = 4                 

ARTIFACTS = {"θυοτε", "οτηερ", "υνκνοων", "ηψπηεν"}
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
LATIN_LETTER = re.compile(r"[A-Za-z]")
BOLD_SPAN    = re.compile(r"\*\*(.+?)\*\*")
LENGTH_MARKS = {0x0304, 0x0306}          
# combining macron, combining breve, marks ignored for RELAXED matching + diaeresis + iota subscript
RELAXED_MARKS = LENGTH_MARKS | {0x0308, 0x0345}
TRAILING_DIGIT = re.compile(r"^(.*?)(\d+)$")


# Homer vocabulary (same loader as cltk_semantic_pipeline.py)
def load_lemma_frequencies():
    freq = Counter()
    for path in CSV_FILES:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))
        header_idx = next(i for i, r in enumerate(rows) if "Lemmas" in r)
        lem_cols = [i for i, c in enumerate(rows[header_idx])
                    if c.strip() == "Lemmas"]
        for row in rows[header_idx + 1:]:
            raw = ""
            for col in reversed(lem_cols):
                if len(row) > col and row[col].strip():
                    raw = row[col]
                    break
            for t in raw.split():
                norm = cltk_normalize(t.strip())
                if norm in ARTIFACTS or not GREEK_LETTER.search(norm):
                    continue
                freq[norm] += 1
    return freq


def build_stoplist():
    return ({cltk_normalize(w) for w in CLTK_GRC_STOPS}
            | {cltk_normalize(w) for w in HOMERIC_STOPS})


# LSJ gloss extraction
def strip_length_marks(word):
    decomposed = unicodedata.normalize("NFD", word)
    kept = "".join(ch for ch in decomposed if ord(ch) not in LENGTH_MARKS)
    return unicodedata.normalize("NFC", kept)


def relaxed_key(word):
    decomposed = unicodedata.normalize("NFD", word)
    kept = "".join(ch for ch in decomposed if ord(ch) not in RELAXED_MARKS)
    return unicodedata.normalize("NFC", kept)

def english_spans(entry_md):
    out = []
    for span in BOLD_SPAN.findall(entry_md):
        latin = len(LATIN_LETTER.findall(span))
        greek = len(GREEK_LETTER.findall(span))
        if latin >= 3 and latin > greek:
            s = span.strip(" ,;:.—-")
            if s and s not in out:
                out.append(s)
        if len(out) >= MAX_SENSES:
            break
    return out


def load_lsj():
    lsj, lsj_rel = defaultdict(list), defaultdict(list)
    n_entries = 0
    with open(LSJ_CEX, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("#", 3)
            if len(parts) < 4 or not parts[1].startswith("urn:"):
                continue
            n_entries += 1
            raw_hw = parts[2].strip().strip("·—").replace("-", "")
            hw = strip_length_marks(cltk_normalize(raw_hw))
            senses = english_spans(parts[3])
            if hw and senses:
                gloss = "; ".join(senses)
                gloss = " ".join(gloss.split()[:MAX_GLOSS_WORDS])
                lsj[hw].append(gloss)
                lsj_rel[relaxed_key(hw)].append(gloss)
    return lsj, lsj_rel, n_entries


def lemma_gloss(lemma, lsj, lsj_rel, agwn):
#(gloss, source) for a treebank lemma; ('', 'none') if not found.
    base, digit = lemma, None
    m = TRAILING_DIGIT.match(lemma)
    if m:
        base, digit = m.group(1), int(m.group(2))
    entries = lsj.get(strip_length_marks(base), [])
    source = "lsj"
    if not entries:
        entries = lsj_rel.get(relaxed_key(base), [])
        source = "lsj (relaxed match)"
    if entries:
        if digit and digit - 1 < len(entries):
            return entries[digit - 1], f"{source} (homograph {digit})"
        if digit:                      # digit beyond entries: combine all
            return " ; ".join(entries)[:400], f"{source} (homographs merged)"
        return entries[0], source
    info = agwn.get(lemma, {})
    if info.get("found") and info.get("gloss"):
        return info["gloss"], "agwn"
    return "", "none"


#  Ancient Greek WordNet fetch-on-miss (extends the shared cache) 
AGWN_BASE = "https://greekwordnet.chs.harvard.edu/api/lemmas/"
_tl = threading.local()


def _session():
    if not hasattr(_tl, "s"):
        _tl.s = requests.Session()
    return _tl.s


def agwn_fetch(lemma):
    url = AGWN_BASE + urllib.parse.quote(lemma) + "/synsets/"
    for attempt in (1, 2):
        try:
            r = _session().get(url, timeout=30)
            if r.status_code != 200:
                continue
            data = r.json()
            semfields, gloss = [], ""
            for res in data.get("results", []):
                for sense_type, lst in (res.get("synsets") or {}).items():
                    for syn in lst or []:
                        for sf in syn.get("semfield") or []:
                            if sf.get("english"):
                                semfields.append(sf["english"])
                        if not gloss and sense_type == "literal":
                            gloss = syn.get("gloss") or ""
            return {"found": bool(data.get("results")),
                    "semfields": semfields, "gloss": gloss[:120]}
        except Exception:
            if attempt == 2:
                return {"found": False, "semfields": [], "gloss": "",
                        "error": True}
    return {"found": False, "semfields": [], "gloss": "", "error": True}


def extend_agwn_cache(agwn, lemmas):
    todo = [w for w in lemmas if w not in agwn]
    if not todo:
        return
    print(f"   AGWN fetch-on-miss: {len(todo)} lemmas ...")
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(agwn_fetch, w): w for w in todo}
        for fut in as_completed(futures):
            agwn[futures[fut]] = fut.result()
            done += 1
            if done % 500 == 0:
                print(f"   AGWN: {done}/{len(todo)}")
    AGWN_CACHE.write_text(json.dumps(agwn, ensure_ascii=False),
                          encoding="utf-8")
    n_err = sum(1 for w in todo if agwn[w].get("error"))
    if n_err:
        print(f"   AGWN: WARNING — {n_err} lookups failed (network)")


# Clustering
def run_umap_hdbscan(vecs):
    reduced = umap.UMAP(n_components=UMAP_DIMS, n_neighbors=UMAP_NEIGHBORS,
                        min_dist=0.0, metric="cosine",
                        random_state=SEED).fit_transform(vecs)
    labels = HDBSCAN(min_cluster_size=HDB_MIN_CLUSTER_SIZE,
                     min_samples=HDB_MIN_SAMPLES,
                     cluster_selection_method=HDB_SELECTION,
                     ).fit(reduced).labels_
    return labels


def run_ward(vecs):
    Z = linkage(vecs, method="ward")
    return {k: fcluster(Z, t=k, criterion="maxclust") for k in WARD_CUTS}


# c-TF-IDF cluster naming (label emerges from members' glosses)
def ctfidf_labels(cluster_ids, glosses, top=LABEL_TERMS):
    docs, keys = [], []
    for lab in sorted(set(cluster_ids)):
        if lab == -1:
            continue
        keys.append(lab)
        docs.append(" ".join(g for g, l in zip(glosses, cluster_ids)
                             if l == lab))
    if not keys:
        return {}
    cv = CountVectorizer(stop_words="english", ngram_range=(1, 2),
                         token_pattern=r"(?u)\b[a-z][a-z]+\b")
    tf = cv.fit_transform(docs).toarray().astype(float)
    tf_norm = tf / np.maximum(tf.sum(axis=1, keepdims=True), 1)
    df = (tf > 0).sum(axis=0)
    idf = np.log(1 + len(keys) / np.maximum(df, 1))
    scores = tf_norm * idf
    vocab = np.array(cv.get_feature_names_out())
    labels = {}
    for i, lab in enumerate(keys):
        order = np.argsort(-scores[i])
        terms, seen = [], set()
        for j in order:
            term = vocab[j]
            if scores[i, j] <= 0:
                break
            if any(t in term or term in t for t in seen):
                continue        # skip near-duplicates like 'wine'/'wine skin'
            seen.add(term)
            terms.append(term)
            if len(terms) >= top:
                break
        labels[lab] = ", ".join(terms) if terms else "(unnamed)"
    return labels


# Reporting
def members_by_centrality(idx_by_cluster, vecs):
    out = {}
    for lab, idx in idx_by_cluster.items():
        idx = np.asarray(idx)
        centroid = vecs[idx].mean(axis=0)
        centroid /= np.linalg.norm(centroid)
        sims = vecs[idx] @ centroid
        out[lab] = idx[np.argsort(-sims)]
    return out


def group_indices(cluster_ids):
    groups = defaultdict(list)
    for i, lab in enumerate(cluster_ids):
        if lab != -1:
            groups[lab].append(i)
    return groups


def write_cluster_file(path, cluster_ids, labels, vecs, lemmas, freqs,
                       glosses, title):
    groups = members_by_centrality(group_indices(cluster_ids), vecs)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title}: {len(groups)} clusters — names are c-TF-IDF "
                f"terms from members' own glosses (emergent, not "
                f"predefined)\n# members sorted by centrality; format: "
                f"lemma (frequency): gloss\n\n")
        for lab, idx in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            f.write(f"cluster {lab}  |  {len(idx)} lemmas  |  "
                    f"{labels.get(lab, '(unnamed)')}\n")
            for i in idx:
                f.write(f"  {lemmas[i]} ({freqs[i]}): {glosses[i][:90]}\n")
            f.write("\n")


# Main
def main(min_freq=MIN_FREQ, suffix=""):
    sfx = f"_{suffix}" if suffix else ""
    print("1) Homer vocabulary ...")
    freq = load_lemma_frequencies()
    stops = build_stoplist()
    vocab = [w for w, c in freq.most_common()
             if c >= min_freq and w not in stops]
    print(f"   {len(vocab)} content lemmas (freq >= {min_freq})")

    print("2) LSJ glosses ...")
    lsj, lsj_rel, n_entries = load_lsj()
    print(f"   {n_entries} LSJ entries, {len(lsj)} glossed headwords")
    agwn = json.loads(AGWN_CACHE.read_text(encoding="utf-8"))

    # fetch AGWN entries for lemmas LSJ cannot gloss and the cache lacks
    lsj_missing = [w for w in vocab
                   if lemma_gloss(w, lsj, lsj_rel, {})[1] == "none"]
    extend_agwn_cache(agwn, lsj_missing)

    rows = []
    for w in vocab:
        gloss, source = lemma_gloss(w, lsj, lsj_rel, agwn)
        rows.append((w, freq[w], gloss, source))
    n_lsj = sum(1 for r in rows if r[3].startswith("lsj"))
    n_agwn = sum(1 for r in rows if r[3] == "agwn")
    unglossed = [r for r in rows if r[3] == "none"]
    glossed = [r for r in rows if r[3] != "none"]
    print(f"   glosses: {n_lsj} LSJ, {n_agwn} AGWN fallback, "
          f"{len(unglossed)} unglossed (excluded)")

    lemmas = [r[0] for r in glossed]
    freqs = [r[1] for r in glossed]
    glosses = [r[2] for r in glossed]
    sources = [r[3] for r in glossed]

    print(f"3) Embedding {len(glosses)} glosses with {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)
    vecs = model.encode(glosses, batch_size=128, show_progress_bar=False,
                        normalize_embeddings=True).astype(np.float64)

    print("4) UMAP + HDBSCAN over gloss embeddings ...")
    hdb = run_umap_hdbscan(vecs)
    n_clusters = len(set(hdb)) - (1 if -1 in hdb else 0)
    n_noise = int((hdb == -1).sum())
    print(f"   {n_clusters} fields, {n_noise} outliers "
          f"({n_noise / len(lemmas):.0%})")

    print("5) Ward hierarchy (cuts at "
          + ", ".join(map(str, WARD_CUTS)) + ") ...")
    ward = run_ward(vecs)

    print("6) Naming clusters (c-TF-IDF over member glosses) ...")
    hdb_names = ctfidf_labels(hdb, glosses)
    ward_names = {k: ctfidf_labels(ward[k], glosses) for k in WARD_CUTS}

    print("7) Writing outputs ...")
    write_cluster_file(HERE / f"clusters_hdbscan_gloss{sfx}.txt", hdb,
                       hdb_names, vecs, lemmas, freqs, glosses,
                       "HDBSCAN over gloss embeddings")
    for k in WARD_CUTS:
        write_cluster_file(HERE / f"clusters_ward_k{k}{sfx}.txt", ward[k],
                           ward_names[k], vecs, lemmas, freqs, glosses,
                           f"Ward cut at K={k}")

    df = pd.DataFrame({
        "lemma": lemmas, "frequency": freqs,
        "gloss_source": sources, "gloss": glosses,
        "hdbscan_cluster": hdb,
        "hdbscan_label": [hdb_names.get(l, "(outlier)") for l in hdb],
    })
    for k in WARD_CUTS:
        df[f"ward_{k}"] = ward[k]
        df[f"ward_{k}_label"] = [ward_names[k][l] for l in ward[k]]
    df.to_csv(HERE / f"lemma_gloss_fields{sfx}.csv", index=False,
              encoding="utf-8-sig")

    with open(HERE / f"unglossed_lemmas{sfx}.txt", "w",
              encoding="utf-8") as f:
        f.write("# lemmas with no LSJ or AGWN gloss (excluded from "
                "clustering; mostly proper names)\n")
        for w, c, _, _ in sorted(unglossed, key=lambda r: -r[1]):
            f.write(f"{w} ({c})\n")

    report = [
        "Gloss-embedding clustering — emergent semantic fields in Homer",
        "=" * 64,
        f"vocabulary: {len(vocab)} content lemmas (freq >= {min_freq}); "
        f"{len(glossed)} glossed and clustered, {len(unglossed)} excluded "
        f"(no gloss; mostly proper names — see unglossed_lemmas.txt)",
        f"gloss sources: {n_lsj} LSJ (first {MAX_SENSES} English senses), "
        f"{n_agwn} Ancient Greek WordNet fallback",
        f"embeddings: {MODEL_NAME} over English glosses, unit-normalized",
        "",
        f"UMAP({UMAP_DIMS}d, cosine) + HDBSCAN(min_cluster_size="
        f"{HDB_MIN_CLUSTER_SIZE}, {HDB_SELECTION}): {n_clusters} fields, "
        f"{n_noise} outliers ({n_noise / len(lemmas):.0%})",
        "Ward hierarchy cuts: " + ", ".join(
            f"K={k}" for k in WARD_CUTS) + " (same vectors, nested "
        "taxonomy — pick the granularity you like)",
        "",
        "Caveats:",
        " - An LSJ gloss covers a word's whole history, not only Homer;",
        "   first senses are usually Homeric (LSJ orders historically),",
        "   but some anachronistic senses leak in.",
        " - Treebank homograph digits are mapped to the Nth LSJ homograph",
        "   entry — a heuristic (see gloss_source column).",
        " - AGWN fallback glosses are auto-projected and noisy.",
        " - Proper names are mostly excluded (no lexicon gloss), which is",
        "   usually what you want for semantic fields.",
    ]
    (HERE / f"gloss_report{sfx}.txt").write_text("\n".join(report),
                                                 encoding="utf-8")
    print("\n".join(report))
    print(f"\nDone. Outputs in {HERE}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-freq", type=int, default=MIN_FREQ,
                    help="cluster only lemmas occurring at least this often")
    ap.add_argument("--suffix", default="",
                    help="suffix appended to every output filename "
                         "(default: derived from --min-freq)")
    args = ap.parse_args()
    suffix = args.suffix or (f"freq_limit_{args.min_freq}"
                             if args.min_freq > 1 else "no-freq-limit")
    main(min_freq=args.min_freq, suffix=suffix)
