# Protocol: WordNet and FrameNet Mapping of Hospitality Cluster 128, with and without WordNet

Oct 16, 2026 · Farnoosh Shamsian

Model: Claude Opus 5.5 (`claude-opus-5-5`), run in Claude Code.

## Summary

The hospitality WordNet & FrameNet experiment (WordNet layer, FrameNet layer, Odyssey 1.123 annotation) was redone on the 18 lemmas of gloss-embedding cluster 128, twice: run A without WordNet and run B with the WordNet layer. Each run was done by a separate, fresh agent. Both runs mapped every lemma to FrameNet 1.7 frames, proposed the same two new frames (Guest_friendship, Tending), and annotated Odyssey 1.123–124 and 7.189–196. Run B produced more sense–frame pairings (62 vs. 52); the two runs agree on the primary frame of 14 of 18 lemmas.

## Protocol

The work ran in five stages.

### Stage 1: Take the word list from the cluster

1. Take cluster 128 (20 entries) from the Ward k=200 gloss-embedding clustering; merge ξένος / ξένος2 and τάμιας / ταμίας, leaving 18 lemmas in three groups (guest/hospitality, escort, attendant/service).
2. Take each lemma's LSJ glosses from the cluster file and its part of speech from the AGLDT treebank.
3. Write the vocabulary list (`cluster128_terms_table.md`).

### Stage 2: Build the WordNet layer

1. Extract every AGWN synset of each lemma from the AGWN database dump (`jcuenod/greekwordnet`), matching exact lemmas: 2,168 synsets for 15 lemmas; ὑποδεξίη, ὑποδρηστήρ and ταμίας have none.
2. Resolve each synset to Princeton WordNet 3.0 (NLTK) and label the match `exact_gloss`, `gloss+lemma`, `lemma_set` or `unresolved`.
3. Add the core / plausible / noise flags and reasons from the earlier WordNet check (42 core, 126 plausible).

### Stage 3: Map the lemmas to FrameNet, twice

1. Prepare identical inputs for both runs: the lemma list, the cluster, the two passages with treebank lemmas and offsets, a format specification copied from the original experiment's files, and a FrameNet 1.7 lookup and validation tool. Run B also gets the WordNet layer.
2. Give each run to a fresh agent that may read only its inputs (and the Homer treebanks, to check usage and citations).
3. Each agent maps every lemma to one primary and any alternative FrameNet 1.7 frames, proposes a new frame only where none exists, and records the senses it used.
4. Check every existing frame and its core frame elements against the FrameNet 1.7 data. Both runs: 0 problems.

### Stage 4: Annotate two Homeric passages

1. Odyssey 1.123–124 (same text as the original experiment) and Odyssey 7.189–196 (the sentence with the most cluster words: ξεῖνον, ξεινίσσομεν, πομπῆς, ξεῖνος, πομπῇ; AGLDT treebank text).
2. Annotate with existing FrameNet 1.7 frames only: targets, frame elements with 0-based, end-inclusive offsets, null instantiations (CNI / DNI / INI), and caveats for words left unannotated.
3. Check that every span matches its offsets and every frame element exists. Both runs: 0 problems.

### Stage 5: Render and compare

1. Render both runs in the original formats: frame-assignment CSV, FrameNet HTML, Obsidian lemma notes, and JSON / XML / HTML per passage.
2. Compare run A with run B, and both with the original experiment on the five shared lemmas and on Odyssey 1.123–124.

## Results

### Frame assignments

| | Run A (without WordNet) | Run B (with WordNet) |
| --- | --- | --- |
| Sense–frame pairings | 52 | 62 |
| Proposed new frames | Guest_friendship, Tending | Guest_friendship, Tending |
| Same primary frame | 14 of 18 lemmas | |
| Mean overlap of frame sets per lemma | 0.58 | |

Primary frames on which the runs differ:

| Lemma | Run A | Run B | WordNet data? |
| --- | --- | --- | --- |
| ξενίζω | Guest_and_host | Have_visitor_over | yes: "have as a guest", "receive into one's home" |
| δαιτυμών | Social_event | Guest_and_host | yes: "guest, invitee" |
| ὑποδεξίη | Have_visitor_over | Hospitality | none |
| ταμίας | Being_in_control | Supply | none |

Run B's extra pairings come mostly from WordNet senses, e.g. ξένος → Foreign_or_domestic_country, Member_of_military (mercenary); ξενία → Temporary_stay; πομπή → Entourage, Being_obligated; θεραπεύω → Cure.

### Proposed frames

Both runs, independently and under the same names, proposed:

- **Guest_friendship.** A lasting, reciprocal, often inherited bond between two guest-friends of different communities, sealed by gifts. Inherits Personal_relationship; uses Guest_and_host. Core FEs: Partner_1, Partner_2, Partners. It corresponds to Ritualized_guest_friendship in the original experiment.
- **Tending.** A Caretaker gives ongoing care to a person, animal, plant or property. Inherits Intentionally_act; uses Assistance. FrameNet 1.7 has no frame for *tend* or *look after*.

### Passage annotations

| Passage | Run A | Run B | Same frame on shared targets |
| --- | --- | --- | --- |
| Odyssey 1.123–124 | 7 sets | 7 sets | 4 of 7 |
| Odyssey 7.189–196 | 26 sets | 30 sets | 22 of 26 |

### Comparison with the original experiment

| Lemma | Original primary | Run A | Run B |
| --- | --- | --- | --- |
| ξένος | Guest_and_host | Guest_and_host | Guest_and_host |
| ξενίζω | Provide_lodging | Guest_and_host | Have_visitor_over |
| ξενία | Ritualized_guest_friendship (proposed) | Hospitality | Hospitality |
| ξεινήιον | Giving | Giving | Giving |
| φιλόξενος | Hospitality | Hospitality | Hospitality |

In both runs ξενία has Guest_friendship as an alternative frame. On Odyssey 1.123–124 the three annotations agree on ξεῖνε (Guest_and_host), πασσάμενος (Ingestion) and χρή (Needing). They differ on φιλήσεαι (Provide_lodging / Guest_and_host / Have_visitor_over), and both runs also annotate ἔπειτα and δείπνου.

## Outputs

| File | Format | Content |
| --- | --- | --- |
| `cluster128_terms_table.md` | Markdown | Vocabulary list |
| `AGWN_PWN/cluster128_field_wordnet_full.csv` | CSV | 2,168 AGWN synsets resolved to PWN 3.0, with flags |
| `AGWN_PWN/cluster128_field_links.html` | HTML | Browsable WordNet layer |
| `A_without_wordnet/`, `B_with_wordnet/` | CSV, HTML, JSON, XML, Markdown | Per run: frame assignments, FrameNet page, proposed frames, lemma notes, two passage annotations, method notes |
| `comparison/` | Markdown, CSV | A vs. B, and both vs. the original |
| `experiment.json`, `../wordnet_framenet_pipeline/pipeline.py`, `common/check_frames.py` | JSON, Python | Settings for this cluster; the pipeline for stages 1, 2 and 5; the FrameNet check for stages 3–4 |

## Caveats

The frame assignments and annotations are drafts for team review, not validated data.

- **One run per condition.** Two of the four primary-frame differences (ὑποδεξίη, ταμίας) are on lemmas without any WordNet data, so they come from run-to-run variation, not from WordNet. Separating the WordNet effect from this variation needs several runs per condition.
- **Same model, same prior knowledge.** Run A had no WordNet data but still knows Greek: it found senses such as ξενίζω "surprise" without WordNet. The comparison measures what WordNet adds to a model that already knows the language.
- **Model judgment.** Senses, frames, proposed frames and annotations are Claude Opus 5.5's proposals. The original experiment used Claude Opus 4.8.
- **Inputs differ from the original.** The cluster's LSJ glosses are truncated at about 90 characters, and the WordNet layer comes from the AGWN dump, not the live API. The PWN 3.0 matches were made by a script that picks the same target as the original on 77% of the 482 shared synsets.
- **Check the Greek text.** Verify both passages against a critical edition before reusing the offsets.
