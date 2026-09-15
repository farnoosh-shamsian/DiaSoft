# DiaSoft — LSJ Social-Relations Extractor

This repository extracts entries from the LSJ that concern social relations — kinship, marriage, friendship, hostility, hospitality, erotic bonds, rank and rule, military rank, servitude, and civic community — and labels each entry with the relevant category.

---

## Source text

The lexical data is the `lsj_chicago.cex` file from the [`Eumaeus/cite_lsj_cex`](https://github.com/Eumaeus/cite_lsj_cex) repository, published by Christopher W. Blackwell and Neel Smith as part of the CITE Architecture / Homer Multitext ecosystem.

The specific edition used here is the "Chicago" version: an updated set of LSJ XML files curated over roughly a decade by Professor Helma Dik's team at the University of Chicago.

---

## Methods

The script turns raw CEX into a labelled CSV in the following stages.

### 1. Parse
Read the CEX file line by line, split each line on `#` into its four fields, and keep only rows whose URN field actually begins with `urn:` (skipping headers, comments, and malformed lines).

### 2. Gloss extraction
For each entry, pull out the `bold` spans — these are the English translations. Spans that are *mostly Greek* are discarded (a character-range test over the Greek Unicode blocks), and the surviving distinct spans are joined with `;`. The result is a compact English gloss for the entry; entries with no English gloss are dropped.

### 3. Seed-keyword pass
A curated keyword list per category (e.g. *father, mother, kinsman* for kinship; *enemy, feud, grudge* for hostility) is matched against each gloss with
word-boundary regexes. Seeds provide fast recall and a small confidence boost.

### 4. Sense splitting
Each gloss is split on `;` into its separate **senses**, so that a polysemous word is judged sense-by-sense. 

### 5. Contrastive sentence-embeddings
Each sense is embedded with the `all-MiniLM-L6-v2` sentence-transformer. For every category we compare the sense against two sets of embedded phrases:

- **positive prompts** — natural-language descriptions of what the category is (e.g.*"affection, tenderness, and love felt for another person*);
- **anti-prompts / decoys** — near-neighbour senses we want to exclude (e.g.*"love of money, honour, power"*; generic grammatical, botanical, medical, and coinage senses that pollute the lexicon).

A sense is accepted for a category only if it (a) reaches a similarity
**threshold** to the positive prompts **and** (b) beats its nearest decoy by a
**margin**. 

### 6. Top-1 assignment
Each word is assigned to its **single best-scoring category** by default (optional multi-label mode keeps any additional category within a small delta of the top). This prevents one word from multiplying across many categories.

### 7. Output
Two CSV files are written:

- **`lsj_social_relations.csv`** — one row per (lemma, category) assignment, with the match method, positive/negative similarity scores, margin, entry length, and gloss.
- **`lsj_social_relations_scores.csv`** — a full score matrix (every category's score for every glossed entry), for inspection and threshold tuning.

---

## Results
- Ex1 served as the baseline. Each category was represented by a single positive prompt, and the full English gloss of each entry was embedded as a single unit. A word was assigned to a category if it either matched a seed keyword or exceeded a single similarity threshold (0.45). No anti-prompts or decoy filtering were used, allowing semantically ambiguous matches to pass.
- Ex2 introduced a substantially revised classification pipeline. Instead of embedding the full gloss, individual senses were extracted and scored separately. Each category was expanded with multiple positive prompts as well as anti-prompts, including both category-specific decoys and a global set of commonly confusable senses. A match was accepted only if it exceeded the positive similarity threshold and outperformed its closest decoy by a required margin. Senses supported by a seed keyword were allowed a slightly lower similarity threshold.
- Ex3 is identical to Ex2 except for a single parameter change: the positive similarity threshold was increased from approximately 0.48 to 0.70. This removed many weaker embedding-only matches, producing a more conservative result set that relied primarily on seed-supported classifications.

In summary, Ex1 → Ex2 introduced per-sense scoring, anti-prompts, and margin-based decoy filtering, while Ex2 → Ex3 simply increased the positive similarity threshold to improve precision.

---

## Running it

```bash
pip install sentence-transformers pandas python-dotenv tqdm numpy
python lsj_social_relations.py
```

Set the input/output paths at the top of the script, then adjust the tuning knobs to control how tight the results are:

| Knob                      | Effect                                                        |
|---------------------------|--------------------------------------------------------------|
| `THRESHOLD`               | Minimum similarity to a positive prompt (raise → fewer, tighter) |
| `MARGIN`                  | How far a sense must beat its nearest decoy (raise → fewer false positives) |
| `MULTI_LABEL`             | `False` = one category per word; `True` = allow near-ties     |
| `TEST_LIMIT`              | Set to e.g. `5000` for a quick trial run; `0` = full corpus   |

The model (~80 MB) downloads and caches on first run.

---

## Categories

`kinship_family`, `marriage`, `friendship_affection`, `hostility_enmity`,
`hospitality_xenia`, `erotic_pederasty`, `rank_kingship_rule`, `military_rank`,
`servitude_slavery`, `messenger_herald_envoy`, `civic_community`.

---

## Credits

- Text: **Perseus Digital Library** (NEH-funded digitization of the public-domain LSJ).
- XML/Unicode edition: **Giuseppe Celano**.
- Chicago curation: **Helma Dik** and the University of Chicago digital-Classics team.
- CEX collection: **Christopher W. Blackwell** and **Neel Smith**
  ([`Eumaeus/cite_lsj_cex`](https://github.com/Eumaeus/cite_lsj_cex)).
- License of the LSJ data: **CC BY-NC-SA 3.0**.https://github.com/Eumaeus/cite_lsj_cex/blob/master/lsj_chicago.cex
- Readme file and parts of the code developed with assistance of Claude opus 4.8 medium.