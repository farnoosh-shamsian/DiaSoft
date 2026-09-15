# clustering_homer — unsupervised semantic-field discovery (CLTK pipeline)

This directory contains an end-to-end pipeline that induces candidate
**semantic fields** from the Homeric corpus (_Iliad_ + _Odyssey_) without any
supervision or predefined categories. Lemmatized text is embedded with
fastText, the embedding space is reduced with UMAP and clustered with HDBSCAN,
the result is cross-validated against a Leiden community-detection partition,
and every cluster is automatically labelled with the semantic fields recorded
for its members in the Ancient Greek WordNet.

- **Primary script:** [`cltk_semantic_pipeline.py`](cltk_semantic_pipeline.py)
- **Variant:** [`semantic_fields_fasttext_HDBSCAN_Leiden.py`](semantic_fields_fasttext_HDBSCAN_Leiden.py)
  — the same clustering core, but clusters are glossed by a large language
  model (Groq API) instead of the WordNet.

The pipeline is fully unsupervised: no field inventory, seed
lists, or annotations are supplied. Field labels are attached only at the end,
as a post-hoc lookup, and do not influence the clustering.

## Data

Input is the `Lemmas` column of the two alignment files in the sibling
`homer_corpus/` directory:

```
../homer_corpus/iliad_alignments.csv
../homer_corpus/odyssey_alignments.csv
```

Each row is a sentence; the `Lemmas` column holds its space-separated lemmas
(dictionary forms), already produced by treebank-based morphological analysis.
Clustering therefore operates over **lemma types**, not inflected surface
forms.

## Method

The pipeline runs in six stages.

### 1–2. Loading and normalization (CLTK)

Lemmas are passed through the Classical Language Toolkit
(`cltk.alphabet.text_normalization.cltk_normalize`), which applies NFC
composition and oxia→tonos folding so that orthographically equivalent forms
collapse to a single canonical spelling. Without this, accent/encoding variants
would fragment frequency counts, defeat the stoplist, and produce spurious
WordNet misses. Non-Greek tokens and a small set of annotation artifacts
(English strings typed in Greek characters) are discarded.

A function-word stoplist is assembled from CLTK's Ancient Greek `STOPS`
augmented with a Homeric/epic supplement (particles, pronouns, prepositions,
and conjunctions the Attic-oriented default omits). Stop words are **retained**
for embedding training — they are legitimate context — but **excluded** from the
clustering vocabulary.

### 3. Embeddings (fastText)

A skip-gram fastText model is trained on the joint lemmatized corpus (both
epics share one embedding space, ~200k tokens). fastText is chosen over plain
word2vec because its subword (character n-gram) representations provide
informative vectors for the many low-frequency and morphologically related
Homeric lemmas that context alone cannot support. The clustering vocabulary is
then restricted to content lemmas with frequency ≥ `MIN_FREQ`, and vectors are
L2-normalized so that comparisons depend on direction (cosine) only.

### 4. Dimensionality reduction and clustering (UMAP + HDBSCAN)

UMAP reduces the L2-normalized vectors to `UMAP_DIMS` dimensions under a cosine
metric, with `min_dist=0.0` to pack points densely — the standard preprocessing
recipe for density-based clustering. HDBSCAN is then run on the reduced space.
HDBSCAN is well suited to this problem because it (a) infers the number of
clusters from the data rather than requiring it as input, and (b) assigns
low-density points to a **noise** label instead of forcing them into a cluster
— appropriate for a corpus dense with near-hapax vocabulary. Leaf cluster
selection is used to favour many fine-grained clusters as field candidates.

### 5. Cross-validation (Leiden)

As an independent check, a mutual k-nearest-neighbour graph is built over the
**original** (un-reduced) vectors with cosine-similarity edge weights, and the
Leiden algorithm partitions it by modularity. Unlike HDBSCAN, Leiden assigns
every lemma to a community (no noise). Agreement between the two partitions is
quantified on the HDBSCAN-assigned lemmas with the Adjusted Rand Index (ARI)
and Adjusted Mutual Information (AMI). Substantial above-chance agreement
between two methodologically unrelated algorithms is stronger evidence for the
reality of the induced structure than any single-partition quality metric.

### 6. Automatic labelling (Ancient Greek WordNet)

Each clustered lemma is queried against the Ancient Greek WordNet REST API
(`greekwordnet.chs.harvard.edu`), and the English `semfield` names of its
synsets are collected. Each cluster is labelled by majority vote: every member
contributes one vote per distinct semfield it carries, and the top
`LABEL_TOP_SEMFIELDS` fields (with ≥ 2 votes) become the label. Per-cluster
**coverage** — the fraction of members found in the WordNet — is reported
alongside, since rare or archaic lemmas may be absent. Responses are cached to
`agwn_cache.json` (shared with the gloss-embedding pipeline) so re-runs avoid
redundant network traffic.

## Outputs

Written to `cltk_pipeline_output/`:

| File                           | Description                                                                                                                                                       |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `cltk_lemma_clusters.csv`      | Per-lemma table: frequency, HDBSCAN and Leiden cluster IDs and labels, WordNet membership flag, semfields, sample gloss. UTF-8-BOM for spreadsheet compatibility. |
| `clusters_hdbscan_labeled.txt` | One block per HDBSCAN cluster: semfield label, coverage, and members with frequencies, sorted by centrality (cosine similarity to the cluster centroid).          |
| `clusters_leiden_labeled.txt`  | The same, for the Leiden partition.                                                                                                                               |
| `cltk_report.txt`              | Run summary: corpus and vocabulary statistics, per-partition clustering statistics, inter-partition agreement, WordNet coverage.                                  |
| `homer_fasttext_cltk.model`    | The trained fastText model (with `.wv.vectors_ngrams.npy` sidecar), reusable downstream.                                                                          |
| `agwn_cache.json`              | Cached WordNet responses (written to `../cluster_gloss_embeddings/`). Delete only if stale.                                                                       |

A representative cluster block:

```
cluster 178  |  33 lemmas  |  AGWN coverage 94%
  label: Eating, drinking; using drugs (17); Life Sciences; Biology (13); Food & Drink (12)
  οἶνος(129)  δέπας(56)  κρατήρ(41)  σπένδω(34)  ... κιρνάω(6)  οἰνοχόος(5)
```

Members are listed most-central first; parenthetical integers are corpus
frequencies for members and semfield vote counts in the label.

## Interpreting the report

`cltk_report.txt` reports the same statistics for each partition:

- **`clusters`** — number of clusters/communities found.
- **`assigned` / `noise`** — lemmas placed in a cluster vs. left unassigned.
  HDBSCAN leaves genuine outliers as noise; Leiden assigns everything.
- **`size_min` / `size_median` / `size_max`** — cluster-size distribution.
- **`silhouette_cosine`** — the mean silhouette coefficient (cosine metric,
  computed on the full-dimensional vectors) over clustered lemmas. For each
  lemma, the silhouette is `(b − a) / max(a, b)`, where `a` is its mean cosine
  distance to other members of its own cluster and `b` its mean distance to the
  members of the nearest other cluster. It ranges from −1 to +1: values near +1
  indicate tight, well-separated clusters; near 0, overlapping clusters with
  fuzzy boundaries; negative, likely misassignment. Expect **low positive**
  values here (≈ 0.02–0.05). This is normal for lexical data: semantic
  neighbourhoods form a continuum rather than well-gapped islands; many small
  clusters necessarily sit close to one another; and cosine distances are
  compressed in high dimensions. Silhouette is therefore most useful
  **comparatively** — HDBSCAN vs. Leiden, or across configurations — not as an
  absolute quality threshold.
- **`modularity`** (Leiden only) — the modularity of the community partition,
  Leiden's internal objective (higher = better-separated communities).
- **ARI / AMI** — agreement between the two partitions on the shared lemmas
  (1 = identical, 0 = chance-adjusted random). AMI is typically the more
  informative of the two when cluster counts differ substantially.
- **WordNet coverage** — the share of the clustered vocabulary found in the
  Ancient Greek WordNet, i.e. the fraction eligible to contribute labels.

## Usage

```bash
# from within this directory
py cltk_semantic_pipeline.py
```

Progress is printed per stage. The first run downloads WordNet entries over the
network (subsequent runs read the cache); model training is single-threaded for
reproducibility and is the other main cost.

## Configuration

All tunables are ALL-CAPS constants near the top of the script. The most
consequential:

| Constant                                                   | Role                                                                                    |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `VECTOR_SIZE`, `WINDOW`, `EPOCHS`, `MIN_N`/`MAX_N`         | fastText capacity, context width, training length, subword n-gram range.                |
| `MIN_COUNT`, `MIN_FREQ`                                    | minimum frequency to receive an embedding / to enter the clustering vocabulary.         |
| `UMAP_DIMS`, `UMAP_NEIGHBORS`, `UMAP_MIN_DIST`             | reduction target dimensionality and local/global structure trade-off.                   |
| `HDB_MIN_CLUSTER_SIZE`, `HDB_MIN_SAMPLES`, `HDB_SELECTION` | minimum cluster size, conservativeness of noise assignment, `leaf` vs. `eom` selection. |
| `KNN_K`, `LEIDEN_RESOLUTION`                               | neighbourhood size and granularity of the Leiden cross-check.                           |
| `LABEL_TOP_SEMFIELDS`                                      | number of semfields retained per cluster label.                                         |

The defaults are tuned for the Homeric corpus. When experimenting, vary one
parameter at a time and track the effect on the report statistics.

## Reproducibility

`SEED = 42` is applied to fastText, UMAP, and HDBSCAN, and fastText trains with
a single worker, so a given input yields identical output across runs.

## Dependencies

```bash
pip install cltk umap-learn gensim scikit-learn python-igraph pandas requests
```

Stage 6 additionally requires network access to the Ancient Greek WordNet API
on the first run (results are cached thereafter).

## Credits

- Text: **Perseus Digital Library**. XML/Unicode edition: **Giuseppe Celano**.
- License of the LSJ data: **CC BY-NC-SA 3.0**.https://github.com/Eumaeus/cite_lsj_cex/blob/master/lsj_chicago.cex
- Readme files and parts of the code developed with assistance of Claude opus 4.8 high and medium.
