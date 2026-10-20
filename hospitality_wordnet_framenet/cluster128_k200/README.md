# Homeric Hospitality Cluster 128 — WordNet & FrameNet

The *Ancient Greek Hospitality — WordNet & FrameNet* experiment (July 2026), redone with the lemmas of a cluster: cluster 128 ("guest, hospitality, escort, attendant") of the Ward k=200 gloss-embedding clustering of Homeric lemmas.
Ancient Greek WordNet + Princeton WordNet 3.0 + FrameNet 1.7.
Done on October 15–16, 2026, with Claude Opus 5.5.

The experiment was run twice, once **without** and once **with** WordNet, to see what the WordNet layer contributes to the frame assignments. Each run was done by a separate, fresh Claude Opus 5.5 agent that saw only its own inputs.

Eighteen lemmata in three groups:

- **guest/hospitality:** ξένος ‘guest, stranger; guest-friend’, ξένιος ‘of guests, hospitable’, ξενίζω ‘receive as a guest, entertain’, ξενία ‘hospitality, guest-friendship’, ξενοσύνη ‘guest-friendship’, ξεινήιον ‘guest-gift’, ὑποδεξίη ‘means of entertaining guests’, φιλόξενος ‘hospitable, kind to strangers’, δαιτυμών ‘guest at a feast’
- **escort:** πομπή ‘escort, conveyance home’, πομπός ‘escort, guide’, πομπεύς ‘escort, conductor’, πομπεύω ‘escort, conduct’
- **attendant/service:** θεραπεύω ‘serve, attend; take care of’, ἀμφιπολεύω ‘tend, take care of’, οἰνοχόος ‘wine-pourer’, ὑποδρηστήρ ‘attendant’, ταμίας ‘steward, dispenser’

## Folder contents

```
cluster128_k200/
├── cluster128_terms_table.md            Source vocabulary list (LSJ glosses, Logeion links)
├── protocol_cluster128_k200.md
├── AGWN_PWN/                            WordNet layer (used by run B only)
│   ├── agwn_synsets_raw.csv                AGWN synsets extracted from the database dump
│   ├── sense_flags.csv                     The core and plausible flags, with reasons
│   ├── cluster128_field_wordnet_full.csv   Every AGWN synset per lemma, resolved to
│   │                                       Princeton WordNet 3.0, flagged core/plausible/noise (2,168 rows)
│   ├── WORDNET_LAYER.md                    Description of the layer, as given to run B
│   └── cluster128_field_links.html         Browsable table with clickable links
├── A_without_wordnet/                   Run A: senses from LSJ glosses only
│   ├── FrameNet/
│   │   ├── cluster128_field_framenet_full.csv   Frame assignments per lemma (52 rows)
│   │   ├── cluster128_framenet.html             Browsable assignments + proposed frames
│   │   ├── proposed_frames.json
│   │   ├── lemma_senses.csv
│   │   └── Lemmata/                             18 Obsidian notes, one per lemma
│   ├── Homer_Odyssey_examples/          Odyssey 1.123–124 and 7.189–196, as JSON, XML and HTML
│   └── method_notes.md                  The run's own account of its decisions
├── B_with_wordnet/                      Run B: senses from LSJ glosses + the WordNet layer
│   └── (same structure; 62 frame-assignment rows)
├── comparison/
│   ├── comparison.md                    A vs. B, and both vs. the original experiment
│   ├── lemma_frames.csv
│   └── passage_targets.csv
├── common/                              Inputs given to both runs, the format specification,
│                                        and the exact prompts of both runs (run_prompts.md)
└── experiment.json                      Cluster, lemmas, groups and passages; read by
                                         ../pipeline/pipeline.py
```

## The WordNet layer (`AGWN_PWN/`)

Each AGWN synset of a lemma is listed and resolved to a Princeton WordNet 3.0 synset. Columns as in the original, plus the sense flags from the earlier WordNet check:

- `agwn_synset_id`, `agwn_gloss` — the Ancient Greek WordNet synset and its gloss
- `pwn30_synset`, `pwn30_offset`, `sense_key` — the Princeton WordNet 3.0 match
- `id_match` — match confidence (`exact_gloss` > `gloss+lemma` > `lemma_set` > `unresolved`)
- `sense_flag`, `flag_reason` — core / plausible / noise, with a reason for each kept sense
- `agwn_synset_url`, `pwn_url` — live AGWN entry and the concept on Open English WordNet

## The FrameNet layer (`A_…/FrameNet/`, `B_…/FrameNet/`)

Each lemma is mapped to the FrameNet frame(s) it evokes: one primary frame and alternatives, with the frame's core frame elements and how the Greek participant fills a role. Both runs proposed the same two new frames where FrameNet 1.7 has none:

- **Guest_friendship** — the lasting, reciprocal bond between guest-friends (ξενοσύνη ‘guest-friendship’, ξένος ‘guest, stranger; guest-friend’, ξενία ‘hospitality, guest-friendship’)
- **Tending** — ongoing care of a person, animal, plant or property (ἀμφιπολεύω ‘tend, take care of’, θεραπεύω ‘serve, attend; take care of’)

The `Lemmata/` notes are for **Obsidian** (YAML frontmatter, tags, `[[wikilinks]]`). In run B they also list each lemma's WordNet senses.

## Provenance

- **Frames** = Berkeley FrameNet 1.7 (English). Every existing frame and frame element in both runs was checked against the FrameNet 1.7 data (`check_frames.py`).
- **Greek senses** = LSJ glosses of the cluster (both runs); plus the Ancient Greek WordNet layer (run B).
- **Word-to-frame pairings and passage annotations** = analytical proposals by Claude Opus 5.5, to be validated against attested Greek text. The proposed frames are proposals, not sanctioned FrameNet entries.

## Live resources

- Ancient Greek WordNet — https://greekwordnet.chs.harvard.edu
- Open English WordNet — https://en-word.net
- Berkeley FrameNet — https://framenet.icsi.berkeley.edu
