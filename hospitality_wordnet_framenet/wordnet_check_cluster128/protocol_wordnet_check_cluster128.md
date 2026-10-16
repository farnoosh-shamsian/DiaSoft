# Protocol: WordNet Check of Gloss-Embedding Cluster 128 (hospitality, escort, service)

Oct 15, 2026, revised Oct 16, 2026 · Farnoosh Shamsian

Model: Claude Opus 5.5 (`claude-opus-5-5`), run in Claude Code.

## Summary

**Aim.** Find out how well Ancient Greek WordNet (AGWN) covers the lemmas of a semantic cluster, and which of its synset links are real senses. This is the first step towards the FrameNet layer (`../cluster128_k200/`), and a redo of the WordNet stage of the ξενία / προξενία protocol with the lemmas of a cluster: cluster 128 ("guest, hospitality, escort, attendant") of the Ward k=200 gloss-embedding clustering of Homeric lemmas.

**Result.** Of the cluster's 18 lemmas, 15 are linked to 2,168 synsets in AGWN. Most links are noise: 42 senses were judged core and 126 plausible. On ξενία the flags agree with the original protocol's manual flags on 73 of 78 synsets (Cohen's κ = 0.82). This check was not blind (see Caveats). No FrameNet annotation was done in this round.

## Materials

| Resource | Version and source | In this repository |
| --- | --- | --- |
| Cluster | Ward k=200 gloss-embedding clustering, no frequency limit; cluster 128 (20 entries) | `input/clusters_ward_k200_no-freq-limit.txt`, `input/cluster_128.txt` |
| Lemma list | The 18 lemmas after merging, with groups and AGWN spellings | `input/lemmas.csv` |
| Ancient Greek WordNet | SQL dump from GitHub `jcuenod/greekwordnet`, branch `master`: `greek_index.sql`, `english_synset.sql`, `common_relation.sql` (MultiWordNet 1.5 format). Downloaded Oct 15, 2026; the commit was not recorded. | No. Download URLs in `../README.md`; downloaded into `../agwn_dump/`, which is ignored by git |
| Reference flags | `greek_hospitality_wordnet_annotated.csv` from the original protocol (9 lemmas, 365 rows) | No, shared within the team |
| Software | Python 3.12.5, standard library only | `extract_synsets.py`, `build_flagged_csv.py` |

## Protocol

The work ran in five stages.

### Stage 1: Take the word list from the cluster

1. Take cluster 128 (20 entries) from `input/clusters_ward_k200_no-freq-limit.txt`.
2. Merge duplicates: ξένος / ξένος2 (homograph entries) and τάμιας / ταμίας (accent variants), leaving 18 lemmas.
3. Group the lemmas by meaning: guest/hospitality (9), escort (4), attendant/service (5).

### Stage 2: Extract the AGWN synsets

1. Query the live AGWN API (`greekwordnet.chs.harvard.edu`). On Oct 13, 2026 the host did not answer (connection timed out), so use the AGWN database dump instead.
2. Match exact lemma fields (Unicode NFC), not substrings, because ξενία is contained in προξενία.
3. Where the Homeric spelling is missing, try the AGWN spelling (ξεινήιον → ξεινήϊον, οἰνοχόος → οἰνόχοος).
4. Export every synset linked to each lemma with its English words, gloss and hypernym (`extract_synsets.py`).
5. Confirm that the dump holds the same data as the original protocol: ξενία and ξένος return the same 78 and 150 synsets.

### Stage 3: Separate real senses from noise

1. Flag each synset with one of three categories, judging its English words and gloss against the Greek sense in LSJ:
   - **core**: a main sense of the Greek word.
   - **plausible**: a secondary sense, including later senses attested in LSJ, or a closely related concept that the word's meaning directly involves.
   - **noise**: a sense brought in by a different meaning of an English gloss word, e.g. "receive (a guest)" → the radio-receiver sense of *receive*.
2. The flags are the judgment of Claude Opus 5.5, which read every synset. AGWN itself gives every link equal weight.
3. Record a one-line reason for every core and plausible flag (`output/agent_flags.csv`). Every synset not listed there was judged noise.

### Stage 4: Export

1. Merge the synsets and flags into one CSV with the columns of the original protocol's CSV, sorted core → plausible → noise, with `flag_method` = `agent` (`build_flagged_csv.py`).
2. Write a summary of counts per lemma and of the comparison (`output/summary.txt`).

### Stage 5: Compare with the original protocol

1. Compare the flags on the two lemmas that both share: ξενία (manual flags in the original) and ξένος (heuristic, unreviewed flags in the original).
2. Report percent agreement, Cohen's κ, and every disagreement by category.

## Deviations from the planned procedure

The plan written on Oct 13, 2026 (`PROMPT.md`) differs from what was done on Oct 15:

| Planned | Done | Reason |
| --- | --- | --- |
| Read a snapshot of the live AGWN API (`fetch_agwn.py` → `input/agwn_snapshot/`) | Read the AGWN database dump | The API host did not answer. `fetch_agwn.py` was never run and `input/agwn_snapshot/` is empty. |
| Flag by a deterministic rule (core = the synset's English words overlap the cluster's LSJ gloss vocabulary; plausible = only its hypernym overlaps), `flag_method` = `rule` | Flag by model judgment, `flag_method` = `agent` | Decided on Oct 15 to follow the original protocol, whose flags are also model judgment. The rule was never implemented, so the flags cannot be regenerated by a script. |
| Outputs `flag_synsets.py` and `report.md` | `extract_synsets.py`, `build_flagged_csv.py` and `summary.txt` | Follows from the change of method. |

## Results

### WordNet coverage

| Group | Lemmas | Synsets linked | Core | Plausible | Noise |
| --- | --- | --- | --- | --- | --- |
| Guest / hospitality | ξένος, ξένιος, ξενίζω, ξενία, ξενοσύνη, ξεινήιον, φιλόξενος, δαιτυμών | 568 | 18 | 50 | 500 |
| Escort | πομπή, πομπός, πομπεύς, πομπεύω | 562 | 12 | 28 | 522 |
| Attendant / service | θεραπεύω, ἀμφιπολεύω, οἰνοχόος | 1,038 | 12 | 48 | 978 |
| **Total** | 15 | **2,168** | **42** | **126** | **2,000** |

The table lists the 15 lemmas with synsets. ὑποδεξίη (guest / hospitality), ὑποδρηστήρ and ταμίας (attendant / service) are in AGWN but have no synsets linked. Counts per lemma are in `output/summary.txt`.

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

| Lemma | Original flags | Same flag | Cohen's κ | Disagreements (original → this check) |
| --- | --- | --- | --- | --- |
| ξενία | manual | 73 of 78 (94%) | 0.82 | noise → plausible 2; plausible → noise 3 |
| ξένος | heuristic | 116 of 150 (77%) | 0.22 | core → plausible 6; core → noise 2; noise → plausible 10; plausible → noise 16 |

Because most synsets are noise in both flag sets, percent agreement is high by chance alone; κ corrects for this. On ξενία the four core senses are the same and agreement is high. On ξένος agreement is low: the two flag sets share only 1 of their 17 plausible senses each, and the original's 12 core senses include 8 that this check did not keep as core. The original's ξένος flags were made heuristically and never reviewed, so this comparison shows that the two methods differ, not which one is right.

### Why the noise appears

As in the original protocol, AGWN attached every sense of a polysemous English gloss word. Here the verbs carry most of the noise: θεραπεύω, πομπεύω, ἀμφιπολεύω and ξενίζω have 1,653 of the 2,168 synsets, pulled in by "make", "take", "hold", "carry" and "run". Examples: "make" brought defecate; "dress" brought dress a salad; "sweet" brought sweet wine (ξένος); "date" brought the date palm (πομπή).

## Outputs

| File | Format | Content |
| --- | --- | --- |
| `output/cluster128_synsets_raw.csv` | CSV | Every AGWN synset for the cluster's lemmas, as extracted (stage 2) |
| `output/agent_flags.csv` | CSV | The 168 core and plausible flags, each with a one-line reason (stage 3) |
| `output/cluster128_wordnet_flagged.csv` | CSV | 2,168 rows with the original protocol's columns: English words, gloss, hypernym, flag, `flag_method` = `agent` (stage 4) |
| `output/summary.txt` | Text | Counts per lemma and the comparison with the original flags (stages 4–5) |
| `extract_synsets.py`, `build_flagged_csv.py` | Python | Scripts for stages 2 and 4–5 |
| `PROMPT.md`, `fetch_agwn.py` | Markdown, Python | The original plan and its API fetcher, kept for the record; not used (see Deviations) |

## Reproducing

1. Download the three AGWN SQL files into `../agwn_dump/` (URLs in `../README.md`).
2. `py extract_synsets.py` writes `output/cluster128_synsets_raw.csv`.
3. `py build_flagged_csv.py` merges it with `output/agent_flags.csv` into `output/cluster128_wordnet_flagged.csv`. It rewrites `output/summary.txt` with the stage 5 comparison only if the original protocol's CSV is placed in `input/`; otherwise it leaves the summary as it is.

Stages 2, 4 and 5 are deterministic. Stage 3 is not: a new flagging by the same or another model will differ, so reuse `output/agent_flags.csv` to reproduce these results.

## Caveats

The flags are drafts for team review, not validated data.

- **Flags are model judgment.** Core / plausible / noise was decided by Claude Opus 5.5 reading each gloss. A team member should confirm at least the core and plausible rows.
- **The ξενία check is not blind.** The flags were made in the same session in which the original protocol's CSV, including its ξενία flags, had already been read. The agreement of 94% (κ = 0.82) is therefore an upper bound, not an independent validation.
- **Categories inferred.** The original protocol gives examples of core and plausible but no definitions. The definitions in stage 3 were written to fit those examples.
- **Dump, not live API.** The dump may predate manual corrections in the live AGWN, and the commit it came from was not recorded.
- **Gaps in AGWN.** ξένος is linked only as an adjective, so "guest-friend" is missing; φιλόξενος has no "hospitable" synset.
