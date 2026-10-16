# Method notes: run A (LSJ glosses + own knowledge, no WordNet)

## Inputs used
- `lemmas.csv` (18 lemmas, LSJ glosses truncated at about 90 characters), `cluster_128.txt`, `passages.json`, `FORMAT_SPEC.md`.
- Berkeley FrameNet 1.7 through NLTK, searched with `check_frames.py search` / `frame`, plus direct NLTK queries for FE core types and core sets. The core FEs and definitions in the CSV are read programmatically from FN 1.7.
- The AGLDT treebanks (`homer_corpus/iliad_treebank.xml`, `odyssey_treebank.xml`), used only to check Homeric usage and verify citations. I pulled concordances of every cluster lemma by lemma attribute and checked line citations from each word's `cite` attribute. Watch out for the work test: `'tlg001' in cts` also matches the Odyssey's `tlg0012.tlg002`, so the test must be `tlg0012.tlg001`.
- No WordNet resource of any kind (AGWN, PWN, NLTK wordnet) was used.
- My own knowledge of Greek supplied senses that the truncated glosses cut off. These are flagged in `note`: ξενίζω 'surprise' (post-classical) and θεραπεύω 'treat medically'.

## Primary vs. alternative
- **Primary** is the sense best attested in Homer for the lemma's basic part of speech, judged from the treebank concordance. Where Homeric evidence is thin or absent, I fell back on the first LSJ gloss. Three cases follow from this rule:
  - ἀμφιπολεύω: 'tend, look after' (4 of 5 Homeric instances) beats LSJ's first gloss 'serve as an attendant' (Od. 20.78 only).
  - ταμίας: all three cluster instances are 'controller/dispenser' (Zeus of war, Il. 4.84 and 19.224; Aeolus of winds, Od. 10.21). The input gloss 'ship's officer in charge of provisions' is kept as an alternative.
  - ξένιος: the commonest Homeric use is the substantive τὰ ξείνια 'guest-gifts'. I still made the adjectival reading primary (Hospitality, 'hospitable / of guests') and listed the substantive as an alternative.
- **Alternatives** are given for every other real sense: Homeric senses first, then post-Homeric ones marked "post-Homeric". If two FN frames frame the same sense from different perspectives (e.g. ξενίζω: Guest_and_host / Have_visitor_over / Provide_lodging), the one whose core FEs best match the Homeric syntax is primary.
- The guest/hospitality nouns and verbs share Guest_and_host and Hospitality. ξενίζω is put in Guest_and_host (Host, Guest, Host_location) because its regular Homeric complement ἐν μεγάροισι (Il. 6.217, Od. 7.190, 19.217) fills Host_location. Have_visitor_over has no location FE. Treating the verb as an LU of a relation frame follows befriend.v in Personal_relationship.
- Escort words: Cotheme (escort.v, guide.v) for the person who escorts (πομπός, πομπεύς, πομπεύω); Bringing for 'conveyor/carrier'. πομπή has Sending as primary, because the dominant Odyssean sense is the host *sending* a guest home, carried by others (the Phaeacian crew). Sending's definition, with a Sender who does not accompany the Theme, fits this exactly.
- Service words: Subordinates_and_superiors (serve.v, servant.n, assistant.n) for attendants, People_by_vocation (attendant.n, bartender.n, waiter.n) for the wine-pourer as an occupation.

## Proposed frames and why
1. **Guest_friendship** (inherits Personal_relationship; uses Guest_and_host, Giving). Homeric ξενίη/ξεινοσύνη is a lasting, symmetric, often hereditary bond between households of different communities, founded and recalled by an exchange of guest-gifts. No FN 1.7 frame covers it:
   - Guest_and_host is a temporary, asymmetric relation that lasts one visit.
   - Personal_relationship and Social_connection carry no notion of reciprocal hospitality obligations, gift tokens or inheritance.
   
   It is primary for ξενοσύνη (its only attestation, Od. 21.35, names exactly this bond) and an alternative for ξένος, ξενία and ξεινήιον. All three examples are verified in the treebank (Il. 6.215; Od. 21.34-35; Il. 6.218). The FE labels on them are mine.
2. **Tending** (inherits Intentionally_act; uses Assistance). FN 1.7 has no LU for tend, look after, take care of or care for. care.v exists only in Desiring and tend.v only in Likelihood. The near frames are each too narrow:
   - Assistance profiles a Goal of a Benefited_party.
   - Subordinates_and_superiors profiles a command relation.
   - Growing_food is limited to crops.
   
   Homeric ἀμφιπολεύω takes as objects βίον 'livelihood' (Od. 18.254 = 19.127) and ὄρχατον 'orchard' (Od. 24.244, 24.257), which none of these covers. The examples are verified in the treebank (Od. 18.254; Od. 24.257).

I proposed no frame for πομπή (Sending and Cotheme cover it, with the hospitality obligation lost), for ξεινήιον (Giving with gift.n), for ταμίας (Being_in_control with manage.v, plus People_by_vocation) or for δαιτυμών (Social_event, Attendee).

## Passage annotation
- Only existing FN 1.7 frames are used: 7 annotation sets for Od. 1.123-124 and 26 for Od. 7.189-196. Unannotated words and debatable decisions are listed in `provenance.caveats`. The main ones:
  - χαῖρε and θεοῖσιν have no frame.
  - ῥέξομεν is treated as a support verb.
  - Non-local FEs are marked for the clause subject ὁ ξεῖνος.
- Offsets come from the token list in `passages.json` and are checked against `text[start:end+1]` by the validator.

## Uncertainties
- Guest_and_host and Hospitality fit the adjectives ξένιος and φιλόξενος only approximately. FN's Hospitality evaluates a host's attitude, whereas ξένιος is mostly relational ('of guests').
- φιλέω 'receive kindly as a guest' (Od. 1.123) has no FN LU. Guest_and_host was used, and Treating_and_mistreating is a possible alternative.
- γέροντες in Od. 7.189 are council elders. People_by_age captures only their age.
- The Phaeacian πομπή is both a sending and an escorted voyage. Annotating it only in Sending loses the escort and the hospitality obligation.
- Post-Homeric senses (procession, worship, medical treatment, 'surprise') rest on my own knowledge, because the input glosses are truncated.
- Text: Od. 1.123-124 follows the original experiment, and Od. 7.189-196 follows AGLDT 2.1. Both should be checked against a critical edition.
