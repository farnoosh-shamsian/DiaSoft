# Method notes: run B (LSJ + own knowledge + WordNet layer)

## Inputs used
- `lemmas.csv` (18 lemmas, LSJ glosses truncated at about 90 characters) and `cluster_128.txt`.
- `wordnet_layer.csv` / `WORDNET_LAYER.md`: only the `core` and `plausible` rows (168 of 2,168). The `noise` rows were not used. ὑποδεξίη ‘means of entertaining guests’, ὑποδρηστήρ ‘attendant’ and ταμίας ‘steward, dispenser’ have no AGWN synsets, so for them I relied on LSJ and Homeric usage alone.
- `passages.json` (Od. 1.123-124, 7.189-196) with its token offsets.
- FrameNet 1.7 through `check_frames.py` (`search`, `frame`) and NLTK lookups of LUs and FE definitions.
- The AGLDT Iliad and Odyssey treebanks in `homer_corpus/`, used only to check Homeric usage and to verify every Homeric citation in the CSV notes and in `proposed_frames.json`. Citations not checked there are not given, and constructed examples are marked `illustrative`. One point to watch: the treebank lemmatises ξεινήιον ‘guest-gift’ under ξένιος ‘of guests, hospitable’, and Il. 19.44 ταμίαι ‘stewards’ under ταμία ‘steward’.

## Choosing primary and alternative frames
1. I listed each lemma's senses from LSJ and my own knowledge of Greek, and checked them against the WordNet core and plausible synsets. Each WordNet synset was either assigned to a sense, which supports a frame, added as a new sense, which adds a frame, or rejected, with the reason noted.
2. The **primary** frame is the one for the lemma's dominant **Homeric** sense, because the cluster and the passages are Homeric. Usually this matches LSJ's first gloss and a WordNet `core` synset. Where the Homeric evidence pointed elsewhere, the Homeric evidence decided: see ξενοσύνη ‘guest-friendship’ below.
3. **Alternatives** cover the other real senses, including post-Homeric ones when LSJ or WordNet attests them. Those are flagged "post-Homeric" in the `note` column. In three places an alternative is an existing-frame fallback for a sense that has a proposed frame as primary, or the reverse: ξενία ‘hospitality, guest-friendship’ → Social_connection, ἀμφιπολεύω ‘tend, take care of’ → Agriculture, and ξενοσύνη ‘guest-friendship’ → Hospitality.
4. For each existing frame I mapped the Greek participants onto its core FEs and copied the core FE list from FrameNet 1.7. The validator confirms the lists.

## Where the WordNet layer changed or confirmed decisions
**WordNet senses that added a frame** (the alternative would not have been included from the truncated LSJ gloss alone):
- **ξένος** ‘guest, stranger; guest-friend’:
  - a#00984582 foreign-born/nonnative → Indigenous_origin
  - a#00983540 / a#00986373 foreign → Foreign_or_domestic_country
  - a#00918323, a#00918134, a#00918492 unacquainted/strange → Familiarity
  - a#01646674 mercenary → Member_of_military
- **ξενίζω** ‘receive as a guest, entertain’:
  - v#01813131 take_in → Provide_lodging
  - v#01506956 give.v.08 → Giving
  - v#00491471 / v#00491581 amaze/surprise → Experiencer_obj
- **ξενία** ‘hospitality, guest-friendship’:
  - n#00682362 lodging, n#00682063 stay → Temporary_stay
  - n#07273101 foreigner, n#00765977 lawsuit (γραφὴ ξενίας ‘indictment for usurping citizenship’) → Indigenous_origin
- **ξεινήιον** ‘guest-gift’: n#00684444 provision → Supply
- **φιλόξενος** ‘hospitable, kind to strangers’: a#01147260 / a#00221441 kind/charitable → Social_interaction_evaluation
- **πομπή** ‘escort, conveyance home’:
  - n#07247289 / n#06097890 escort/bodyguard (a group) → Entourage
  - n#06234223 parade, procession.n.02 → Mass_motion
  - n#00471060 mission → Being_obligated
- **πομπός** ‘escort, guide’:
  - n#07141701 carrier, n#07182314 conveyer → Bringing
  - n#07117864 bodyguard, n#07304133 guard → Protecting
- **πομπεύς** ‘escort, conductor’: n#06233236 procession → Participation
- **πομπεύω** ‘escort, conduct’:
  - v#01313330 parade, v#01307876 strut → Self_motion
  - v#00994853 / v#00981851 transport/bear → Bringing
  - v#00572942 abuse → Judgment_direct_address
- **θεραπεύω** ‘serve, attend; take care of’:
  - v#01214483 worship → Rite
  - v#00056004 / v#00054862 cure/treat → Cure
  - v#01732330 serve.v.10 → Assistance
  - v#01738960 care.v.02 → Tending
- **ἀμφιπολεύω** ‘tend, take care of’:
  - v#01732330 serve.v.10 → Assistance
  - v#00741327 / v#00741990 serve.v.02 / officiate → Serving_in_capacity

**WordNet senses that decided or confirmed a primary:**
- ξενίζω ‘receive as a guest, entertain’: v#01624648 invite.v.05 'have as a guest', v#01008263 receive.v.05 and v#01008154 welcome.v.03 led me to choose Have_visitor_over over Provide_lodging as primary. Provide_lodging, from take_in, became an alternative.
- θεραπεύω ‘serve, attend; take care of’: v#01768189 serve.v.07 'be in the service of' supports Subordinates_and_superiors, which also matches the only Homeric token (Od. 13.265).
- Other confirmations:
  - ξένιος ‘of guests, hospitable’: a#01192687 hospitable → Hospitality
  - ξενία ‘hospitality, guest-friendship’: n#04975139 hospitality → Hospitality
  - ξεινήιον ‘guest-gift’: n#09545388 gift → Giving
  - δαιτυμών ‘guest at a feast’: n#07304800 guest → Guest_and_host
  - πομπή ‘escort, conveyance home’: n#00077232 sending → Sending
  - πομπός ‘escort, guide’ and πομπεύς ‘escort, conductor’: guide.n.02, escort.n.03, usher.n.03 → Cotheme
  - πομπεύω ‘escort, conduct’: escort.v.01, see.v.22, lead.v.01 → Cotheme
  - οἰνοχόος ‘wine-pourer’: n#07196494 cupbearer → People_by_vocation

**WordNet senses that led to a proposed frame:** the core synsets care.v.02, tend.v.02, tend.v.03 and minister.v.01 for ἀμφιπολεύω ‘tend, take care of’, and care.v.02 for θεραπεύω ‘serve, attend; take care of’, have no FrameNet counterpart. FrameNet's care.v is only in Desiring, tend.v only in Likelihood, and look after, take care of and look after (keep.v.07) have no LU. This gap is the reason for **Tending**.

**WordNet senses I kept but demoted, or rejected:**
- ξενοσύνη ‘guest-friendship’: n#04975139 hospitality is kept, but as an alternative. The only Homeric token, Od. 21.35 (ἀρχὴν ξεινοσύνης προσκηδέος ‘the beginning of a close guest-friendship’), denotes the bond that Odysseus and Iphitus began by exchanging gifts. They "never knew each other at table", so the primary is Guest_friendship.
- ξένιος ‘of guests, hospitable’: a#00984080 / a#00983540 alien/foreign rejected, as a later sense not attested in Homer.
- ξενία ‘hospitality, guest-friendship’: guest.n.01 / guest.n.03 not treated as a sense of the abstract noun. They come from phrases like ἐπὶ ξενίᾳ 'as a guest' and are folded into Temporary_stay. The gift synsets (n#09545388, n#00703535) are rejected for ξενία, because the guest-gifts are τὰ ξένια ‘gifts for a guest’ of ξένιος ‘of guests, hospitable’.
- ξενίζω ‘receive as a guest, entertain’: entertain.v.01 not mapped to FrameNet entertain.v (Cause_to_experience = amusement). hold.v.03 and receive.v.10 (hold a reception) considered for Social_event but not added, because the verb does not denote the event.
- δαιτυμών ‘guest at a feast’: helping/portion (n#05631178) is used only as evidence for the 'contributes his portion' sense (Giving), not as a referent.
- πομπή ‘escort, conveyance home’: pomp.n.02 rejected. πομπός ‘escort, guide’: emissary and messenger rejected, as not supported by LSJ or Homer. πομπεύς ‘escort, conductor’: guard rejected.
- θεραπεύω ‘serve, attend; take care of’: flatter, woo/court, honour, restore/repair and foster/rear noted but not mapped. 'Pay court to' is a real LSJ sense, but no FrameNet frame fits it without distortion (Forming_relationships woo.v is romantic).
- φιλόξενος ‘hospitable, kind to strangers’: WordNet has no 'hospitable' synset, so the primary (Hospitality) comes from LSJ and from Od. 6.121 and 9.176. The WordNet kindness senses are compatible, since Hospitality inherits from Social_interaction_evaluation.

## Why each proposed frame was needed
- **Guest_friendship** (ξένος 'guest-friend', ξενοσύνη ‘guest-friendship’, ξενία 'friendly relation', ξένιος 'of guest-friendship'). Guest_and_host is explicitly a *temporary* relationship with fixed roles. Personal_relationship and Social_connection are generic, with no hospitality, gift exchange, inheritance or divine guarantor. Xenia is a lasting, reciprocal, inheritable bond between members of different communities, created and attested by gifts (Il. 6.215, Od. 1.187, Od. 21.34-35, all verified). The frame inherits Personal_relationship and uses Guest_and_host and Exchange. ξεινήιον ‘guest-gift’ fills its Token FE rather than being an LU.
- **Tending** (ἀμφιπολεύω ‘tend, take care of’, and θεραπεύω 'take care of'). FrameNet 1.7 has no frame for continuous care and upkeep of a person, animal, plant, land or livelihood. Assistance needs a Goal of a Benefited_party, Agriculture is about growing Food, and Cure is about healing an Affliction. The Homeric uses of ἀμφιπολεύω (tending an orchard, Od. 24.244 and 24.257; looking after a livelihood, Od. 18.254) fall between these, so Tending is its primary.
- I did not propose a frame for πομπή ‘escort, conveyance home’ as the host's duty of conveying a guest home. Sending (host = Sender, guest = Theme, homeland = Goal, ship = Transport_means) captures the event, and Guest_and_host captures the social setting.
- I did not propose a frame for the steward (ταμίας ‘steward, dispenser’) or the cupbearer (οἰνοχόος ‘wine-pourer’). Supply, Being_in_control and People_by_vocation are adequate.

## Passage annotation
- I used only existing FrameNet 1.7 frames. There are 7 annotation sets for Od. 1.123-124 and 30 for Od. 7.189-196. Every span was located programmatically and checked against the token offsets and the validator.
- χαῖρε ‘hail! welcome!’ (a greeting) and θεοῖσιν ‘to the gods’ are left unannotated: FrameNet has no Greeting frame and no deity frame. Particles, the article, pronouns and the copula are not targets. Each such decision is listed in `caveats`.
- The hospitality verbs in the passages are annotated consistently with the lemma table: ξεινίσσομεν ‘we will entertain (as a guest)’, and φιλήσεαι ‘you will be made welcome’ in its hospitality sense, are in Have_visitor_over. Both πομπή ‘escort, conveyance home’ tokens are in Sending, and the ξεῖνος ‘guest, stranger; guest-friend’ tokens are in Guest_and_host.

## Uncertainties
- **ξενοσύνη** ‘guest-friendship’: making Guest_friendship primary rests on a single Homeric token. LSJ and WordNet both say 'hospitality'.
- **ὑποδεξίη** ‘means of entertaining guests’: one token (Il. 9.73) with no WordNet data. Hospitality (primary), Have_visitor_over and Supply are all defensible readings of 'means of entertainment'.
- **δαιτυμών** ‘guest at a feast’: Guest_and_host (primary, after the WordNet core synset and LSJ's first gloss) versus Social_event Attendee ('banqueter') is close. Homeric contexts stress participation in the feast as much as guest status.
- **πομπή ‘escort, conveyance home’, πομπός ‘escort, guide’, πομπεύς** ‘escort, conductor’: the line between Sending (conveyance by others), Bringing (carrying), Cotheme (accompanying) and Entourage (a group) is fluid in Homer. The Phaeacians both send and carry Odysseus.
- **ταμίας** ‘steward, dispenser’: the LSJ gloss given ('ship's officer in charge of provisions') reflects Il. 19.44, but 3 of 4 Homeric tokens are figurative: Zeus ταμίης πολέμοιο ‘dispenser of war’, Aeolus ταμίης ἀνέμων ‘steward of the winds’. Supply was preferred to Being_in_control as primary.
- **Fit of the FrameNet frames**:
  - Rite has no FE for the god to whom a rite is addressed (θεραπεύω 'worship'; θεοῖσιν ... ἱερά ‘to the gods ... sacrifices’ in passage 2).
  - Member_of_military assumes a state army, which fits mercenaries only loosely.
  - Hospitality is framed as an evaluation of a host's attitude, which fits ξενία 'entertainment' only approximately.
- Post-Homeric senses are included as alternatives on the strength of LSJ and WordNet, but they were not checked against any post-Homeric corpus.
