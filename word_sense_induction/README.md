# Word sense induction — a simple explanation

Many words mean more than one thing. In Homer, for instance, a single word can
mean "spirit/anger" in one line and "life/breath" in another; another word can
mean both "ship" and "temple" depending on the passage. When we treated each
word as having just **one** meaning, these different senses got blurred together.

This folder fixes that. It looks at **every single occurrence** of a word
separately, figures out how many distinct senses that word really has in Homer,
and then groups those senses into topics. The name for automatically
discovering a word's senses from data — without a dictionary telling us in
advance — is **word sense induction (WSI)**.

## Why this needs a different tool

The rest of the project mostly uses one number-profile per word. That can't
separate senses, because "spirit" and "life" would share the same profile. So
here we use a model that reads a word **in its sentence** and gives a different
profile depending on the surrounding words. The model is **GreBERTa**, an AI
language model trained specifically on ancient Greek. Give it a sentence and it
produces, for each word, a set of numbers capturing how that word is being used
*right there* — so the same word in two different contexts gets two different
profiles. That is exactly what's needed to tell senses apart.

## The three steps

The work is split into three scripts that run in order. Each one saves its
results so the next can pick them up.

| Step | Script | In plain words |
| --- | --- | --- |
| 1 | `embed_occurrences.py` | **Read every word in context.** For each occurrence of each noun, verb, and adjective in both epics, GreBERTa produces a numeric profile of how it's used in that specific line. |
| 2 | `wsi_cluster.py` | **Split each word into senses.** For one word, look at all its occurrence-profiles. If they all look alike, it has one sense. If they fall into distinct groups, each group is a separate sense — with its own example lines and typical neighbouring words. Safeguards stop it from over-splitting Homer's repeated formulas. |
| 3 | `sense_fields.py` | **Group the senses into topics.** Now that words are split into senses, cluster the senses into semantic fields (topics). A word with two meanings can now sit in two different topics at once — one per sense. |

(`wsi_common.py` is just shared setup — file paths and settings the three steps
have in common. You don't run it directly.)

## How to run it

```bash
py word_sense_induction/embed_occurrences.py    # step 1 (slow: reads all of Homer)
py word_sense_induction/wsi_cluster.py          # step 2
py word_sense_induction/sense_fields.py         # step 3
```

Step 1 is the heavy one because the AI model has to read the whole corpus. To
try it quickly on just *Iliad* book 1 first, add `--smoke`:

```bash
py word_sense_induction/embed_occurrences.py --smoke
```

## What comes out

Everything lands in the `wsi_output/` folder:

- `occ_vectors.npy` + `occ_index.csv` (step 1) — the profile for every word
  occurrence, and a table saying which word/line each profile belongs to.
- `senses.csv` (step 2) — one row per discovered sense: the word, which sense
  number it is, how many times it occurs, a sample meaning, its most typical
  neighbouring words, and example line references.
- `sense_centroids.npy` (step 2) — the numeric summary of each sense (used by
  step 3).
- `sense_fields.csv` (step 3) — each sense with the topic (semantic field) it
  was placed in.
- `fields_hdbscan.txt` and `fields_ward_k*.txt` (step 3) — human-readable lists
  of the topics and their member senses, at a few levels of coarseness.
- `field_report.txt` (step 3) — a summary: how many senses and fields, how
  clean the grouping is, how much polysemy (multiple senses) was found, and how
  much the result agrees with the earlier one-profile-per-word approach.

## What makes this special

Because it works one occurrence at a time, a word that means two different
things in Homer can finally be recognised as two things and placed in two
different topics — something none of the simpler methods in the project can do.
