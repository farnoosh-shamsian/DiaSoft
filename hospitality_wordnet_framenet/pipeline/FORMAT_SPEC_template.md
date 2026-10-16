# Output specification: FrameNet layer for an Ancient Greek lexical field

The task is to map every lemma in `lemmas.csv` to the FrameNet frame(s) it evokes, and to annotate two Homeric passages in FrameNet full-text format. The format follows an earlier experiment on Ancient Greek hospitality vocabulary; example rows below come from that experiment and cover lemmas that are *not* in this list.

Write five files into your output folder.

## 1. `frame_assignments.csv`

Columns, in this order:

```
translit,greek_lemma,word_sense,assignment,frame,frame_status,frame_core_FEs,participant_to_FE_mapping,frame_definition,note
```

- One row per sense–frame pairing. Each lemma in `lemmas.csv` has exactly one row with `assignment` = `primary` and any number with `alternative`.
- `word_sense`: the sense this row covers, in a few words, e.g. `friend (person)`, `to receive (a guest)`.
- `frame_status`: `existing (FN1.7)` for a Berkeley FrameNet 1.7 frame, `PROPOSED NEW` for a frame you define.
- `frame_core_FEs`: comma-separated core frame elements. For an existing frame, exactly that frame's core FEs (`check_frames.py frame <Name>` lists them).
- `participant_to_FE_mapping`: how the Greek word and its participants fill the frame's FEs.
- `frame_definition`: the FrameNet definition, may be cut at about 200 characters; for a proposed frame, start with `PROPOSED.`
- `note`: short, optional.

Example rows from the earlier experiment:

```
proxenos,πρόξενος,represents a foreign state,alternative,Representative,existing (FN1.7),Representative,proxenos = Representative; foreign state = Represented,A Representative is authorized by a Represented to communicate on behalf of the Represented.,
Philia,φιλία,friendship-bond,primary,Social_connection,existing (FN1.7),"Individuals, Individual_1, Individual_2, Connection",philia = Connection; friends = Individual_1/2,A mutual social and personal relationship that keeps people involved in each other's lives comprises a Connection of Individual1 to Individual2 or between Individuals.,
Philia,φιλία,friendship (named relationship),alternative,Personal_relationship,existing (FN1.7),"Partner_1, Partner_2, Partners",= Partners / Relationship,The words in this frame have to do with people and the personal Relationships they are or can be a part of.,
philos,φίλος,friend (person),primary,Personal_relationship,existing (FN1.7),"Partner_1, Partner_2, Partners",philos = Partner_1/Partner_2,The words in this frame have to do with people and the personal Relationships they are or can be a part of.,"person, not bond"
```

## 2. `proposed_frames.json`

Propose a new frame only where no existing FrameNet 1.7 frame captures the concept. There may be none. A list of objects:

```json
[
  {
    "name": "Proxeny",
    "definition": "An individual, the Proxenos — a citizen of the Host_community — is publicly appointed by another state, the Represented_state, to host, protect and advance the interests of that state's citizens within the Proxenos's own community, typically in return for Honours.",
    "inherits": ["Representative"],
    "uses": ["Guest_and_host"],
    "core_FEs": [{"name": "Proxenos", "definition": "The individual who holds the office and discharges its duties."}],
    "noncore_FEs": [{"name": "Honour", "definition": "The privileges granted to the Proxenos by the Represented_state."}],
    "lexical_units": [{"lemma": "πρόξενος", "pos": "N", "gloss": "the office-holder"}],
    "examples": [{"text": "As πρόξενος of [Sparta|Represented_state], [he|Proxenos] received every Spartan who came to his city.", "note": "illustrative"}]
  }
]
```

(This example is abridged.) In `examples`, mark each frame element as `[words|FE_name]`. An example is `illustrative` unless it quotes a Homeric line you have verified in the treebank; never invent a citation.

## 3. `lemma_senses.csv`

Columns `greek_lemma,sense`. One row per lemma: a short dictionary-style sense summary, e.g. `friend; (adj.) dear, beloved`.

## 4. `passage_annotations.json`

Annotate both passages in `passages.json`. Use each passage's `text` exactly as given; the `tokens` list gives every word's lemma, morphological tag and character offsets. Schema:

```json
{
  "corpus": "{corpus}",
  "document": "Homer, Odyssey",
  "provenance": {
    "text": "public-domain ({sources})",
    "translation": "author's",
    "annotation": "illustrative proposal, using existing Berkeley FrameNet 1.7 frames only",
    "offsets": "0-based character positions, end inclusive",
    "caveats": ["..."]
  },
  "sentences": [
    {
      "id": 1,
      "source": "Homer, Odyssey 1.123-124",
      "text": "<passage text>",
      "translation": "<your English translation>",
      "annotationSets": [
        {
          "id": 1,
          "luName": "<Greek lemma>.<n|v|a|adv|prep>",
          "frameName": "<FrameNet 1.7 frame>",
          "frameStatus": "existing",
          "target": {"name": "Target", "start": 0, "end": 4, "text": "<target word>"},
          "FEs": [
            {"name": "<FE>", "start": 0, "end": 4, "text": "<span>"},
            {"name": "<FE>", "itype": "CNI"}
          ]
        }
      ]
    }
  ]
}
```

- Mark every frame-evoking word (target) for which an existing FrameNet 1.7 frame fits; use existing frames only in the passages.
- Leave a word unannotated if no existing frame fits, and say so in `caveats` (e.g. "χαῖρε left unannotated: FrameNet 1.7 has no Greeting frame").
- Mark FEs with their Greek span and offsets: 0-based, end inclusive, so `text[start:end+1]` equals the span.
- Mark unexpressed core FEs as null instantiations with `itype`: CNI (constructional, e.g. a pro-dropped subject), DNI (definite, recoverable from context), INI (indefinite).
- Number annotation sets from 1 within each sentence.

## 5. `method_notes.md`

Brief: the inputs you used, how you chose primary vs. alternative frames, why each proposed frame was needed, and anything uncertain.

## Checking

Run until both report 0 problems:

```
py check_frames.py csv <output>/frame_assignments.csv
py check_frames.py json <output>/passage_annotations.json
```

`py check_frames.py frame <Name>` shows a frame's definition, FEs, relations and LUs; `py check_frames.py search <english word>` lists frames whose lexical units match. Set `PYTHONIOENCODING=utf-8` when printing Greek.
