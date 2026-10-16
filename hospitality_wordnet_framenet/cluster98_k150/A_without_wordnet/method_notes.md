# Method notes: cluster 98, run A (no WordNet)

## Inputs
- `lemmas.csv` (50 lemmas, LSJ glosses cut at about 90 characters), `cluster.txt`, `passages.json`, `FORMAT_SPEC.md`, `check_frames.py` (NLTK FrameNet 1.7).
- **Sense sources:** the LSJ glosses plus my own knowledge of Ancient Greek. No WordNet of any kind (Ancient Greek WordNet, Princeton WordNet, NLTK `wordnet`) was used.
- **Homeric usage:** checked in the AGLDT treebanks (`homer_corpus/iliad_treebank.xml`, `odyssey_treebank.xml`), matching works by the full CTS prefix (`tlg0012.tlg001` = Iliad, `tlg0012.tlg002` = Odyssey).
  - Every Homeric citation in the notes and every example marked "verified" in `proposed_frames.json` was looked up there.
  - The work scripts (`kwic.py`, `lines.py`, `rows.py`, `build.py`) are in `c98_runA/work`.

## Choosing primary and alternative frames
- **Primary frame:** the frame for the lemma's dominant *Homeric* sense, judged from the treebank tokens where the lemma is attested. For lemmas that do not occur in Homer, the primary is the first LSJ sense.
- **Alternatives:** the other real senses, including post-Homeric ones, which are marked "post-Homeric" in `note`.
- **Same frame, two senses:** one lemma can have two rows with the same frame when the senses differ in role. For example, ξένος as Guest and as Host are both in Guest_and_host.
- **Choices that depart from the cluster label:**
  - **προσδέχομαι → Waiting:** all 15 Homeric tokens are ποτιδέγμενος 'waiting for'. The 'receive favourably' sense the cluster suggests is post-Homeric and is listed as an alternative.
  - **ἐπίηρα → Assistance:** the Homeric phrase is ἐπίηρα φέρειν 'do a favour' (Il. 1.572, 1.578). Giving is the alternative.
  - **δωρητός → Suasion:** Il. 9.526 means 'open to (persuasion by) gifts'.
  - **ἀμοιβός → Take_place_of:** its only Homeric token, Il. 13.793, refers to relief troops.
  - **ταμίας → People_by_vocation:** the steward who issues stores. Being_in_control is the alternative, for Zeus as ταμίης of war (Il. 4.84) and Aeolus of the winds (Od. 10.21).
  - **ὑποδεξίη → Receive_visitor_scenario:** the definition fits 'reception, means of entertaining' exactly, but the frame has no LUs in FN 1.7.
  - **ξενίζω → Provide_lodging:** the frame contains host.v, and Homeric hosting lasts for days (Il. 6.174, 6.217).
  - **ὑποδέχομαι → Have_visitor_over.**

## Proposed frames (3)
1. **Guest_friendship.** Guest_and_host is explicitly a *temporary* relationship in which the guest does not reciprocate. Personal_relationship and Social_connection carry no hospitality, gift-exchange or hereditary component. Homeric ξενοσύνη/ξενίη/ξεῖνος πατρώϊος name a lasting, symmetrical, inheritable bond sealed by exchanging gifts (Il. 6.215-218; Od. 21.34-35; Od. 24.314).
   - Primary for: ξενοσύνη.
   - Alternative for: ξένος, ξενία, ξεινήιον.
2. **Honorific_prerogative.** FN 1.7 has no frame or LU for privilege or prerogative. Rewards_and_punishments presupposes a judgment of an action, and Giving lacks the status-marking component. γέρας is a status share whose loss is dishonour (Il. 1.118-123); it can also be a choice cut of meat for a guest (Od. 14.437) or the burial due to the dead (Il. 16.457).
   - Primary for: γέρας, πρεσβεῖον, ἀγέραστος, γεραίρω.
3. **Plaything.** FrameNet 1.7 has no frame or LU for toy or plaything. Artifact is too general, and Accoutrements covers only wearable accessories, though it has trinket.n.
   - Primary for: ἄθυρμα (Il. 15.363, a child's sand toys).
   - Alternative for: γλῆνος.
   - The 'trinket' senses (Od. 15.416, 18.323; γλῆνος Il. 24.192) are mapped to Accoutrements.

## Passages
- Only existing FN 1.7 frames are used: 8 annotation sets in Od. 1.123-124 and 7 in Od. 8.544-545.
- `caveats` lists every word left unannotated (χαῖρε, εἵνεκα, φίλα, particles), every non-obvious frame choice, and the policy of null-instantiating only one member per CoreSet.
- Offsets were computed by script and checked against the token offsets in `passages.json`.
- The Purpose FE in 8.544 is discontinuous because of hyperbaton, so it is given as two spans with the same FE name.

## Uncertainties
- **φιλήσεαι (Od. 1.123):** Have_visitor_over versus Treating_and_mistreating.
- **δείπνου:** Food versus Social_event.
- **αἰδοίοιο → Judgment:** an evaluee-oriented adjective in a mostly cognizer-oriented frame.
- **τέτυκται:** possibly near-copular rather than 'made'.
- **ἐπίμαστος (Od. 20.377):** the sense is disputed ('sought out, picked up' vs. 'begging, searching for food').
- **ἀφήκω:** has no genuine Homeric token. The AGLDT form at Il. 8.133 (ἀφῆκ') is the aorist of ἀφίημι, so it is a lemmatization error.
- **ξεινήιον:** the treebank lemmatizes these forms under ξένιος. The counts in `lemmas.csv` evidently come from a different lemmatization.
- **ἐπιδίδωμι (mid.) 'take as witnesses' (Il. 22.254)** is mapped to Commitment. FN has no witness-invocation frame, so the gods fill no FE.
- **Unmapped minor LSJ senses:**
  - δόσις 'ramming'
  - γλῆνος 'stars'
  - προίξ 'with impunity'
  - δωτίνη 'rent in kind'
  - ἀναδέχομαι 'acknowledge'
