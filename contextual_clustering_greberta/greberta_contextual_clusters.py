"""
Semantic clustering of Homer from contextual embeddings of an Ancient Greek RoBERTa.

Corpus-only pipeline: nothing from LSJ, AGWN, the treebanks or any earlier analysis
is used. The only inputs are the two Homer alignment CSVs (Greek text + Lemmas).

  1. load aligned (token, lemma) sentences from the Iliad and Odyssey CSVs
  2. run bowphs/GreBerta (RoBERTa-base pretrained on Ancient Greek) over every
     sentence, mean-pool sub-words back to word level, average the last 4 layers
  3. average each lemma's contextual token vectors -> one "type" vector per lemma
  4. de-anisotropise the type space (centre + drop the top principal components)
  5. cluster: UMAP -> HDBSCAN (emergent fields) and Ward on cosine (fixed cuts)

Run:  $env:PYTHONIOENCODING='utf-8'; py "greberta_contextual_clusters.py"
"""

import os
import re
import sys
import json
import unicodedata
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel

sys.stdout.reconfigure(encoding="utf-8")

# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CORPUS = os.path.join(REPO, "homer_corpus")
OUT = os.path.join(HERE, "greberta_clusters_output")

MODEL_NAME = "bowphs/GreBerta"     # RoBERTa-base, Ancient Greek (Riemenschneider & Frank 2023)
LAYERS = (-1, -2, -3, -4)          # layers averaged into the token representation
BATCH = 16
MAX_LEN = 256                      # sentences are single-digit verse spans

MIN_FREQ = 5                       # a lemma needs this many attestations to be clustered
DROP_TOP_PCS = 2                   # anisotropy correction ("all-but-the-top")
UMAP_DIM = 15
UMAP_NEIGHBORS = 15
HDBSCAN_MIN_SIZE = 5
WARD_CUTS = (40, 80, 150)
SEED = 42

# beta-code conversion artifacts sitting in the Lemmas column
ARTIFACTS = {"θυοτε", "οτηερ", "υνκνοων", "ηψπηεν", "αμπερσανδ", "εθυαλσ"}

# high-frequency function words: they dominate any distributional space and carry
# no semantic field, so they are held out of the clustering (still embedded, so
# they keep providing context for the content words around them).
FUNCTION_WORDS = {
    # article / demonstratives / pronouns
    "ὁ", "ὅς", "ὅς2", "οὗτος", "ὅδε", "ἐκεῖνος", "αὐτός", "ἐγώ", "σύ", "ἑ", "σφεῖς",
    "τίς", "τις", "ἄλλος", "ἕτερος", "ἀλλήλων", "ἑαυτοῦ", "ὅστις", "οἷος", "ὅσος",
    "τοῖος", "τόσος", "ἡμεῖς", "ὑμεῖς", "νώ", "σφωε", "μιν", "ἕ",
    # particles / conjunctions / negation
    "δέ", "καί", "τε", "μέν", "γάρ", "ἀλλά", "ἄρα", "γε", "δή", "οὖν", "μήν", "περ",
    "τοι", "νυ", "αὖ", "αὖτε", "αὐτάρ", "ἀτάρ", "ἠδέ", "ἰδέ", "εἰ", "ἐάν", "ἵνα",
    "ὅτι", "ὅτι2", "ὡς", "ὥστε", "ὅτε", "ἐπεί", "ἐπειδή", "ὄφρα", "ἕως", "πρίν",
    "οὐ", "μή", "οὐδέ", "μηδέ", "οὔτε", "μήτε", "οὐκί", "ἦ", "ἤ", "ἤ2", "ἄν", "κε",
    "κέν", "ἄν2", "ναί", "νή", "μά", "ἀτάρ", "ἠμέν", "εἴτε", "ὅπως", "ὄφρα",
    # prepositions / adverbs of place-time that are purely relational
    "ἐν", "εἰς", "ἐκ", "ἀπό", "ἐπί", "πρός", "παρά", "περί", "ὑπό", "ὑπέρ", "διά",
    "κατά", "μετά", "ἀνά", "σύν", "ἀμφί", "ἄνευ", "ἕνεκα", "πρό", "ἀντί", "ἄχρι",
    "νῦν", "τότε", "ἔτι", "ἤδη", "αἰεί", "πάλιν", "αὖθι", "ἐνθάδε", "ἔνθα", "ὧδε",
    "οὕτως", "μάλα", "λίαν", "πάνυ", "σφόδρα", "ποτέ", "πού", "πῶς", "πη",
    # copula / bleached verbs
    "εἰμί", "εἰμί2", "γίγνομαι",
}

CITATION = re.compile(r"\[[^\]]*\]")
STRIP_CHARS = "().,;:·’'\"«»—-–…!?*[]<>{}"


# --------------------------------------------------------------------------- #
# 1. corpus
# --------------------------------------------------------------------------- #
def read_alignment_csv(path):
    """The Iliad file has a junk URL line above the header and a duplicated
    column block; locate the real header by looking for 'Lemmas'."""
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    header = next(i for i, line in enumerate(lines) if "Lemmas" in line)
    df = pd.read_csv(path, skiprows=header)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def tokenize_line(text):
    text = CITATION.sub(" ", str(text))
    out = []
    for word in text.split():
        word = word.strip(STRIP_CHARS)
        if word:
            out.append(unicodedata.normalize("NFC", word))
    return out


def load_corpus():
    sentences = []
    stats = {}
    for work, fname in [("Iliad", "iliad_alignments.csv"),
                        ("Odyssey", "odyssey_alignments.csv")]:
        df = read_alignment_csv(os.path.join(CORPUS, fname))
        kept = dropped = 0
        for _, row in df.iterrows():
            greek, lemmas = row.get("Greek text"), row.get("Lemmas")
            if not isinstance(greek, str) or not isinstance(lemmas, str):
                continue
            words = tokenize_line(greek)
            lems = [unicodedata.normalize("NFC", l) for l in lemmas.split()]
            # only keep sentences where the two columns line up 1:1, otherwise a
            # token's vector would be filed under the wrong lemma
            if len(words) != len(lems) or not words:
                dropped += 1
                continue
            sentences.append({"work": work, "cite": row.get("Citation"),
                              "words": words, "lemmas": lems})
            kept += 1
        stats[work] = (kept, dropped)
    return sentences, stats


# --------------------------------------------------------------------------- #
# 2. contextual embeddings
# --------------------------------------------------------------------------- #
def embed_corpus(sentences, model_name=MODEL_NAME):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[embed] {model_name} on {device}")
    tok = AutoTokenizer.from_pretrained(model_name, add_prefix_space=True)
    model = AutoModel.from_pretrained(model_name, output_hidden_states=True).to(device).eval()

    dim = model.config.hidden_size
    sums = defaultdict(lambda: np.zeros(dim, dtype=np.float64))
    counts = Counter()

    with torch.inference_mode():
        for start in range(0, len(sentences), BATCH):
            batch = sentences[start:start + BATCH]
            enc = tok([s["words"] for s in batch], is_split_into_words=True,
                      truncation=True, max_length=MAX_LEN, padding=True,
                      return_tensors="pt")
            hidden = model(**{k: v.to(device) for k, v in enc.items()}).hidden_states
            reps = torch.stack([hidden[i] for i in LAYERS]).mean(0).cpu().numpy()

            for b, sent in enumerate(batch):
                word_ids = enc.word_ids(b)
                pieces = defaultdict(list)
                for pos, wid in enumerate(word_ids):
                    if wid is not None:
                        pieces[wid].append(reps[b, pos])
                for wid, vecs in pieces.items():
                    lemma = sent["lemmas"][wid]
                    sums[lemma] += np.mean(vecs, axis=0)
                    counts[lemma] += 1

            if (start // BATCH) % 50 == 0:
                done = min(start + BATCH, len(sentences))
                print(f"  {done}/{len(sentences)} sentences", flush=True)

    lemmas = sorted(counts)
    matrix = np.vstack([sums[l] / counts[l] for l in lemmas]).astype(np.float32)
    return lemmas, matrix, counts


# --------------------------------------------------------------------------- #
# 3. post-processing of the type space
# --------------------------------------------------------------------------- #
def l2(x):
    return x / np.clip(np.linalg.norm(x, axis=1, keepdims=True), 1e-9, None)


def remove_top_pcs(x, k):
    """Contextual embedding spaces are strongly anisotropic; dropping the first
    few principal components (Mu & Viswanath 2018) is what makes cosine
    similarity in them behave semantically."""
    if k <= 0:
        return x
    centred = x - x.mean(0, keepdims=True)
    _, _, vt = np.linalg.svd(centred, full_matrices=False)
    top = vt[:k]
    return centred - (centred @ top.T) @ top


# --------------------------------------------------------------------------- #
# 4. clustering
# --------------------------------------------------------------------------- #
def cluster(vectors, lemmas, freqs):
    import umap
    from sklearn.cluster import HDBSCAN, AgglomerativeClustering

    print(f"[cluster] {len(lemmas)} lemmas x {vectors.shape[1]}d")
    reducer = umap.UMAP(n_components=UMAP_DIM, n_neighbors=UMAP_NEIGHBORS,
                        min_dist=0.0, metric="cosine", random_state=SEED)
    embedded = reducer.fit_transform(vectors)

    hdb = HDBSCAN(min_cluster_size=HDBSCAN_MIN_SIZE, min_samples=1,
                  cluster_selection_method="leaf")
    labels = hdb.fit_predict(embedded)

    result = pd.DataFrame({"lemma": lemmas, "freq": [freqs[l] for l in lemmas],
                           "hdbscan": labels})

    # Ward on the (normalised) type vectors: gives complete, tunable partitions
    # that do not leave a noise bucket, as a cross-check on HDBSCAN
    for k in WARD_CUTS:
        ward = AgglomerativeClustering(n_clusters=k, metric="cosine", linkage="average")
        result[f"ward_{k}"] = ward.fit_predict(vectors)

    # 2-D projection for plotting
    plot_xy = umap.UMAP(n_components=2, n_neighbors=UMAP_NEIGHBORS, min_dist=0.05,
                        metric="cosine", random_state=SEED).fit_transform(vectors)
    result["x"], result["y"] = plot_xy[:, 0], plot_xy[:, 1]
    return result, embedded


def describe_clusters(result, vectors, lemmas, column, path, top_n=25):
    index = {l: i for i, l in enumerate(lemmas)}
    lines = []
    groups = result[result[column] >= 0].groupby(column)
    order = sorted(groups.groups, key=lambda g: -len(groups.get_group(g)))
    for gid in order:
        members = groups.get_group(gid)
        idx = [index[l] for l in members["lemma"]]
        centroid = l2(vectors[idx].mean(0, keepdims=True))[0]
        sims = vectors[idx] @ centroid
        ranked = sorted(zip(members["lemma"], members["freq"], sims),
                        key=lambda t: -t[2])
        coherence = float(np.mean(sims))
        lines.append(f"\n=== {column} cluster {gid}  (n={len(idx)}, coherence={coherence:.3f}) ===")
        shown = ranked[:top_n]
        lines.append("  " + "  ".join(f"{lem}({freq})" for lem, freq, _ in shown))
        if len(ranked) > top_n:
            lines.append(f"  ... +{len(ranked) - top_n} more")
    noise = int((result[column] == -1).sum())
    header = [f"{column}: {len(order)} clusters, {noise} unassigned lemmas"]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(header + lines) + "\n")


def nearest_neighbours(vectors, lemmas, path, probes, k=12):
    index = {l: i for i, l in enumerate(lemmas)}
    sim = vectors @ vectors.T
    lines = []
    for probe in probes:
        if probe not in index:
            lines.append(f"{probe}: not in vocabulary")
            continue
        i = index[probe]
        order = np.argsort(-sim[i])[1:k + 1]
        lines.append(f"{probe:14s} -> " + ", ".join(f"{lemmas[j]} {sim[i, j]:.3f}" for j in order))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return lines


# --------------------------------------------------------------------------- #
def main():
    os.makedirs(OUT, exist_ok=True)
    np.random.seed(SEED)
    torch.manual_seed(SEED)

    sentences, stats = load_corpus()
    total_tokens = sum(len(s["words"]) for s in sentences)
    print(f"[corpus] {len(sentences)} aligned sentences, {total_tokens} tokens")
    for work, (kept, dropped) in stats.items():
        print(f"  {work}: {kept} kept, {dropped} dropped (token/lemma count mismatch)")

    cache = os.path.join(OUT, "lemma_vectors.npz")
    if os.path.exists(cache):
        print("[embed] reusing cached lemma vectors")
        z = np.load(cache, allow_pickle=True)
        lemmas, matrix = list(z["lemmas"]), z["matrix"]
        freqs = Counter(dict(zip(lemmas, z["freqs"].tolist())))
    else:
        lemmas, matrix, freqs = embed_corpus(sentences)
        np.savez_compressed(cache, lemmas=np.array(lemmas, dtype=object),
                            matrix=matrix,
                            freqs=np.array([freqs[l] for l in lemmas]))
    print(f"[embed] {len(lemmas)} distinct lemmas embedded")

    keep = [i for i, l in enumerate(lemmas)
            if freqs[l] >= MIN_FREQ and l not in FUNCTION_WORDS
            and l not in ARTIFACTS and any(ch.isalpha() for ch in l)]
    lemmas_kept = [lemmas[i] for i in keep]
    print(f"[filter] {len(lemmas_kept)} lemmas with freq>={MIN_FREQ}, "
          f"function words and beta-code artifacts removed")

    vectors = remove_top_pcs(matrix[keep], DROP_TOP_PCS)
    vectors = l2(vectors).astype(np.float32)

    result, _ = cluster(vectors, lemmas_kept, freqs)
    result.to_csv(os.path.join(OUT, "lemma_clusters.csv"), index=False,
                  encoding="utf-8-sig")

    for column in ["hdbscan"] + [f"ward_{k}" for k in WARD_CUTS]:
        describe_clusters(result, vectors, lemmas_kept, column,
                          os.path.join(OUT, f"clusters_{column}.txt"))

    probes = ["πόλεμος", "μάχη", "ἔγχος", "ναῦς", "θάλασσα", "πατήρ", "γυνή",
              "βασιλεύς", "θεός", "ἵππος", "φιλέω", "θυμός", "οἶνος", "δῶρον",
              "κτείνω", "βαίνω", "λέγω", "ὁράω", "καλός", "δεινός"]
    for line in nearest_neighbours(vectors, lemmas_kept,
                                   os.path.join(OUT, "nearest_neighbours.txt"), probes):
        print("  " + line)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(13, 11))
        labels = result["hdbscan"].values
        noise = labels == -1
        ax.scatter(result["x"][noise], result["y"][noise], s=4, c="#d0d0d0", lw=0)
        ax.scatter(result["x"][~noise], result["y"][~noise], s=8,
                   c=labels[~noise], cmap="tab20", lw=0)
        for _, row in result[~noise].nlargest(140, "freq").iterrows():
            ax.text(row["x"], row["y"], row["lemma"], fontsize=6.5)
        ax.set_title("Homer lemmas — GreBerta contextual embeddings (UMAP, HDBSCAN)")
        ax.set_xticks([]); ax.set_yticks([])
        fig.tight_layout()
        fig.savefig(os.path.join(OUT, "lemma_map.png"), dpi=190)
        print("[plot] lemma_map.png")
    except Exception as exc:  # plotting is optional
        print(f"[plot] skipped: {exc}")

    summary = {
        "model": MODEL_NAME,
        "sentences": len(sentences),
        "tokens": total_tokens,
        "lemmas_embedded": len(lemmas),
        "lemmas_clustered": len(lemmas_kept),
        "hdbscan_clusters": int(result["hdbscan"].max()) + 1,
        "hdbscan_noise": int((result["hdbscan"] == -1).sum()),
    }
    with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
