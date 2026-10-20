# Protocol: WordNet and FrameNet Mapping of Gift and Hospitality Cluster 98 (k=150), with and without WordNet

Oct 16, 2026 · Farnoosh Shamsian

Model: Claude Opus 5.5 (`claude-opus-5-5`), run in Claude Code.

## Summary

The hospitality WordNet & FrameNet experiment was redone on the 50 lemmas of gloss-embedding cluster 98 (Ward k=150), which contains all of cluster 128 plus the vocabulary of giving, receiving, honour and possessions. As for cluster 128 it was run twice, run A without WordNet and run B with the WordNet layer, each by a separate, fresh agent. Both runs proposed three new frames, two of them the same in both runs (Guest_friendship, and an honour-privilege frame under two names). Run B produced more sense–frame pairings (146 vs. 134); the runs agree on the primary frame of 37 of 50 lemmas, 41 counting the two names of the honour frame as one.

## Protocol

The work ran in five stages, as for cluster 128, with the shared pipeline (`../pipeline/pipeline.py`).

### Stage 1: Take the word list from the cluster

1. Take cluster 98 (52 entries) from the Ward k=150 clustering; merge ξένος ‘guest, stranger; guest-friend’ / ξένος2 and τάμιας ‘steward’ / ταμίας ‘steward, dispenser’, leaving 50 lemmas in nine groups.
2. Take each lemma's LSJ glosses from the cluster file and its part of speech from the AGLDT treebank.
3. Write the vocabulary list (`cluster98_k150_terms_table.md`).

### Stage 2: Build the WordNet layer

1. Extract every AGWN synset of each lemma from the AGWN database dump, matching exact lemmas: 14,466 synsets for 45 lemmas; ὑποδεξίη ‘means of entertaining guests’, ὑποδέχομαι ‘receive (as a guest)’, ἀγέραστος ‘without a gift of honour’, ταμίας ‘steward, dispenser’ and ὑποδρηστήρ ‘attendant’ have none.
2. Flag each synset core, plausible or noise. The 15 lemmas shared with cluster 128 keep their cluster-128 flags (2,168 synsets). The other 12,298 synsets were split into four batches and flagged by four parallel agents, each reading every synset, with the written criteria (`AGWN_PWN/FLAGGING_CRITERIA.md`) and the cluster-128 flags as calibration. Result: 144 core, 482 plausible, 13,840 noise.
3. Resolve each synset to Princeton WordNet 3.0 and label the match `exact_gloss`, `gloss+lemma`, `lemma_set` or `unresolved`.

### Stage 3: Map the lemmas to FrameNet, twice

1. Prepare identical inputs for both runs: the lemma list, the cluster, the two passages with treebank lemmas and offsets, the format specification, and the FrameNet 1.7 lookup and validation tool. Run B also gets the WordNet layer.
2. Give each run to a fresh agent that may read only its inputs (and the Homer treebanks, to check usage and citations).
3. Each agent maps every lemma to one primary and any alternative FrameNet 1.7 frames, proposes a new frame only where none exists, and records the senses it used.
4. Check every existing frame and its core frame elements against the FrameNet 1.7 data. Both runs: 0 problems.

### Stage 4: Annotate two Homeric passages

1. Odyssey 1.123–124 (same text as the original experiment) and Odyssey 8.544–545, the treebank sentence with the most distinct cluster lemmas, shortest first: ξείνοιο ‘of the guest’, πομπή ‘escort, conveyance home’, δῶρα ‘gifts’, δίδομεν ("for the honoured stranger's sake all this is made ready: his escort home and the dear gifts that we give him in friendship").
2. Annotate with existing FrameNet 1.7 frames only: targets, frame elements with 0-based, end-inclusive offsets, null instantiations, and caveats for words left unannotated.
3. Check that every span matches its offsets and every frame element exists. Both runs: 0 problems.

### Stage 5: Render and compare

1. Render both runs in the original formats: frame-assignment CSV, FrameNet HTML, Obsidian lemma notes, and JSON / XML / HTML per passage.
2. Compare run A with run B, both with the original experiment, and both with cluster 128 on the 18 shared lemmas.

## Results

### Frame assignments

| | Run A (without WordNet) | Run B (with WordNet) |
| --- | --- | --- |
| Sense–frame pairings | 134 | 146 |
| Proposed new frames | Guest_friendship, Honorific_prerogative, Plaything | Guest_friendship, Honorific_privilege, Apportioning |
| Same primary frame | 37 of 50 lemmas (41 counting the two honour-frame names as one) | |
| Mean overlap of frame sets per lemma | 0.63 | |

Primary frames on which the runs differ (besides the honour-frame name):

| Lemma | Gloss | Run A | Run B | WordNet data? |
| --- | --- | --- | --- | --- |
| ξενίζω | receive as a guest, entertain | Provide_lodging | Have_visitor_over | yes |
| δαιτυμών | guest at a feast | Social_event | Guest_and_host | yes: "guest, invitee" |
| ὑποδέχομαι | receive (as a guest) | Have_visitor_over | Receive_visitor_scenario | none |
| ἀναδέχομαι | take up; endure | Receiving | Tolerating | yes: "digest, endure" |
| νέμω | deal out, distribute | Giving | Apportioning (proposed) | yes: "distribute", "share", "assign" |
| δοτήρ | giver, dispenser | Supply | Giving | yes |
| ἄθυρμα | plaything, toy | Plaything (proposed) | Artifact | yes |
| γλῆνος | trinkets, pretty things | Accoutrements | Possession | yes |
| ἀμφιπολεύω | tend, take care of | Subordinates_and_superiors | Assistance | yes |

Run B's extra pairings come mostly from WordNet senses, e.g. δέχομαι ‘receive, accept’ → Relative_time ("follow, come next"), δίδωμι ‘give’ → Exchange, Forming_relationships, παρέχω ‘provide, furnish’ → Preventing_or_letting, ἐπιδίδωμι ‘give besides; (mid.) take as witnesses’ → Change_position_on_a_scale ("increase"), νέμω ‘deal out, distribute’ → Fire_burning.

### Proposed frames

- **Guest_friendship** (both runs): a lasting, reciprocal, often inherited bond between guest-friends of different communities, sealed by gift-tokens. It was proposed in all four runs of the two clusters.
- **Honorific_prerogative / Honorific_privilege** (both runs, two names): a community, leader or host allots someone a share or privilege — a prize, a choice portion, burial honours — in recognition of status, age or merit.
- **Plaything** (run A): an object kept for amusement rather than use.
- **Apportioning** (run B): a Distributor divides a stock into shares for many Recipients; FrameNet's Giving covers a single transfer, Dispersal is spatial.

Tending, proposed in both cluster-128 runs for ἀμφιπολεύω ‘tend, take care of’ and θεραπεύω ‘serve, attend; take care of’, was not proposed here: both runs used existing service frames instead.

### Passage annotations

| Passage | Run A | Run B | Same frame on shared targets |
| --- | --- | --- | --- |
| Odyssey 1.123–124 | 8 sets | 8 sets | 8 of 8 |
| Odyssey 8.544–545 | 7 sets | 8 sets | 7 of 7 |

### Comparison with the original experiment and with cluster 128

| Lemma | Gloss | Original primary | Run A | Run B |
| --- | --- | --- | --- | --- |
| ξένος | guest, stranger; guest-friend | Guest_and_host | Guest_and_host | Guest_and_host |
| ξενίζω | receive as a guest, entertain | Provide_lodging | Provide_lodging | Have_visitor_over |
| ξενία | hospitality, guest-friendship | Ritualized_guest_friendship (proposed) | Hospitality | Hospitality |
| ξεινήιον | guest-gift | Giving | Giving | Giving |
| φιλόξενος | hospitable, kind to strangers | Hospitality | Hospitality | Hospitality |

On Odyssey 1.123–124 the original and both runs agree on ξεῖνε ‘stranger’ (Guest_and_host), πασσάμενος ‘having tasted’ (Ingestion), μυθήσεαι ‘you will tell’ (Telling) and χρή ‘need’ (Needing); for φιλήσεαι ‘you will be made welcome’ the original has Provide_lodging and both runs Have_visitor_over.

The 18 lemmas shared with cluster 128 get the same primary frame in both clusters for 14 of 18 (without WordNet) and 15 of 18 (with WordNet).

## Outputs

| File | Format | Content |
| --- | --- | --- |
| `cluster98_k150_terms_table.md` | Markdown | Vocabulary list |
| `AGWN_PWN/cluster98_k150_field_wordnet_full.csv` | CSV | 14,466 AGWN synsets resolved to PWN 3.0, with flags |
| `AGWN_PWN/cluster98_k150_field_links.html` | HTML | Browsable WordNet layer |
| `AGWN_PWN/sense_flags.csv`, `AGWN_PWN/FLAGGING_CRITERIA.md` | CSV, Markdown | The 626 kept senses with reasons; the flagging criteria |
| `A_without_wordnet/`, `B_with_wordnet/` | CSV, HTML, JSON, XML, Markdown | Per run: frame assignments, FrameNet page, proposed frames, lemma notes, two passage annotations, method notes |
| `comparison/` | Markdown, CSV | A vs. B, and both vs. the original |
| `experiment.json`, `../pipeline/pipeline.py`, `common/check_frames.py` | JSON, Python | Settings for this cluster; the pipeline for stages 1, 2 and 5; the FrameNet check for stages 3–4 |

## Caveats

The flags, frame assignments and annotations are drafts for team review, not validated data.

- **One run per condition.** Some differences between A and B come from run-to-run variation, not from WordNet: ὑποδέχομαι ‘receive (as a guest)’ has no WordNet data but still differs, and both runs reached some decisions (προσδέχομαι ‘wait for; receive, accept’ → Waiting, ἀμοιβός ‘relief; one who exchanges’ → Take_place_of) from Homeric usage in the treebank, with or without WordNet.
- **Same model, same prior knowledge.** Run A had no WordNet data but knows Greek; the comparison measures what WordNet adds to a model that already knows the language.
- **Flags by several agents.** Most of the 14,466 synsets were flagged by four agents rather than one reader; consistency rests on the shared criteria and calibration file.
- **Cluster noise.** ἀφήκω ‘arrive; depart’ has no genuine Homeric occurrence: its only treebank token (Il. 8.133) is a form of ἀφίημι ‘let go, let fly’, mislemmatized. The treebank also files some ξεινήιον ‘guest-gift’ forms under ξένιος ‘of guests, hospitable’.
- **Frame names.** Proposed frames are matched by name across runs; the honour frame is the one case of the same frame under two names.
- **Check the Greek text.** Verify both passages against a critical edition before reusing the offsets.
