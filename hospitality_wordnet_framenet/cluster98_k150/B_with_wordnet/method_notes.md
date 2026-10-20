# Method notes: cluster 98 (k150), run B (with the WordNet layer)

## Inputs used
- `lemmas.csv` (50 lemmas, LSJ glosses) and `cluster.txt`; `passages.json`; `FORMAT_SPEC.md`.
- `wordnet_layer.csv`, filtered to the 626 `core` and `plausible` rows. The 13,840 `noise` rows were not used. ὑποδεξίη ‘means of entertaining guests’, ὑποδέχομαι ‘receive (as a guest)’, ἀγέραστος ‘without a gift of honour’, ταμίας ‘steward, dispenser’ and ὑποδρηστήρ ‘attendant’ have no WordNet rows, so they were decided from LSJ and the treebank alone.
- `check_frames.py` (NLTK FrameNet 1.7) for frame lookup (`search`, `frame`) and validation.
- The AGLDT treebanks `homer_corpus/iliad_treebank.xml` and `odyssey_treebank.xml` (identified by `tlg0012.tlg001` / `tlg0012.tlg002`). I used them to see how each lemma is actually used in Homer and to verify every citation and every example marked "verified". Citations in `note` give book.line; anything not checked in the treebank is labelled as such or left uncited.
- Nothing else was read; no web search.

## How frames were chosen
1. For each lemma I listed its senses from LSJ, from my own knowledge, and from the core and plausible WordNet synsets. Each WordNet synset was read as a candidate sense, and its English lemmas were run through `check_frames.py search` to find FrameNet LUs.
2. **Primary frame** = the frame of the lemma's main Homeric sense, judged from the treebank tokens. Where the Homeric material is thin or absent, I followed the LSJ head sense together with the WordNet core synsets. **Alternatives** = other real senses: Homeric, post-Homeric (labelled), or WordNet-attested. A WordNet sense was added as an alternative only if it is a genuine sense of the Greek word. Plausible rows that only restate the parent of an existing frame were not added (e.g. kind.a.01 for φιλόξενος ‘hospitable, kind to strangers’ is covered by Hospitality, which inherits from Social_interaction_evaluation).
3. A frame was proposed only where no FN 1.7 frame covers the concept and the concept is central to the cluster: three proposals in all.
4. The core FEs and definitions in `frame_assignments.csv` are generated from NLTK FrameNet 1.7. Definitions are cut at about 200 characters, and FrameNet's example sentences are dropped.

## Decisions changed or supported by the WordNet layer (synset IDs = PWN 3.0)
- **προσδέχομαι** ‘wait for; receive, accept’: the primary changed from LSJ's 'receive' to **Waiting**. This rests on wait.v.01 and expect.v.03 (core), whose reason column cites Homeric ποτιδέγμενος ‘waiting for’. The treebank confirms it: all 15 Homeric tokens are ποτιδέγμενος 'waiting for'.
- **ἀναδέχομαι** ‘take up; endure’: primary **Tolerating**, based on digest.v.03 'endure' (core) and confirmed by Od. 17.563. Commitment was added on undertake.v.05 and guarantee.v.01.
- **ἀμοιβός** ‘relief; one who exchanges’: primary **Take_place_of**, based on substitution.n.02 ('soldiers that relieve others'), which fits Il. 13.793 ἦλθον ἀμοιβοί ‘they had come as relief troops’.
- **ἐπίηρα** ‘acceptable gifts, favours’: primary **Assistance**, based on service.n.02 'act of help' (core). Stimulus_focus is an alternative (pleasant.a.01, grateful.s.01).
- **δαιτυμών** ‘guest at a feast’: the primary is Guest_and_host rather than Social_event, because of guest.n.01 (core). Social_event was kept as an alternative on helping.n.01 'each brings his portion'.
- **ξενίζω** ‘receive as a guest, entertain’: Provide_lodging added (take_in.v.01), Giving added (give.v.08) and Experiencer_obj added (amaze.v.01, surprise.v.01; post-Homeric 'surprise').
- **ξεινήιον** ‘guest-gift’: Supply added (provision.n.02).
- **ξενία** ‘hospitality, guest-friendship’: Guest_friendship (friendship.n.01) and Temporary_stay (stay.n.01, lodging.n.03) added. guest.n.01 / guest.n.03 (core) **rejected** as person-senses, which an abstract noun cannot have; they come from the phrase 'as a guest'.
- **ξένιος** ‘of guests, hospitable’: alien.s.02 / foreign.a.02 (plausible) **rejected**: LSJ gives ξένιος no 'foreign' sense; the rows are borrowed from ξένος ‘guest, stranger; guest-friend’.
- **ξένος** ‘guest, stranger; guest-friend’: Indigenous_origin (foreign-born.s.01), Foreign_or_domestic_country (foreign.a.02, alien.s.02) and Familiarity (unacquainted.s.02) added. mercenary.s.02 was noted but not mapped.
- **δέχομαι** ‘receive, accept’: Waiting added (wait.v.01, expect.v.03, 'Homeric await') and Relative_time added (follow.v.06, matching Il. 19.290 κακὸν ἐκ κακοῦ δέχεται ‘evil follows upon evil’).
- **ἀποδέχομαι** ‘accept, receive’: Judgment (approve.v.02) and Grasp (understand.v.02, absorb.v.03) added.
- **δίδωμι** ‘give’: Deny_or_grant_permission (allow.v.03, accord.v.02, permit.v.01), Forming_relationships (betroth.v.01) and Exchange (give.v.29) added.
- **ἐπιδίδωμι** ‘give besides; (mid.) take as witnesses’: Cause_to_be_included (add.v.01) and Change_position_on_a_scale (increase.v.01, progress.v.01) added.
- **προσάγω** ‘bring to, bring upon’: Supply, Cause_to_be_included, Cotheme and Arriving all follow from core synsets (furnish.v.02, add.v.01, lead.v.01, come.v.01 / approach.v.01).
- **παρέχω** ‘provide, furnish’: Causation (yield.v.01) and Preventing_or_letting (permit.v.01) added.
- **δόσις** ‘gift, giving’: Deny_or_grant_permission (permission.n.01) added.
- **νέμω** ‘deal out, distribute’: Possession (have.v.01, bear.v.11) and Fire_burning (consume.v.04, devour.v.01) added. The core synsets distribute.v.01, share.v.04 and assign.v.02 found no FN frame, which supported proposing Apportioning.
- **γεραίρω** ‘honour (with a gift of honour)’: Judgment (respect.v.02) and Rewards_and_punishments (reward.v.03) added. **γέρας** ‘gift of honour, prize’: Rewards_and_punishments (reward.n.02, wages.n.01) added; prerogative.n.01 and privilege.n.01 (core) found no FN frame, which supported proposing Honorific_privilege. **δῶρον** ‘gift’: the Honorific_privilege alternative (award.n.02) and Measure_linear_extent (palm.n.02) added.
- **κτῆμα** ‘possession’: Locale_by_ownership (estate.n.02, farm.n.01). **κειμήλιον** ‘treasure, heirloom’: Store (treasure.n.01 'hoarded wealth'). **ἄθυρμα** ‘plaything, toy’: Stimulus_focus (joy.n.02).
- **πομπή** ‘escort, conveyance home’: Entourage (escort.n.03, bodyguard.n.02), Being_obligated (mission.n.03) and Mass_motion (parade.n.01). **πομπεύω** ‘escort, conduct’: Mass_motion (parade.v.02), Bringing (transport.v.02). **πομπός** ‘escort, guide’: Entourage (bodyguard.n.02), Bringing (carrier.n.01). **πομπεύς** ‘escort, conductor’: Mass_motion (procession.n.02).
- **θεραπεύω** ‘serve, attend; take care of’: Rite (worship.v.02), Cure (bring_around.v.02, treat.v.03) and Agriculture (cultivate.v.02). **ἀμφιπολεύω** ‘tend, take care of’: Agriculture (tend.v.02, matching Od. 24.244 ὄρχατον ἀμφιπολεύειν ‘to tend the orchard’) and Serving_in_capacity (serve.v.02).
- **δωρητός** ‘open to gifts’: Giving kept as an alternative on given.s.01 (core), while the primary is Suasion on the Homeric evidence (Il. 9.526) and open.s.04.
- **ἐπίμαστος** ‘sought out, brought in’: Seeking on sought.a.01 (core). **ἀφήκω** ‘arrive; depart’: Arriving / Departing on arrive.v.01 / depart.v.03.
- WordNet senses noted but left unmapped, for lack of a fitting FN frame: rent.n.01 (δωτίνη ‘gift’), impunity.n.01 (προίξ ‘gift’), dose.n.01 (δόσις ‘gift, giving’), introduce.v.08 (εἰσφέρω ‘carry in, bring in’), abuse.v.03 (πομπεύω ‘escort, conduct’), range.v.07 'let graze' (νέμω ‘deal out, distribute’), catch.v.04 (ἀναδέχομαι ‘take up; endure’), celebrate.v.02 (γεραίρω ‘honour (with a gift of honour)’).

## Proposed frames and why
- **Guest_friendship** (primary for ξενοσύνη ‘guest-friendship’; alternative for ξένος ‘guest, stranger; guest-friend’, ξενία ‘hospitality, guest-friendship’, ξεινήιον ‘guest-gift’, ξένιος ‘of guests, hospitable’, δωτίνη ‘gift’). Guest_and_host is explicitly a *temporary*, asymmetrical host–guest relation, and Personal_relationship / Social_connection lack the defining features: hereditary transmission (πατρώϊος ‘of the fathers, inherited’), symmetry, tokens exchanged, and a divine guarantor. Examples are verified at Il. 6.215, Od. 1.187, Od. 21.34-35 and Od. 9.270-271.
- **Honorific_privilege** (primary for γέρας ‘gift of honour, prize’, πρεσβεῖον ‘gift of honour; privilege of age’, γεραίρω ‘honour (with a gift of honour)’, ἀγέραστος ‘without a gift of honour’). FN 1.7 has no frame or LU for privilege, prerogative or prize of honour. Giving misses the status-recognition and the 'due share' aspects, and Rewards_and_punishments misses the status-based (non-merit) privileges, e.g. Il. 4.323 τὸ γὰρ γέρας ἐστὶ γερόντων ‘for that is the privilege of the old men’. Examples are verified at Od. 7.149-150, Il. 4.323, Il. 1.161-162, Il. 7.321 and Il. 1.118-119.
- **Apportioning** (primary for νέμω ‘deal out, distribute’; alternative for δοτήρ ‘giver, dispenser’, ταμίας ‘steward, dispenser’). FN 1.7 has no LU for allot, apportion, ration or dole out. Dispersal is spatial scattering, and Giving profiles a single transfer, not the division of one stock into shares for many recipients. Examples are verified at Od. 6.188-189, Od. 8.470 and Il. 19.44.

## Passages
Both passages were annotated with existing FN 1.7 frames only: 8 annotation sets each. Words with no fitting frame, and every judgment call, are listed in `provenance.caveats`. The main points:
- χαῖρε ‘hail! welcome!’: there is no Greeting frame.
- εἵνεκα ‘for the sake of’: there is no 'for the sake of' LU.
- φιλέω ‘love; welcome (a guest)’: read as hospitality (Have_visitor_over) in Od. 1.123 but as affect (Experiencer_focus) in Od. 8.545.
- τέτυκται ‘has been made ready’: Intentionally_create, possibly only a copula.
- πομπὴ ‘conveyance home’: Sending, with all FEs DNI.

## Uncertainties
- Several primaries rest on very few Homeric tokens (ἐπίηρα ‘acceptable gifts, favours’, δωρητός ‘open to gifts’, ἀμοιβός ‘relief; one who exchanges’, ἐπίμαστος ‘sought out, brought in’, ὑποδεξίη ‘means of entertaining guests’). For ἐπίμαστος the meaning itself is disputed ('picked up' vs 'begging').
- ἀφήκω ‘arrive; depart’ has no genuine Homeric attestation. Its only treebank token (Il. 8.133 ἀφῆκ' ‘he let fly’) is a mislemmatized form of ἀφίημι ‘let go, let fly’. Likewise, the treebank files some ξεινήιον ‘guest-gift’ forms under ξένιος ‘of guests, hospitable’ and δειδέχαται 'greet' under δέχομαι ‘receive, accept’.
- νέμω ‘deal out, distribute’: the commonest Homeric use is middle 'inhabit' (Residence). Apportioning was nevertheless made primary as the base active sense that puts the lemma in this cluster.
- ἀμφιπολεύω 'take care of': FN 1.7 has no caretaking frame, so Assistance is an approximation. A separate Tending frame could be considered.
- Many alternatives are post-Homeric senses attested in LSJ or WordNet. They are labelled as such in `note`.
