# Emergent Semantic Fields in Homer via Gloss-Embedding Clustering

This folder discovers the semantic fields of the Homeric vocabulary (Iliad +
Odyssey) **without any predefined category list and without seed words**: the
categories emerge from the data. Each Homeric lemma is represented by the
sentence-embedding of its **English dictionary definition**, and those
definition vectors are clustered. The corpus decides _which_ words enter the
space (Homer's vocabulary); the lexicon supplies _what they mean_; the
cluster structure — fields such as _kinship_, _marriage_, _ruling_, _war_,
_love/desire_, _hospitality_ — is found, not imposed.

Script: `gloss_embedding_clusters.py`

---

## Why gloss embeddings (and not distributional embeddings)

Two earlier pipelines in this repository (in `../clustering_homer/`:
`semantic_fields_fasttext_HDBSCAN_Leiden.py` and
`cltk_semantic_pipeline.py`) clustered **distributional** vectors: fastText
trained on the ~200k lemmatized tokens of the two epics. The clusters were
unsatisfactory, and for a principled reason: on a small, highly formulaic
corpus, "similar context" means **collocation, not category**. Words that
travel together in formulas clustered together (e.g. the speech-introduction
formula words προσαυδάω, πτερόεις, ἔπος), while true field-mates like
πατήρ / μήτηρ / κασίγνητος were scattered, because they occupy different
formulaic slots.

Representing a lemma by its _definition_ instead of its _contexts_ removes
that failure mode: πατήρ ("father"), μήτηρ ("mother") and τέκνον ("child")
are close in definition space regardless of how Homer deploys them in the
hexameter. Clustering stays fully unsupervised — no category names, no
seeds — so the field inventory is still emergent.

---

## Data sources

| Source                                                                                       | Role                                                                                                                                                                                 |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `../homer_corpus/iliad_alignments.csv`, `../homer_corpus/odyssey_alignments.csv` | The corpus. The lemma sequence of each sentence is read from the last non-empty **"Lemmas"** column. 15,122 sentences, 199,967 tokens, 8,885 unique lemmas.                          |
| `../lsj_semantic_search/lsj_chicago.cex`                                                     | **Primary gloss source.** LSJ, Chicago edition (116,854 entries).                                                                                                                    |
| Ancient Greek WordNet API (`greekwordnet.chs.harvard.edu/api/`)                              | **Fallback gloss source** for lemmas LSJ cannot gloss. Responses are cached in `agwn_cache.json` (this folder, shared with the CLTK pipeline); missing lemmas are fetched on demand. |
| `all-MiniLM-L6-v2` (sentence-transformers)                                                   | English sentence-embedding model — the same model used in the LSJ social-relations experiments, so scores are comparable across the repository.                                      |

---

## Method, stage by stage

### 1. Vocabulary

Lemmas are normalized with CLTK (`cltk_normalize`: NFC composition,
oxia→tonos). Treebank artifacts (θυοτε, οτηερ, υνκνοων, ηψπηεν — English
annotation words typed in Greek letters) and non-Greek tokens are dropped.
A stoplist of 179 function words (CLTK's Ancient Greek `STOPS` plus a
Homeric supplement: particles, prepositions, pronouns, the copula) is
excluded — function words are not candidate field members. An optional
frequency threshold (`--min-freq`) restricts the vocabulary; see
**Results** for why the final run does not use one.

### 2. Glossing

For each lemma, an English definition is built:

- **LSJ parsing.** Each CEX line is split on `#` into
  `seq / urn / headword / entry`. The entry's `**bold**` spans are
  extracted; a span is kept as English if it contains ≥ 3 Latin letters and
  more Latin than Greek letters (this drops the bold Greek headword and
  Greek cross-references). The **first 4** surviving senses are joined with
  `;` and capped at 60 words. Because LSJ orders senses historically, the
  first senses are usually the _Homeric_ ones — a property this method
  relies on.
- **Headword matching.** LSJ headwords carry vowel-length marks (πᾰτήρ)
  and morpheme hyphens; matching strips combining macron/breve (U+0304,
  U+0306) and hyphens. If that exact key misses, a **relaxed key** is tried
  that additionally ignores diaeresis (U+0308) and iota subscript (U+0345),
  so treebank θνήσκω matches LSJ θνῄσκω, ὀιστός matches ὀϊστός, σώζω
  matches σῴζω. The relaxed pass recovered ~2,400 lemmas that the exact
  pass missed.
- **Homographs.** Treebank lemmas disambiguate homographs with trailing
  digits (λέγω3, χράω2). Digit _N_ selects the _N_-th LSJ homograph entry
  (LSJ (A), (B), … in file order); if there is no _N_-th entry, all
  homograph glosses are merged. This is a heuristic — the `gloss_source`
  column records exactly which rule fired for every lemma.
- **AGWN fallback.** Lemmas with no LSJ gloss are looked up in the Ancient
  Greek WordNet (first literal-sense gloss). Lookups are cached; lemmas
  missing from the cache are fetched from the API (8 threads) and the cache
  is persisted. AGWN glosses are auto-projected from English WordNet and
  noticeably noisier than LSJ — which is why they are the fallback, not the
  primary source.
- Lemmas with no gloss anywhere are **excluded** from clustering and listed
  in `unglossed_lemmas*.txt`. They are dominated by proper names, which is
  usually desirable for a semantic-field lexicon.

### 3. Embedding

Each gloss is embedded with `all-MiniLM-L6-v2` (384 dims) and
unit-normalized.

### 4. Clustering — two complementary views of the same vectors

- **UMAP + HDBSCAN** (flat fields): UMAP to 15 dimensions
  (`n_neighbors=15`, `min_dist=0.0`, cosine metric, `random_state=42`),
  then HDBSCAN (`min_cluster_size=8`, `min_samples=3`, leaf selection).
  HDBSCAN finds the number of clusters itself and marks unclusterable
  lemmas as outliers rather than forcing them into a field.
- **Ward hierarchy** (nested taxonomy): Ward linkage over the full
  384-dim unit vectors, cut at K = 12, 25, 50, 100. The dendrogram _is_
  the emergent category system at every granularity at once; coarse cuts
  (K=12, K=25) contain broad grab-bag clusters, and the useful
  granularities are K=50, K=100, and the HDBSCAN fields.

### 5. Naming

Every cluster is labelled by **c-TF-IDF** over its members' own glosses
(unigrams + bigrams, English stopwords removed, top 4 non-overlapping
terms). The label is therefore _derived from the cluster_, not supplied by
anyone.

---

## Running it

```powershell
# default vocabulary (lemmas occurring >= 5 times) -> outputs *_freq_limit_5
py "gloss_embedding_clusters.py"

# full vocabulary -> outputs *_no-freq-limit
py "gloss_embedding_clusters.py" --min-freq 1
```

The output suffix is derived from `--min-freq` (`_freq_limit_N`, or
`_no-freq-limit` when N = 1); pass `--suffix` to override.

Dependencies: `pip install sentence-transformers umap-learn scikit-learn
scipy pandas requests cltk`. Set `PYTHONIOENCODING=utf-8` on Windows
consoles (polytonic Greek output).

---

## Exact results

Two runs, identical code, differing only in the frequency threshold:

|                                   | freq ≥ 5               | no frequency limit       |
| --------------------------------- | ---------------------- | ------------------------ |
| candidate lemmas (after stoplist) | 3,224                  | 8,784                    |
| glossed & clustered               | 2,937                  | 7,051                    |
| — from LSJ                        | 2,857                  | 6,855                    |
| — from AGWN fallback              | 80                     | 196                      |
| unglossed (excluded)              | 287                    | 1,733 (65% proper names) |
| HDBSCAN fields                    | 144                    | 314                      |
| outliers                          | 701 (24%)              | 1,812 (26%)              |
| output files                      | `_freq_limit_5` suffix | `_no-freq-limit` suffix  |

### Why the frequency limit was removed

The `freq >= 5` threshold was inherited from the distributional pipelines,
where it was _necessary_: a corpus-trained vector for a rare word is
garbage, because it is estimated from a handful of contexts. For gloss
embeddings that justification evaporates — the vector comes from the LSJ
definition, which is equally good whether the word occurs once or 500
times. Homer's frequency distribution is very top-heavy (3,018 of 8,885
lemmas are hapax legomena), so the threshold was silently discarding a
third of the vocabulary — and the rare words are where much of the
lexically specific material lives.

The hospitality field from the no-limit run shows what is gained. It
assembles essentially the complete _xenia_ lexicon, including three words
that occur only once each and would have been invisible under the old
threshold:

> **guest, hospitality, strangers, entertainment** (13 lemmas):
> ξένος (207×), ξένιος, ξενία, ξεινήιον, ξενίζω, φιλόξενος, ξενοδόκος,
> δαιτυμών, κακόξενος (1×), ξενοσύνη (1×), ὑποδεξίη (1×), …

### Representative emergent fields (no-limit run, HDBSCAN)

- _wife, marriage, wedding, marry_ (20 lemmas): γάμος, ἄλοχος, δάμαρ,
  πόσις, μνηστήρ, γαμβρός, ἕδνον, …
- _son, child, offspring, infant_ (13): παῖς, τέκνον, υἱός, γόνος, … with a
  separate _travail, born, pangs, childbirth_ field (12)
- _lord, king, ruler, leader_ (14): βασιλεύς, ἄναξ, κρείων, … and
  _chief, leader, rule, sway_ (15): ἡγεμών, ὄρχαμος, ἀγός, …
- _desire, wish, longing, hope_ (27) and _affection, love, heart,
  friendship_ (14): ἔραμαι, ἵμερος, φιλέω, φιλότης, ἔρος, …
- _battle, fight, combat, war_ (9): πόλεμος, ὑσμίνη, φύλοπις, …
- _slave, taken in war_ (8), _dance, song, sport, play_ (22),
  _tears/sobbing_ (8), and ~300 more.

### Known noise sources (all visible in the outputs)

1. **English polysemy intruders.** στρατόω ("to be on campaign") sits in
   the hospitality cluster because its gloss contains "host" — the army
   sense, not the innkeeper sense. Each member's gloss is printed beside
   it, so such intruders are easy to spot.
2. **AGWN fallback glosses** are auto-projected and occasionally absurd
   (κασίγνητος → "sorority member" in an early run). The fix applied here
   was to maximize LSJ coverage (relaxed matching) so the fallback shrank
   from 661 to 196 lemmas; filter `gloss_source == "agwn"` for a stricter
   lexicon.
3. **Anachronistic LSJ senses.** An LSJ gloss covers a word's whole
   history; the first-4-senses rule usually keeps the Homeric meaning but
   post-Homeric senses sometimes leak in.
4. **Residual unglossed common words.** ~600 non-proper-name lemmas remain
   unglossed because LSJ files them under a different (Attic) headword:
   ἠέλιος → ἥλιος, ζώω → ζάω, μίγνυμι → μείγνυμι. A hand-made variant
   table would recover the most frequent ones.

---

## Files

Each run writes one set of files, suffixed `_freq_limit_5` or
`_no-freq-limit` (see **Running it**):

| File                                         | Content                                                                                                                       |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `lemma_gloss_fields_<suffix>.csv`            | One row per clustered lemma: frequency, gloss, gloss source, HDBSCAN cluster + label, Ward cluster + label at K=12/25/50/100. |
| `clusters_hdbscan_gloss_<suffix>.txt`        | One block per HDBSCAN field: c-TF-IDF label, members sorted by centrality, each with frequency and gloss.                     |
| `clusters_ward_k{12,25,50,100}_<suffix>.txt` | The Ward taxonomy at each granularity, same format.                                                                           |
| `unglossed_lemmas_<suffix>.txt`              | Excluded lemmas (no gloss found), by frequency.                                                                               |
| `gloss_report_<suffix>.txt`                  | Run statistics and caveats.                                                                                                   |
| `agwn_cache.json`                            | Cached Ancient Greek WordNet API responses (shared across pipelines; safe to delete, will be re-fetched).                     |

---

## Credits

- **LSJ text**: Perseus Digital Library (public-domain LSJ); XML/Unicode
  edition by Giuseppe Celano; "Chicago" curation by Helma Dik's team
  (University of Chicago / Logeion); CEX collection by Christopher W.
  Blackwell and Neel Smith
  ([`Eumaeus/cite_lsj_cex`](https://github.com/Eumaeus/cite_lsj_cex),
  CC BY-NC-SA 3.0).
- **Ancient Greek WordNet**: Harvard CHS / Exeter / Pavia
  (`greekwordnet.chs.harvard.edu`).
- **Corpus**: Perseids/Arethusa-aligned Iliad and Odyssey treebank
  alignments (the two CSVs in the repository root).
- **Tools**: CLTK, sentence-transformers, UMAP, scikit-learn (HDBSCAN),
  SciPy (Ward).
- README and code developed with the assistance of Claude Fable 5.
