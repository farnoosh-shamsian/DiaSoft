# `wordnet_layer.csv`: Ancient Greek WordNet senses for the lemmas

Every Ancient Greek WordNet (AGWN) synset linked to each lemma (2,168 rows; ὑποδεξίη, ὑποδρηστήρ and ταμίας have none), resolved to Princeton WordNet 3.0, with a judgment of whether the synset is a real sense of the Greek word.

| Column | Meaning |
| --- | --- |
| `greek_lemma`, `translit`, `pos` | the Greek lemma |
| `agwn_synset_id`, `english_words`, `agwn_gloss` | the AGWN synset (PWN 1.6 / MultiWordNet ID), its English words and gloss |
| `pwn30_synset`, `pwn30_offset`, `sense_key`, `id_match` | the matched Princeton WordNet 3.0 synset and the match quality (`exact_gloss` > `gloss+lemma` > `lemma_set` > `unresolved`) |
| `sense_flag` | `core` (a main sense of the Greek word), `plausible` (a secondary sense or closely related concept), `noise` (brought in by another meaning of an English gloss word) |
| `flag_reason` | why a synset was judged core or plausible |
| `agwn_synset_url`, `pwn_url` | links |

AGWN links were generated automatically from Greek–English dictionaries, so most are noise (2,000 of 2,168). Use the core and plausible rows as evidence for which senses each lemma has.
