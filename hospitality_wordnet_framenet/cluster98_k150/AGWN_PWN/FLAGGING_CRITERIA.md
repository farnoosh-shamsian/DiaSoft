# Flagging Ancient Greek WordNet synsets: core / plausible / noise

Ancient Greek WordNet (AGWN) linked each Greek lemma to English WordNet synsets automatically, by matching the English words of Greek–English dictionary glosses. Every sense of a polysemous English gloss word was attached, so most links are wrong. The task is to judge, for every synset linked to a lemma, whether it is a real sense of the Greek word.

## Categories

- **core**: a main sense of the Greek word (as in LSJ).
- **plausible**: a secondary sense of the Greek word (including later, non-Homeric senses attested in LSJ), or a closely related concept that the word's meaning directly involves.
- **noise**: a sense brought in by a different meaning of an English gloss word. Example: Greek "receive (a guest)" → English "receive" → the synset "convert incoming radio signals into sounds or pictures".

Judge by reading the synset's English words and gloss against what the Greek word means (LSJ glosses are in `lemmas.csv`; use your knowledge of Greek). Do not judge by the English words alone: "receive" can be core in one synset and noise in the next.

## Calibration

`calibration_flags_cluster128.csv` holds every core and plausible flag from an earlier batch of 2,168 synsets (18 lemmas, 168 kept, 2,000 noise), with reasons, judged with the same criteria. Match its strictness: on large verbs typically only a few percent of synsets are kept.

## Output

Write `flags.csv` in your output folder with columns `greek_lemma,synset_id,sense_flag,reason`, listing **only** core and plausible synsets (everything not listed counts as noise). `reason`: one short line, in the style of the calibration file (e.g. `give as a present`, `receive into one's house`, `honour: 'gift of honour'`).

Read every synset; do not skip any or judge by keyword search.
