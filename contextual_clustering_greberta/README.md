# Contextual clustering of Homer with GreBerta

Semantic clustering of Homeric vocabulary from **contextual embeddings only**. The
sole input is the Homer corpus itself (`../homer_corpus/*.csv`) — no LSJ glosses, no
Ancient Greek WordNet, no treebank annotation, none of the earlier pipelines in this
repo.

## Model

[`bowphs/GreBerta`](https://huggingface.co/bowphs/GreBerta) — a RoBERTa-base model
pretrained on Ancient Greek (Riemenschneider & Frank, *Exploring Large Language
Models for Classical Philology*, ACL 2023). It is the strongest general-purpose
encoder currently available for Ancient Greek; `pranaydeeps/Ancient-Greek-BERT` is
the usual alternative and can be swapped in via `MODEL_NAME`.

## Pipeline

1. **Corpus** — the Iliad and Odyssey alignment CSVs. The whitespace tokens of the
   `Greek text` column are matched 1:1 against the `Lemmas` column; sentences where
   the two do not line up are dropped so no vector is filed under the wrong lemma.
2. **Contextual embeddings** — every sentence is passed through GreBerta; sub-word
   pieces are mean-pooled back to word level and the last four hidden layers are
   averaged.
3. **Type vectors** — each lemma's token vectors are averaged into a single vector.
4. **Anisotropy correction** — the space is centred and its top 2 principal
   components are removed (Mu & Viswanath 2018). Without this, cosine similarity in
   a contextual space is dominated by frequency/positional structure rather than
   meaning.
5. **Clustering** — UMAP (cosine, 15d) → HDBSCAN for emergent fields, plus Ward
   cuts at k = 40 / 80 / 150 on the type vectors as a complete-partition cross-check.

Function words and the beta-code artifact tokens in the lemma column
(`θυοτε`, `οτηερ`, …) are excluded from clustering, and lemmas need ≥ 5
attestations. Function words are still embedded, so they keep providing context for
the content words around them.

## Running

```powershell
$env:PYTHONIOENCODING='utf-8'; py "greberta_contextual_clusters.py"
```

The embedding pass is the slow step (CPU-only here). Its result is cached in
`greberta_clusters_output/lemma_vectors.npz`; delete that file to re-embed, keep it
to re-cluster instantly with different parameters.

## Output (`greberta_clusters_output/`)

| file | contents |
| --- | --- |
| `lemma_clusters.csv` | one row per lemma: frequency, HDBSCAN and Ward labels, 2-D UMAP coordinates |
| `clusters_hdbscan.txt` | readable cluster listings, members ranked by centroid similarity |
| `clusters_ward_{40,80,150}.txt` | the same at three fixed granularities |
| `nearest_neighbours.txt` | nearest neighbours for probe lemmas — a quick sanity check on the space |
| `lemma_map.png` | 2-D UMAP map with the most frequent lemmas labelled |
| `lemma_vectors.npz` | cached type vectors + frequencies |
| `summary.json` | run statistics |
