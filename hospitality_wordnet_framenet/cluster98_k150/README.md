# Homeric Gift and Hospitality Cluster 98 (k=150) — WordNet & FrameNet

The *Ancient Greek Hospitality — WordNet & FrameNet* experiment (July 2026), redone with the lemmas of a cluster: cluster 98 ("gift, guest, receive, hospitality") of the Ward k=150 gloss-embedding clustering of Homeric lemmas. It contains all of cluster 128 (k=200) plus the vocabulary of giving, receiving, honour and possessions.
Ancient Greek WordNet + Princeton WordNet 3.0 + FrameNet 1.7.
Done on October 16, 2026, with Claude Opus 5.5.

The experiment was run twice, once **without** and once **with** WordNet, to see what the WordNet layer contributes to the frame assignments. Each run was done by a separate, fresh Claude Opus 5.5 agent that saw only its own inputs.

Fifty lemmata (52 cluster entries; ξένος / ξένος2 and τάμιας / ταμίας merged) in nine groups:

- **guest/hospitality:** ξενίζω, ξεινήιον, ξένιος, δαιτυμών, ξενοσύνη, φιλόξενος, ξένος, ξενία, ὑποδεξίη
- **receiving:** προσδέχομαι, ὑποδέχομαι, ἀναδέχομαι, δέχομαι, ἀποδέχομαι
- **gift/giving:** δῶρον, ἐπίηρα, δωρητός, δίδωμι, ἐπιδίδωμι, προσάγω, δωτίνη, προίξ, δωρέω, παρέχω, δόσις, νέμω, δοτήρ, εἰσφέρω
- **honour/privilege:** γεραίρω, πρεσβεῖον, γέρας, ἀγέραστος
- **possessions/treasure:** κτέρας, κτῆμα, ἄθυρμα, γλῆνος, κειμήλιον
- **exchange:** ἐπαμείβω, ἀμοιβός
- **escort:** πομπή, πομπεύω, πομπός, πομπεύς
- **attendant/service:** θεραπεύω, ἀμφιπολεύω, ταμίας, οἰνοχόος, ὑποδρηστήρ
- **other:** ἐπίμαστος, ἀφήκω

## Folder contents

```
cluster98_k150/
├── cluster98_k150_terms_table.md        Source vocabulary list (LSJ glosses, Logeion links)
├── protocol_cluster98_k150.md
├── AGWN_PWN/                            WordNet layer (used by run B only)
│   ├── agwn_synsets_raw.csv                AGWN synsets extracted from the database dump
│   ├── FLAGGING_CRITERIA.md                The criteria used to flag the synsets
│   ├── sense_flags.csv                     The core and plausible flags, with reasons
│   ├── cluster98_k150_field_wordnet_full.csv   Every AGWN synset per lemma, resolved to
│   │                                       Princeton WordNet 3.0, flagged core/plausible/noise (14,466 rows)
│   └── cluster98_k150_field_links.html     Browsable table with clickable links
├── A_without_wordnet/                   Run A: senses from LSJ glosses only
│   ├── FrameNet/
│   │   ├── cluster98_k150_field_framenet_full.csv   Frame assignments per lemma (134 rows)
│   │   ├── cluster98_k150_framenet.html             Browsable assignments + proposed frames
│   │   ├── proposed_frames.json
│   │   ├── lemma_senses.csv
│   │   └── Lemmata/                                 50 Obsidian notes, one per lemma
│   ├── Homer_Odyssey_examples/          Odyssey 1.123–124 and 8.544–545, as JSON, XML and HTML
│   └── method_notes.md                  The run's own account of its decisions
├── B_with_wordnet/                      Run B: senses from LSJ glosses + the WordNet layer
│   └── (same structure; 146 frame-assignment rows)
├── comparison/
│   ├── comparison.md                    A vs. B, and both vs. the original experiment
│   ├── lemma_frames.csv
│   └── passage_targets.csv
├── common/                              Inputs given to both runs, and the format specification
└── experiment.json                      Cluster, lemmas, groups and passages; read by
                                         ../pipeline/pipeline.py
```

## The WordNet layer (`AGWN_PWN/`)

Each AGWN synset of a lemma is listed and resolved to a Princeton WordNet 3.0 synset, with the same columns as in cluster 128:

- `agwn_synset_id`, `agwn_gloss` — the Ancient Greek WordNet synset and its gloss
- `pwn30_synset`, `pwn30_offset`, `sense_key` — the Princeton WordNet 3.0 match
- `id_match` — match confidence (`exact_gloss` > `gloss+lemma` > `lemma_set` > `unresolved`)
- `sense_flag`, `flag_reason` — core / plausible / noise, with a reason for each kept sense
- `agwn_synset_url`, `pwn_url` — live AGWN entry and the concept on Open English WordNet

Of 14,466 synsets, 626 are kept as real senses (144 core, 482 plausible). The 15 lemmas shared with cluster 128 keep their cluster-128 flags; the other synsets were flagged by four parallel agents with the same criteria (`FLAGGING_CRITERIA.md`), calibrated on the cluster-128 flags. ὑποδεξίη, ὑποδέχομαι, ἀγέραστος, ταμίας and ὑποδρηστήρ are in AGWN but have no synsets linked.

## The FrameNet layer (`A_…/FrameNet/`, `B_…/FrameNet/`)

Each lemma is mapped to the FrameNet frame(s) it evokes: one primary frame and alternatives, with the frame's core frame elements and how the Greek participant fills a role. New frames proposed where FrameNet 1.7 has none:

| Proposed frame | Run A | Run B | Lexical units |
| --- | --- | --- | --- |
| **Guest_friendship** — the lasting, reciprocal bond between guest-friends | ✓ | ✓ | ξενοσύνη, ξένος, ξενία, ξεινήιον (B also ξένιος, δωτίνη) |
| **Honorific_prerogative** (A) / **Honorific_privilege** (B) — a share or privilege allotted in recognition of status | ✓ | ✓ | γέρας, γεραίρω, πρεσβεῖον, ἀγέραστος (B also δῶρον) |
| **Plaything** — an object kept for amusement rather than use | ✓ | | ἄθυρμα, γλῆνος |
| **Apportioning** — dividing a stock into shares for many recipients | | ✓ | νέμω, δοτήρ, ταμίας |

The two honour frames are the same frame under two names; `experiment.json` records the equivalence, and the comparison counts both ways.

The `Lemmata/` notes are for **Obsidian** (YAML frontmatter, tags, `[[wikilinks]]`). In run B they also list each lemma's WordNet senses.

## Provenance

- **Frames** = Berkeley FrameNet 1.7 (English). Every existing frame and frame element in both runs was checked against the FrameNet 1.7 data (`check_frames.py`).
- **Greek senses** = LSJ glosses of the cluster (both runs); plus the Ancient Greek WordNet layer (run B).
- **Word-to-frame pairings, sense flags and passage annotations** = analytical proposals by Claude Opus 5.5, to be validated against attested Greek text. The proposed frames are proposals, not sanctioned FrameNet entries.

## Live resources

- Ancient Greek WordNet — https://greekwordnet.chs.harvard.edu
- Open English WordNet — https://en-word.net
- Berkeley FrameNet — https://framenet.icsi.berkeley.edu
