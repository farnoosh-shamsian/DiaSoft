# inducing candidate FRAMES for Homer from predicate-argument structure 
#Reuses treebank, existing FastText space, LSJ glosses + c-TF-IDF naming + Ward/UMAP-HDBSCAN clustering from "cluster_gloss_embeddings/gloss_embedding_clusters.py"

import argparse
import importlib.util
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import treebank as tb   # same folder (sys.path[0] when run as a script)
from gensim.models import FastText

# Configuration
HERE = Path(__file__).parent
REPO = HERE.parent
FASTTEXT_MODEL = (REPO / "clustering_homer" /
                  "semantic_fields_output_HDBSCAN_Leiden" / "homer_fasttext.model")
GLOSS_MODULE = REPO / "cluster_gloss_embeddings" / "gloss_embedding_clusters.py"
OUTPUT_DIR = HERE / "frame_output"

SEED = 42
MIN_FREQ = 5            
TOP_FILLERS = 8        
SLOTS = ("sbj", "obj") 


CACHED_MODEL = None   
FT_PARAMS = dict(vector_size=100, window=5, min_count=3, sg=1, negative=10,
                 sample=1e-4, epochs=80, min_n=3, max_n=6, seed=SEED, workers=1)


def treebank_lemma_sentences():
    tok = tb.build_token_table()
    sents = []
    for _sid, g in tok.groupby("sentence_id", sort=False):
        lemmas = [l for l in g.sort_values("word_id")["lemma"]
                  if l and l not in tb.ARTIFACTS and tb.GREEK_LETTER.search(l)]
        if lemmas:
            sents.append(lemmas)
    return sents


def train_or_load_fasttext(cache_path):
    if cache_path.exists():
        try:
            return FastText.load(str(cache_path))
        except Exception as exc:
            print(f"   cached model unreadable ({exc}); retraining ...")
    print("   training FastText on treebank lemma sequences ...")
    sents = treebank_lemma_sentences()
    model = FastText(sentences=sents, **FT_PARAMS)
    model.save(str(cache_path))
    return model


# Loading the reusable gloss/clustering module
def load_gloss_module():
    spec = importlib.util.spec_from_file_location("gloss_mod", GLOSS_MODULE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Verb argument profiles -> vectors
def slot_mean(counter, ft, stops):
    vecs, wts = [], []
    for lemma, c in counter.items():
        if lemma in stops:
            continue
        try:
            vecs.append(ft.wv[lemma])         
            wts.append(c)
        except KeyError:
            continue
    if not vecs:
        return None
    V = np.asarray(vecs, dtype=np.float64)
    w = np.asarray(wts, dtype=np.float64)
    m = (V * w[:, None]).sum(0) / w.sum()
    n = np.linalg.norm(m)
    return m / n if n > 0 else None


def build_verb_vectors(profiles, verbs, ft, stops):
    #Concatenating the per-slot mean vectors; keep only verbs with >=1 slot.
    dim = ft.wv.vector_size
    rows, kept = [], []
    for v in verbs:
        parts = [slot_mean(profiles[v][s], ft, stops) for s in SLOTS]
        if all(p is None for p in parts):
            continue                            # no usable participants
        vec = np.concatenate([p if p is not None else np.zeros(dim)
                              for p in parts])
        nrm = np.linalg.norm(vec)
        if nrm == 0:
            continue
        rows.append(vec / nrm)
        kept.append(v)
    return kept, np.vstack(rows)


# Selectional preferences per frame
def frame_fillers(cluster_ids, verbs, profiles, stops):
    agg = defaultdict(lambda: {s: Counter() for s in SLOTS})
    for v, lab in zip(verbs, cluster_ids):
        if lab == -1:
            continue
        for s in SLOTS:
            for filler, c in profiles[v][s].items():
                if filler not in stops:
                    agg[lab][s][filler] += c
    return agg


# Main
def main(min_freq=MIN_FREQ):
    OUTPUT_DIR.mkdir(exist_ok=True)
    print("Loading reusable gloss/clustering module ...")
    gloss = load_gloss_module()
    stops = gloss.build_stoplist()         

    print("1) Extracting predicate-argument tuples from the treebanks ...")
    pa = tb.extract_predicate_arguments()
    profiles = tb.verb_slot_fillers(pa, slots=SLOTS)
    verb_freq = pa["verb_lemma"].value_counts()
    # verbs frequent enough AND not themselves function/copula verbs
    verbs = [v for v in verb_freq.index
             if verb_freq[v] >= min_freq and v not in stops]
    print(f"   {len(pa):,} verb occurrences; "
          f"{len(verbs)} verb lemmas with freq >= {min_freq}")

    print("2) Building verb argument-profile vectors (FastText fillers) ...")
    ft = train_or_load_fasttext(OUTPUT_DIR / "homer_fasttext_treebank.model")
    verbs, vecs = build_verb_vectors(profiles, verbs, ft, stops)
    print(f"   {len(verbs)} verbs representable "
          f"(>=1 non-stoplist SBJ/OBJ filler), dim={vecs.shape[1]}")

    print("3) Clustering verbs into frames ...")
    hdb = gloss.run_umap_hdbscan(vecs)          # flat frames (primary)
    ward = gloss.run_ward(vecs)                 # nested taxonomy (cross-view)
    n_frames = len(set(hdb)) - (1 if -1 in hdb else 0)
    n_noise = int((hdb == -1).sum())
    print(f"   UMAP+HDBSCAN: {n_frames} frames, {n_noise} unassigned "
          f"({n_noise/len(verbs):.0%}); Ward cuts at {gloss.WARD_CUTS}")

    print("4) Naming frames (c-TF-IDF over member verbs' LSJ glosses) ...")
    lsj, lsj_rel, _ = gloss.load_lsj()
    v_gloss = [gloss.lemma_gloss(v, lsj, lsj_rel, {})[0] or "" for v in verbs]
    hdb_names = gloss.ctfidf_labels(hdb, v_gloss)

    print("5) Selectional preferences per frame ...")
    fillers = frame_fillers(hdb, verbs, profiles, stops)

    # write frames.txt
    groups = gloss.members_by_centrality(gloss.group_indices(hdb), vecs)
    with open(OUTPUT_DIR / "frames.txt", "w", encoding="utf-8") as f:
        f.write(f"# Induced Homeric frames: {n_frames} clusters of verbs "
                f"grouped by argument profile (SBJ+OBJ fillers).\n"
                f"# Frame names are c-TF-IDF terms from member verbs' LSJ "
                f"glosses. Verbs sorted by centrality.\n\n")
        for lab, idx in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            f.write(f"FRAME {lab}  |  {len(idx)} verbs  |  "
                    f"{hdb_names.get(lab, '(unnamed)')}\n")
            members = "  ".join(
                f"{verbs[i]}({int(verb_freq[verbs[i]])})" for i in idx)
            f.write(f"  verbs: {members}\n")
            for s, label in (("sbj", "SUBJECTS (Agent-ish)"),
                             ("obj", "OBJECTS (Patient-ish)")):
                top = fillers[lab][s].most_common(TOP_FILLERS)
                if top:
                    f.write(f"  {label}: "
                            + ", ".join(f"{w}({c})" for w, c in top) + "\n")
            f.write("\n")

    #  write frames.csv
    ward_primary = gloss.WARD_CUTS[1] if len(gloss.WARD_CUTS) > 1 else gloss.WARD_CUTS[0]
    df = pd.DataFrame({
        "verb": verbs,
        "frequency": [int(verb_freq[v]) for v in verbs],
        "frame_hdbscan": hdb,
        "frame_label": [hdb_names.get(l, "(unassigned)") for l in hdb],
        f"frame_ward_{ward_primary}": ward[ward_primary],
        "gloss": v_gloss,
        "top_subjects": ["; ".join(
            f"{w}({c})" for w, c in profiles[v]["sbj"].most_common(5)
            if w not in stops) for v in verbs],
        "top_objects": ["; ".join(
            f"{w}({c})" for w, c in profiles[v]["obj"].most_common(5)
            if w not in stops) for v in verbs],
    })
    df.to_csv(OUTPUT_DIR / "frames.csv", index=False, encoding="utf-8-sig")

    #  report
    report = [
        "Predicate-argument frame induction for Homer",
        "=" * 60,
        f"predicate-argument tuples: {len(pa):,} verb occurrences",
        f"verbs clustered: {len(verbs)} (freq >= {min_freq}, function verbs "
        f"excluded, >=1 non-stoplist SBJ/OBJ filler)",
        f"representation: [mean SBJ-filler | mean OBJ-filler] FastText vectors "
        f"({vecs.shape[1]}d), unit-normalized",
        f"UMAP+HDBSCAN: {n_frames} frames, {n_noise} unassigned "
        f"({n_noise/len(verbs):.0%})",
        f"Ward cross-view cuts: {gloss.WARD_CUTS}",
        "",
        "Outputs:",
        "  frames.txt   frames with member verbs + selectional preferences",
        "  frames.csv   verb -> frame id/label + its own top subjects/objects",
        "  ../predicate_arguments.csv  the raw tuple table (reusable)",
        "",
        "Caveats:",
        " - AGLDT relations are syntactic, not semantic roles; SBJ != Agent",
        "   under passive/middle voice (voice kept in predicate_arguments.csv",
        "   for later Agent/Patient refinement).",
        " - Fillers are embedded in the FastText space trained on Homer, so",
        "   frames group verbs whose participants PATTERN alike — a candidate",
        "   frame inventory, to be curated against LSJ / the 11 LSJ categories.",
        " - Pronoun / article fillers are excluded via the CLTK+Homeric stoplist.",
    ]
    (OUTPUT_DIR / "frame_report.txt").write_text("\n".join(report),
                                                 encoding="utf-8")
    print("\n".join(report))
    print(f"\nDone. Outputs in {OUTPUT_DIR}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-freq", type=int, default=MIN_FREQ,
                    help="minimum verb occurrences to cluster")
    args = ap.parse_args()
    main(min_freq=args.min_freq)
