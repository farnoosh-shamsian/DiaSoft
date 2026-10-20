# Homeric Hospitality — WordNet & FrameNet from Gloss-Embedding Clusters

The Ancient Greek hospitality WordNet & FrameNet experiment (July 2026), redone with word lists taken from the gloss-embedding clusters of Homeric lemmas (`../cluster_gloss_embeddings/`). For each cluster:

1. **WordNet layer.** Every Ancient Greek WordNet (AGWN) synset of every lemma, resolved to Princeton WordNet 3.0 and flagged core / plausible / noise.
2. **FrameNet layer, twice.** The lemmas are mapped to Berkeley FrameNet 1.7 frames once **without** and once **with** the WordNet layer, each run by a separate Claude Opus 5.5 agent that sees only its own inputs. New frames are proposed where FrameNet has none.
3. **Homeric passages.** Odyssey 1.123–124 and the sentence richest in the cluster's words are annotated in FrameNet full-text format (JSON, XML, HTML).
4. **Comparison.** Without vs. with WordNet, and both vs. the original experiment.

**Browse the results:** [`index.html`](index.html) (on GitHub Pages: the project folder's URL).

## Folder contents

| Folder | Content |
| --- | --- |
| [`index.html`](index.html) | Overview page: summary, new frames proposed, links to every page and data file |
| [`cluster128_k200/`](cluster128_k200/) | Cluster 128 of the Ward k=200 clustering — "guest, hospitality, escort, attendant", 18 lemmas |
| [`cluster98_k150/`](cluster98_k150/) | Cluster 98 of the Ward k=150 clustering — "gift, guest, receive, hospitality", 50 lemmas (contains all of cluster 128) |
| [`wordnet_check_cluster128/`](wordnet_check_cluster128/) | The first step: the WordNet check (core / plausible / noise) on cluster 128 |
| [`pipeline/`](pipeline/) | `pipeline.py` (all mechanical steps), `check_frames.py` (FrameNet 1.7 lookup and validation), `FORMAT_SPEC_template.md` (the output format given to the runs), `greek_glosses.json` (English glosses for all Greek on the pages) |

Each cluster folder has the same layout: `experiment.json` (lemmas, merges, groups, passages), `common/` (the inputs given to both runs), `AGWN_PWN/` (WordNet layer), `A_without_wordnet/`, `B_with_wordnet/`, `comparison/`, a README and a protocol.

## Running it for another cluster

1. Write `<folder>/experiment.json` (see the two existing ones).
2. `py pipeline/pipeline.py prepare <folder>`, then `passages` to rank candidate passages, and `extract` for the AGWN synsets.
3. Flag the synsets (judgment step) into `<folder>/AGWN_PWN/sense_flags.csv`, then `resolve` and `links`.
4. Give `common/` (plus the WordNet layer for run B) to two fresh agents; render each run with `render`, then `compare` and `index`.
5. Add glosses to `pipeline/greek_glosses.json` for any Greek the render steps report as unglossed, then `rerender <folder>` and `index`.

## Glosses

Every Greek word on the HTML pages carries an English gloss, taken from `pipeline/greek_glosses.json` and checked against LSJ (`../lsj_semantic_search/lsj_chicago.cex`): headwords and quoted words get a short gloss after them, the Homeric examples of the proposed frames get a translation line, and the annotated Odyssey passages are glossed word by word (hover a word for its lemma, morphology and frame). After editing the glosses, `py pipeline/pipeline.py rerender <folder>` rebuilds a cluster's pages from the files already in its folder.

The markdown pages are glossed the same way: the comparison tables and the lemma, target and frame tables in the protocols and READMEs have a Gloss column next to the Greek (`lemma_frames.csv` and `passage_targets.csv` have a `gloss` column), and Greek in running text, in the Obsidian lemma notes and in the method notes has its gloss after it. `render` and `compare` do this when they write their files; for hand-written pages run `py pipeline/pipeline.py gloss <file.md> ...`, which only adds glosses that are missing. The inputs given to the runs (`common/`, `WORDNET_LAYER.md`, `FLAGGING_CRITERIA.md`, `PROMPT.md`) and the data CSVs are left as they were.

Transliterations on the pages, in the lemma notes and in the terms tables show accent and vowel length: ē ō = η ω; ā ī ȳ = long α ι υ (a i y unmarked are short); ´ ` ˆ = acute, grave, circumflex accent; h = rough breathing; ï = a separate syllable (e.g. ξεινήιον *xeinḗïon* ‘guest-gift’, ταμίας *tamíās* ‘steward, dispenser’, δῶρον *dôron* ‘gift’). Lengths of α ι υ follow LSJ's quantity marks where LSJ gives them, otherwise the regular morphology. They are listed per headword under `translit` in `pipeline/greek_glosses.json`. The plain ASCII form stays in `experiment.json` and the data CSVs, where it serves as an identifier, and still works in the pages' search boxes and as an Obsidian alias.

Requirements: Python 3.12 with `nltk` (WordNet 3.0 and FrameNet 1.7 data: `nltk.download("wordnet")`, `nltk.download("framenet_v17")`).

## Data not included

- **Ancient Greek WordNet dump** (needed for `extract`). Download the three SQL files from GitHub `jcuenod/greekwordnet` (GPL-3.0) into `agwn_dump/` in this folder (ignored by git); every cluster's `extract` step reads it from there:

  ```
  https://raw.githubusercontent.com/jcuenod/greekwordnet/master/greekwordnet/db/greek/greek_index.sql
  https://raw.githubusercontent.com/jcuenod/greekwordnet/master/greekwordnet/db/english/english_synset.sql
  https://raw.githubusercontent.com/jcuenod/greekwordnet/master/greekwordnet/db/common/common_relation.sql
  ```

- **The original experiment's files** (its frame-assignment CSV and Odyssey 1.123 JSON, needed for `compare`; its WordNet-check CSV, needed for the ξενία ‘hospitality, guest-friendship’ check in `wordnet_check_cluster128/build_flagged_csv.py`) are shared within the team. The comparisons already made are in each cluster's `comparison/` folder and in `wordnet_check_cluster128/output/summary.txt`.

## Provenance

- **Frames:** Berkeley FrameNet 1.7. Every existing frame and frame element used was checked against the FrameNet 1.7 data.
- **Greek senses:** LSJ glosses of the cluster; Ancient Greek WordNet (database dump, GitHub `jcuenod/greekwordnet`) in the runs with WordNet.
- **Judgments:** sense flags, frame assignments, proposed frames and passage annotations are proposals by Claude Opus 5.5, for review by the team.
