# Frame induction for Homer

Predicate–argument **frame semantics** from the full AGLDT 2.1 dependency
treebanks — the step beyond the semantic _field_ clustering in the rest of
DiaSoft. Fields group lemma _types_ by similarity; **frames** group _verbs_ by
the participant roles their arguments fill (Fillmore), which needs syntax the
old lemmas-only CSVs did not carry.

## Pipeline

| File                 | What it does                                                                                                                                                                                                                                  | Key outputs                                                                                                                                                                   |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| `treebank.py`        | Parses both `.tb.xml` into a token table (lemma + decomposed morphology + head/relation + book.line) and extracts predicate–argument tuples. Resolves AGLDT coordination (`_CO`/`_AP`), climbs `AuxP` prepositions for obliques, keeps voice. | `predicate_arguments.csv`                                                                                                                                                     |
| `frame_induction.py` | Represents each verb by `[mean SBJ-filler                                                                                                                                                                                                     | mean OBJ-filler]` FastText vectors, clusters verbs into frames (UMAP+HDBSCAN, Ward), names them via c-TF-IDF over member verbs' LSJ glosses, reports selectional preferences. | `frame_output/frames.txt`, `frames.csv` |
| `topic_models.py`    | Topic modeling as a syntax-aware component: NMF type-scene topics over passage windows, `verb>object` dependency-tuple topics, per-book prevalence matrix, optional anchored CorEx seeded from the 11 social-relation categories.             | `topic_output/*.txt`, `topic_prevalence_by_book.csv`                                                                                                                          |

## Run

```
py frame_induction/treebank.py          # parse + self-test
py frame_induction/frame_induction.py   # induce frames
py frame_induction/topic_models.py      # topic models + prevalence
```

## Validation (observed)

Induced frames are coherent: combat-wounding (βάλλω/οὐτάζω + body-part objects),
speech (εἶπον/φημί + ἔπος/μῦθος), sacrifice/feast (ἔδω/ἱερεύω + ox/thigh-bones),
oath (ὄμνυμι + ὅρκος), lament (θυμός-as-experiencer). NMF type-scene topics and
their per-book prevalence recover real narrative structure — the bow-contest
topic peaks in Odyssey 21, the sea-storm topic in Odyssey 5, the feast topic in
Odyssey 3.

## Caveats

AGLDT relations are **syntactic, not semantic roles** — `SBJ` ≠ Agent under
passive/middle voice (voice is retained in `predicate_arguments.csv` for later
refinement). Homer uses the middle heavily. Frames are a _candidate inventory_
to curate against LSJ and the 11 categories, not a gold FrameNet.
