#topic modeling as a syntax-AWARE supporting tool for frame semantics on Homer.

#Three products: 1.TYPE-SCENE discovery 2.DEPENDENCY-TUPLE topics 3.PER-BOOK PREVALENCE

#Reuses treebank.py (token table + predicate-argument tuples) and the CLTK + Homeric stoplist from the gloss script.

import argparse
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import treebank as tb

HERE = Path(__file__).parent
REPO = HERE.parent
GLOSS_MODULE = REPO / "cluster_gloss_embeddings" / "gloss_embedding_clusters.py"
OUTPUT_DIR = HERE / "topic_output"

SEED = 42
N_TOPICS = 20
WINDOW = 30          
CONTENT_POS = {"n", "v", "a"}   
TOP_TERMS = 12

# Greek seed lemmas per DiaSoft social-relation category (anchors for CorEx).
# Mirrors the 11 categories of "lsj_semantic_search". Only lemmas present in the corpus vocab are used.
CATEGORY_SEEDS = {
    "kinship_family":       ["πατήρ", "μήτηρ", "υἱός", "θυγάτηρ", "τέκνον", "κασίγνητος"],
    "marriage":             ["γάμος", "ἄλοχος", "νύμφη", "μνηστήρ", "ἀκοίτης"],
    "friendship_affection": ["φίλος", "ἑταῖρος", "φιλέω", "ἠθεῖος"],
    "hostility_enmity":     ["ἐχθρός", "δυσμενής", "χόλος", "ἔρις", "μῆνις", "κότος"],
    "hospitality_xenia":    ["ξεῖνος", "ξενίη", "δῶρον", "δαίς", "ἱκέτης"],
    "erotic":               ["ἔρος", "φιλότης", "εὐνή", "ἵμερος"],
    "rank_kingship_rule":   ["βασιλεύς", "ἄναξ", "σκῆπτρον", "τιμή", "γέρας"],
    "military_rank":        ["ἡγεμών", "στρατός", "λόχος", "πρόμαχος"],
    "servitude_slavery":    ["δμώς", "δούλη", "θεράπων", "ἀμφίπολος"],
    "messenger_herald":     ["κῆρυξ", "ἄγγελος", "ἀγγελίη", "πομπός"],
    "civic_community":      ["δῆμος", "ἀγορή", "λαός", "βουλή"],
}


def load_gloss_module():
    spec = importlib.util.spec_from_file_location("gloss_mod", GLOSS_MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Passage-window documents
def content_windows(tok, stops):
    #Return (docs, meta): docs are space-joined content lemmas per ~WINDOW-line window; meta rows carry (work, book, window).
    tok = tok[tok["pos"].isin(CONTENT_POS) & tok["line"].notna()].copy()
    tok = tok[tok["lemma"].astype(bool)]
    buckets = defaultdict(list)
    for work, book, line, lemma in zip(tok["work"], tok["book"],
                                       tok["line"], tok["lemma"]):
        if lemma in stops or lemma in tb.ARTIFACTS:
            continue
        if not tb.GREEK_LETTER.search(lemma):
            continue
        win = int(line) // WINDOW
        buckets[(work, int(book), win)].append(lemma)
    docs, meta = [], []
    for key, lemmas in buckets.items():
        if len(lemmas) >= 5:               # skip near-empty windows
            docs.append(" ".join(lemmas))
            meta.append(key)
    meta = pd.DataFrame(meta, columns=["work", "book", "window"])
    return docs, meta


def tuple_windows(pa, stops):
    #verb>object" tuple documents per window (dependency-tuple topics).
    buckets = defaultdict(list)
    for _i, r in pa.iterrows():
        if r["line"] is None or pd.isna(r["line"]) or not r["obj"]:
            continue
        v = r["verb_lemma"]
        if v in stops:
            continue
        win = int(r["line"]) // WINDOW
        for obj in r["obj"].split("|"):
            if obj and obj not in stops:
                buckets[(r["work"], int(r["book"]), win)].append(f"{v}>{obj}")
    docs, meta = [], []
    for key, toks in buckets.items():
        if len(toks) >= 4:
            docs.append(" ".join(toks))
            meta.append(key)
    return docs, pd.DataFrame(meta, columns=["work", "book", "window"])


# NMF topic model
def nmf_topics(docs, n_topics, top_terms=TOP_TERMS):
    vec = TfidfVectorizer(token_pattern=r"(?u)\S+", min_df=3)
    X = vec.fit_transform(docs)
    model = NMF(n_components=n_topics, init="nndsvd", random_state=SEED,
                max_iter=500)
    W = model.fit_transform(X)          # docs x topics
    H = model.components_               # topics x terms
    terms = np.array(vec.get_feature_names_out())
    topic_terms = [terms[np.argsort(-H[k])[:top_terms]].tolist()
                   for k in range(n_topics)]
    return W, topic_terms


def per_book_prevalence(W, meta, n_topics):
    #Sum topic weight per (work, book), row-normalized -> prevalence.
    rows = []
    key = meta[["work", "book"]].copy()
    for (work, book), grp in key.groupby(["work", "book"]):
        w = W[grp.index].sum(axis=0)
        s = w.sum()
        rows.append([work, book] + list(w / s if s else w))
    cols = ["work", "book"] + [f"topic_{k}" for k in range(n_topics)]
    return pd.DataFrame(rows, columns=cols).sort_values(["work", "book"])


# Anchored CorEx
def anchored_corex(docs, vocab_present):
    try:
        from corextopic import corextopic as ct
    except Exception:
        return None, "corextopic not installed — anchored model skipped"
    vec = CountVectorizer(token_pattern=r"(?u)\S+", min_df=3, binary=True)
    X = vec.fit_transform(docs)
    words = list(vec.get_feature_names_out())
    word_index = {w: i for i, w in enumerate(words)}
    anchors, names = [], []
    for cat, seeds in CATEGORY_SEEDS.items():
        present = [s for s in seeds if s in word_index]
        if present:
            anchors.append(present)
            names.append(cat)
    model = ct.Corex(n_hidden=len(anchors), seed=SEED)
    model.fit(X, words=words, anchors=anchors, anchor_strength=4)
    topics = []
    for i, name in enumerate(names):
        top = [w for w, _s, _ in model.get_topics(topic=i, n_words=12)]
        topics.append((name, top))
    return topics, None


# Main
def main(n_topics=N_TOPICS, window=WINDOW):
    global WINDOW
    WINDOW = window
    OUTPUT_DIR.mkdir(exist_ok=True)
    gloss = load_gloss_module()
    stops = gloss.build_stoplist()

    print("1) Building passage-window documents ...")
    tok = tb.build_token_table()
    docs, meta = content_windows(tok, stops)
    print(f"   {len(docs)} windows (~{window} lines each)")

    print(f"2) NMF type-scene topics (K={n_topics}) ...")
    W, topic_terms = nmf_topics(docs, n_topics)

    with open(OUTPUT_DIR / "type_scene_topics.txt", "w",
              encoding="utf-8") as f:
        f.write(f"# NMF type-scene topics: {n_topics} topics over "
                f"{len(docs)} passage windows (~{window} lines), "
                f"content lemmas (noun/verb/adj).\n\n")
        for k, terms in enumerate(topic_terms):
            f.write(f"topic {k:2d}: " + " ".join(terms) + "\n")
    for k, terms in enumerate(topic_terms):
        print(f"   topic {k:2d}: " + " ".join(terms[:8]))

    print("3) Per-book prevalence matrix ...")
    prev = per_book_prevalence(W, meta, n_topics)
    prev.to_csv(OUTPUT_DIR / "topic_prevalence_by_book.csv", index=False,
                encoding="utf-8-sig")

    print("4) Dependency-tuple (verb>object) topics ...")
    pa = tb.extract_predicate_arguments()
    tdocs, _tmeta = tuple_windows(pa, stops)
    if tdocs:
        _Wt, tuple_terms = nmf_topics(tdocs, min(n_topics, 15))
        with open(OUTPUT_DIR / "dependency_tuple_topics.txt", "w",
                  encoding="utf-8") as f:
            f.write(f"# NMF over verb>object tuples, {len(tdocs)} windows\n\n")
            for k, terms in enumerate(tuple_terms):
                f.write(f"topic {k:2d}: " + " ".join(terms) + "\n")
        print(f"   {len(tdocs)} tuple-windows -> "
              f"dependency_tuple_topics.txt")

    print("5) Optional anchored CorEx (11 social-relation categories) ...")
    corex_topics, note = anchored_corex(docs, None)
    if corex_topics:
        with open(OUTPUT_DIR / "anchored_category_topics.txt", "w",
                  encoding="utf-8") as f:
            f.write("# Anchored CorEx topics seeded from the 11 DiaSoft "
                    "social-relation categories (Greek seed lemmas).\n\n")
            for name, terms in corex_topics:
                f.write(f"{name}: " + " ".join(terms) + "\n")
        print("   wrote anchored_category_topics.txt")
    else:
        print(f"   {note}")

    print(f"\nDone. Outputs in {OUTPUT_DIR}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics", type=int, default=N_TOPICS)
    ap.add_argument("--window", type=int, default=WINDOW)
    args = ap.parse_args()
    main(n_topics=args.topics, window=args.window)
