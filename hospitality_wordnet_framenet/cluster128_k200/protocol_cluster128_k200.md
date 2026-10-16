# Protocol: WordNet and FrameNet Mapping of Hospitality Cluster 128, with and without WordNet

Oct 16, 2026 · Farnoosh Shamsian

Model: Claude Opus 5.5 (`claude-opus-5-5`), run in Claude Code.

## Summary

**Aim.** Redo the hospitality WordNet & FrameNet experiment (WordNet layer, FrameNet layer, Odyssey 1.123 annotation) on the 18 lemmas of gloss-embedding cluster 128, and find out what the WordNet layer adds to the FrameNet mapping. The FrameNet mapping was therefore done twice, by separate, fresh agents with identical inputs except for the WordNet layer: run A without WordNet, run B with it.

**Result.** Both runs mapped every lemma to FrameNet 1.7 frames, annotated Odyssey 1.123–124 and 7.189–196, and proposed two new frames under the same names (Guest_friendship, Tending). Run B produced more sense–frame pairings (62 vs. 52), mostly from WordNet senses. The runs agree on the primary frame of 14 of 18 lemmas. With one run per condition, the differences cannot yet be separated from run-to-run variation.

## Materials

| Resource | Version and source | In this repository |
| --- | --- | --- |
| Cluster | Ward k=200 gloss-embedding clustering, no frequency limit; cluster 128 (20 entries) | `common/cluster.txt`; settings in `experiment.json` |
| Greek senses | The cluster's LSJ glosses, truncated at about 90 characters | `common/lemmas.csv` |
| Homeric text | AGLDT treebanks of the Iliad and Odyssey, version 2.1 | `../../homer_corpus/` |
| Ancient Greek WordNet | SQL dump from GitHub `jcuenod/greekwordnet`, branch `master`, downloaded Oct 15, 2026 (commit not recorded) | No. Download URLs in `../README.md` |
| Sense flags | core / plausible / noise flags from the WordNet check | `../wordnet_check_cluster128/` |
| Princeton WordNet | 3.0, through NLTK 3.10.0 | No (`nltk.download("wordnet")`) |
| FrameNet | Berkeley FrameNet 1.7, through NLTK 3.10.0 | No (`nltk.download("framenet_v17")`) |
| Original experiment | Its frame-assignment CSV, Odyssey 1.123 annotation and PWN 3.0 links (July 2026, Claude Opus 4.8) | No, shared within the team |
| Software | Python 3.12.5 | `../pipeline/pipeline.py`, `common/check_frames.py` |

## Protocol

The work ran in five stages. Stages 1, 2 and 5 are scripted (`../pipeline/pipeline.py`); stages 3 and 4 are model judgment.

### Stage 1: Take the word list from the cluster

1. Take cluster 128 (20 entries) from the Ward k=200 gloss-embedding clustering. Merge ξένος / ξένος2 and τάμιας / ταμίας, leaving 18 lemmas in three groups: guest/hospitality (9), escort (4), attendant/service (5).
2. Take each lemma's LSJ glosses from the cluster file and its part of speech from the AGLDT treebank.
3. Write the vocabulary list (`cluster128_terms_table.md`).

### Stage 2: Build the WordNet layer

1. Extract every AGWN synset of each lemma from the AGWN database dump, matching exact lemmas: 2,168 synsets for 15 lemmas. ὑποδεξίη, ὑποδρηστήρ and ταμίας have none.
2. Resolve each synset to Princeton WordNet 3.0. The candidates are the PWN 3.0 synsets, with the same part of speech, of the synset's English words. Label the match:
   - `exact_gloss`: a candidate has the same gloss (after normalising case and punctuation).
   - `gloss+lemma`: otherwise, the candidate with the most similar gloss, if the similarity is at least 0.6 (Python `difflib` ratio).
   - `lemma_set`: otherwise, the candidate whose lemma names overlap the English words most.
   - `unresolved`: no candidate.
3. Add the core / plausible / noise flags and reasons from the WordNet check (42 core, 126 plausible, 2,000 noise).

### Stage 3: Map the lemmas to FrameNet, twice

1. Prepare identical inputs for both runs: the lemma list, the cluster, the two passages with treebank lemmas and character offsets, a format specification, and a FrameNet 1.7 lookup and validation tool (`common/`). The format specification shows example rows from the original experiment, all for lemmas outside the cluster (πρόξενος, φιλία, φίλος, and a proposed frame Proxeny). Run B also gets the WordNet layer (`AGWN_PWN/cluster128_field_wordnet_full.csv`, described in `AGWN_PWN/WORDNET_LAYER.md`), with the instruction to use its core and plausible senses as evidence.
2. Start both runs within one minute of each other, each as a separate Claude Code subagent with no access to the main session's conversation. The prompts are in `common/run_prompts.md`. Each run may read only its inputs and the Homer treebanks (to check usage and citations), must not search the web, and in run A must not use any WordNet. These rules were given as instructions; file access was not technically restricted.
3. Each run maps every lemma to one primary and any number of alternative FrameNet 1.7 frames, proposes a new frame only where no existing frame captures a concept, and records its senses and decisions (`method_notes.md`). The rule for the primary frame was each run's own; both chose the lemma's dominant Homeric sense.
4. Check every existing frame and its core frame elements against the FrameNet 1.7 data (`check_frames.py csv`). Both runs: 0 problems.

### Stage 4: Annotate two Homeric passages

1. Odyssey 1.123–124, the same text as the original experiment, and Odyssey 7.189–196, the treebank sentence with the most cluster words (ξεῖνον, ξεινίσσομεν, πομπῆς, ξεῖνος, πομπῇ), in the AGLDT text.
2. Annotate with existing FrameNet 1.7 frames only: targets, frame elements with 0-based, end-inclusive character offsets, null instantiations (CNI / DNI / INI), and caveats for words left unannotated.
3. Check that every span matches its offsets and every frame element exists (`check_frames.py json`). Both runs: 0 problems.

### Stage 5: Render and compare

1. Render both runs in the original experiment's formats: frame-assignment CSV, FrameNet HTML, Obsidian lemma notes, and JSON / XML / HTML per passage.
2. Compare run A with run B, and both with the original experiment on the five lemmas they share and on Odyssey 1.123–124. Measures:
   - **Same primary frame:** the two runs give a lemma the same primary frame name.
   - **Frame-set overlap:** for each lemma, the Jaccard index of the two runs' sets of frames (primary and alternatives), averaged over the 18 lemmas.
   - **Passage agreement:** targets are matched by their character offsets; for targets annotated in both runs, the number with the same frame, and with the same frame and the same frame-element labels.

## Results

### Frame assignments

| | Run A (without WordNet) | Run B (with WordNet) |
| --- | --- | --- |
| Sense–frame pairings | 52 | 62 |
| Proposed new frames | Guest_friendship, Tending | Guest_friendship, Tending |
| Same primary frame | 14 of 18 lemmas | |
| Mean frame-set overlap (Jaccard) | 0.58 | |

Primary frames on which the runs differ:

| Lemma | Run A | Run B | WordNet data? |
| --- | --- | --- | --- |
| ξενίζω | Guest_and_host | Have_visitor_over | yes: "have as a guest", "receive into one's home" |
| δαιτυμών | Social_event | Guest_and_host | yes: "guest, invitee" |
| ὑποδεξίη | Have_visitor_over | Hospitality | none |
| ταμίας | Being_in_control | Supply | none |

Run B's extra pairings come mostly from WordNet senses, e.g. ξένος → Foreign_or_domestic_country, Member_of_military (mercenary); ξενία → Temporary_stay; πομπή → Entourage, Being_obligated; θεραπεύω → Cure. Run B names the synsets behind them in its `note` column and in `method_notes.md`. The full lemma-by-lemma comparison is in `comparison/comparison.md`.

### Proposed frames

Both runs proposed two frames under the same names. The definitions describe the same concepts in different words; the frame relations and some frame elements differ:

| Frame | Both runs | Run A | Run B |
| --- | --- | --- | --- |
| **Guest_friendship** | A lasting, reciprocal, often inherited bond between guest-friends of different communities, sealed by gifts. Inherits Personal_relationship. Core FEs: Partner_1, Partner_2, Partners. | Uses Guest_and_host, Giving. LUs: ξενοσύνη, ξένος, ξενία, ξεινήιον | Uses Guest_and_host, Exchange. LUs: ξένος, ξενοσύνη, ξενία, ξένιος; ξεινήιον fills the Token FE |
| **Tending** | Ongoing care of a person, animal, plant or property; FrameNet 1.7 has no frame for *tend* or *look after*. Inherits Intentionally_act; uses Assistance. LUs: ἀμφιπολεύω, θεραπεύω | Core FEs: Caretaker, Ward | Core FEs: Caretaker, Charge |

Guest_friendship corresponds to Ritualized_guest_friendship, proposed in the original experiment.

### Passage annotations

| Passage | Annotation sets, run A | Run B | Targets in both runs | Same frame | Same frame and FE labels |
| --- | --- | --- | --- | --- | --- |
| Odyssey 1.123–124 | 7 | 7 | 7 | 4 | 3 |
| Odyssey 7.189–196 | 26 | 30 | 26 | 22 | 14 |

### Comparison with the original experiment

| Lemma | Original primary | Run A | Run B |
| --- | --- | --- | --- |
| ξένος | Guest_and_host | Guest_and_host | Guest_and_host |
| ξενίζω | Provide_lodging | Guest_and_host | Have_visitor_over |
| ξενία | Ritualized_guest_friendship (proposed) | Hospitality | Hospitality |
| ξεινήιον | Giving | Giving | Giving |
| φιλόξενος | Hospitality | Hospitality | Hospitality |

In both runs ξενία has Guest_friendship as an alternative frame. On Odyssey 1.123–124 the three annotations agree on ξεῖνε (Guest_and_host), πασσάμενος (Ingestion) and χρή (Needing). They differ on φιλήσεαι (Provide_lodging / Guest_and_host / Have_visitor_over) and μυθήσεαι (Telling / Statement / Telling), and both runs also annotate ἔπειτα and δείπνου.

The WordNet layers differ too: on the 482 AGWN synsets that both contain, this experiment's script picks the same PWN 3.0 synset as the original in 369 cases (77%).

## Outputs

| File | Format | Content |
| --- | --- | --- |
| `cluster128_terms_table.md` | Markdown | Vocabulary list (stage 1) |
| `AGWN_PWN/agwn_synsets_raw.csv` | CSV | AGWN synsets as extracted from the dump (stage 2) |
| `AGWN_PWN/sense_flags.csv` | CSV | The 168 core and plausible flags, with reasons |
| `AGWN_PWN/cluster128_field_wordnet_full.csv` | CSV | 2,168 AGWN synsets resolved to PWN 3.0, with flags: the WordNet layer given to run B |
| `AGWN_PWN/WORDNET_LAYER.md` | Markdown | The description of the WordNet layer given to run B |
| `AGWN_PWN/cluster128_field_links.html` | HTML | Browsable WordNet layer |
| `common/` | CSV, JSON, Markdown, Python | Inputs given to both runs; `run_prompts.md`, the exact prompts of both runs |
| `A_without_wordnet/`, `B_with_wordnet/` | CSV, HTML, JSON, XML, Markdown | Per run: frame assignments, FrameNet page, proposed frames, lemma notes, two passage annotations, method notes |
| `comparison/` | Markdown, CSV | A vs. B, and both vs. the original |
| `experiment.json`, `../pipeline/pipeline.py` | JSON, Python | Settings for this cluster; the pipeline for stages 1, 2 and 5 |

## Reproducing

1. Download the AGWN dump (`../README.md`) and the NLTK data for WordNet 3.0 and FrameNet 1.7.
2. Stages 1 and 2, run from `hospitality_wordnet_framenet/`: `py pipeline/pipeline.py prepare cluster128_k200`, then the same with `passages`, `extract`, `resolve` and `links`. The flags come from `AGWN_PWN/sense_flags.csv`.
3. Stages 3 and 4: start two fresh agents with the prompts in `common/run_prompts.md`, pointing them at copies of `common/` (and, for run B, of the two WordNet layer files). Claude Code exposes no temperature or random seed, so new runs will not reproduce these frames exactly. To reproduce the results, reuse the run folders.
4. Stage 5: `render` each run, then `compare` with the original experiment's files, then `index`.

## Caveats

The frame assignments and annotations are drafts for team review, not validated data.

- **One run per condition.** Two of the four primary-frame differences (ὑποδεξίη, ταμίας) are on lemmas without any WordNet data, so they come from run-to-run variation, not from WordNet. Separating the WordNet effect from this variation needs several runs per condition.
- **Same model, same prior knowledge.** Run A had no WordNet data but still knows Greek: it found senses such as ξενίζω "surprise" without WordNet. The comparison measures what WordNet adds to a model that already knows the language. Shared knowledge, and the shared format specification with its example rows from the original experiment, can also explain why both runs proposed frames under the same names.
- **Isolation by instruction.** The runs were told to read only their own inputs; this was not technically enforced. Their method notes list only the permitted inputs.
- **Model judgment.** Senses, frames, proposed frames and annotations are Claude Opus 5.5's proposals; the sense flags behind run B are too (see the WordNet check). The original experiment used Claude Opus 4.8.
- **Inputs differ from the original.** The cluster's LSJ glosses are truncated at about 90 characters, the WordNet layer comes from the AGWN dump rather than the live API, and its PWN 3.0 matches differ from the original's on 23% of shared synsets.
- **Check the Greek text.** Odyssey 1.123–124 follows the original experiment and 7.189–196 follows AGLDT 2.1. Verify both against a critical edition before reusing the offsets.
