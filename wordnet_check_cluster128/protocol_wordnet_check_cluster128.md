# Protocol: WordNet Check of Gloss-Embedding Cluster 128 (hospitality, escort, service)

Oct 15, 2026 · Farnoosh Shamsian

Model: Claude Opus 5.5 (`claude-opus-5-5`), run in Claude Code.

## Summary

The WordNet stage of the ξενία / προξενία protocol was redone with the lemmas of a cluster: cluster 128 ("guest, hospitality, escort, attendant") of the Ward k=200 gloss-embedding clustering of Homeric lemmas. Of its 18 lemmas, 15 are linked to 2,168 synsets in Ancient Greek WordNet (AGWN). Most links are noise: 42 senses were judged core and 126 plausible. On ξενία, the flags agree with the original protocol's manual flags on 73 of 78 synsets. No FrameNet annotation was done in this round.

## Protocol

The work ran in four stages.

### Stage 1: Take the word list from the cluster

1. Take cluster 128 (20 entries) from `clusters_ward_k200_no-freq-limit.txt`.
2. Merge duplicates: ξένος / ξένος2 (homograph entries) and τάμιας / ταμίας (accent variants), leaving 18 lemmas.
3. Group the lemmas by meaning: guest/hospitality (9), escort (4), attendant/service (5).

### Stage 2: Check WordNet coverage

1. Query the AGWN API (`greekwordnet.chs.harvard.edu`). It did not respond, so use the AGWN database dump in the GitHub repository `jcuenod/greekwordnet` instead.
2. Match exact lemma fields, not substrings.
3. Where the Homeric spelling is missing, try the AGWN spelling (ξεινήιον → ξεινήϊον, οἰνοχόος → οἰνόχοος).
4. Confirm the dump matches the data of the original protocol: ξενία and ξένος return the same 78 and 150 synsets.

### Stage 3: Separate real senses from noise

1. Export every synset linked to each lemma with its English words, gloss and hypernym.
2. Flag each synset core, plausible or noise by reading the gloss against the Greek sense in LSJ. These flags are the judgment of Claude Opus 5.5; AGWN gives every link equal weight.
3. Record a one-line reason for every core and plausible flag.
4. Compare the flags with the original protocol on the two lemmas both share (ξενία, ξένος).

### Stage 4: Export

1. Save all rows as a CSV with the columns of `greek_hospitality_wordnet_annotated.csv`, sorted core → plausible → noise.
2. Write a summary of counts per lemma and of the comparison.

## Results

### WordNet coverage

| Group | Lemmas | Synsets linked | Core | Plausible | Noise |
| --- | --- | --- | --- | --- | --- |
| Guest / hospitality | ξένος, ξένιος, ξενίζω, ξενία, ξενοσύνη, ξεινήιον, φιλόξενος, δαιτυμών | 568 | 18 | 50 | 500 |
| Escort | πομπή, πομπός, πομπεύς, πομπεύω | 562 | 12 | 28 | 522 |
| Attendant / service | θεραπεύω, ἀμφιπολεύω, οἰνοχόος | 1,038 | 12 | 48 | 978 |
| **Total** | 15 | **2,168** | **42** | **126** | **2,000** |

ὑποδεξίη, ὑποδρηστήρ and ταμίας are in AGWN but have no synsets linked.

### Core senses kept

| Lemma | Senses |
| --- | --- |
| ξένος | foreign; alien, strange; foreign-born; visiting, guest |
| ξένιος | hospitable |
| ξενίζω | welcome; entertain; have as a guest; receive into one's home; take in |
| ξενία | hospitality; guest, invitee; guest, visitor; friendship |
| ξενοσύνη | hospitality |
| ξεινήιον | gift |
| δαιτυμών | guest, invitee; guest, visitor |
| πομπή | escort; ceremonial procession; sending |
| πομπός | guide; escort; bodyguard |
| πομπεύς | guide; usher |
| πομπεύω | escort (2); lead, conduct; march in procession |
| θεραπεύω | attend, wait on; serve; worship; treat medically; cure; care for |
| ἀμφιπολεύω | attend, wait on; minister; care for; tend (2) |
| οἰνοχόος | cupbearer |

Notable plausible senses: for ξένος, mercenary, unacquainted with, non-citizen; for ξενίζω, astonish, give as a present; for ξενία, lawsuit (γραφὴ ξενίας), lodging, guest-gifts; for πομπεύω, revile (from the jests of processions); for θεραπεύω, honour, court, cultivate, heal.

### Comparison with the original protocol

| Lemma | Original flags | Same flag |
| --- | --- | --- |
| ξενία | manual | 73 of 78 (94%); same 4 core senses |
| ξένος | heuristic | 116 of 150 (77%) |

### Why the noise appears

As in the original protocol, AGWN attached every sense of a polysemous English gloss word. Here the verbs carry most of the noise: θεραπεύω, πομπεύω, ἀμφιπολεύω and ξενίζω have 1,653 of the 2,168 synsets, pulled in by "make", "take", "hold", "carry" and "run". Examples: "make" brought defecate; "dress" brought dress a salad; "sweet" brought sweet wine (ξένος); "date" brought the date palm (πομπή).

## Outputs

| File | Format | Content |
| --- | --- | --- |
| `cluster128_wordnet_flagged.csv` | CSV | 2,168 rows: every AGWN synset for the cluster's lemmas with English words, gloss, hypernym and core / plausible / noise flag |
| `agent_flags.csv` | CSV | The 168 core and plausible flags, each with a one-line reason |
| `summary.txt` | Text | Counts per lemma and the comparison with the original flags |
| `extract_synsets.py`, `build_flagged_csv.py` | Python | Scripts for stages 2 and 4 |

## Caveats

The flags are drafts for team review, not validated data.

- **Flags are model judgment.** Core / plausible / noise was decided by Claude Opus 5.5 reading each gloss; a team member should confirm at least the core and plausible rows.
- **Dump, not live API.** The dump may predate manual corrections in the live AGWN.
- **Gaps in AGWN.** ξένος is linked only as an adjective, so "guest-friend" is missing; φιλόξενος has no "hospitable" synset.
- **Categories inferred.** The original protocol gives examples of core and plausible but no definitions; the categories here follow those examples.
