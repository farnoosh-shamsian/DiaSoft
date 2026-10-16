# Protocol: WordNet Check and FrameNet Annotation of ξενία / προξενία

Oct 6, 2026 · @Monica Berti

## Summary

ξενία and προξενία are absent from Princeton WordNet but present in Ancient Greek WordNet (AGWN), with 78 and 37 synset links. Most links are noise: only 17 and 16 senses respectively were judged core or plausible. The chat then produced a FrameNet annotation of Odyssey 1.123 using five existing FrameNet 1.7 frames, exported as HTML, XML and JSON.

## Protocol

The chat ran in four stages. User prompts are quoted as they appear in the transcript.

### Stage 1: Check WordNet coverage

Prompt: "Do you know if the ancient Greek words ξενία and προξενία are present in WordNet?"

1. Search Princeton WordNet (through NLTK) for the Greek forms and the transliterations xenia, proxenia and proxeny.
2. Download the AGWN database dump (Center for Hellenic Studies, University of Exeter, University of Pavia).
3. Match exact lemma fields, not substrings, because ξενία is contained in προξενία.
4. Count synsets per lemma and synsets shared by both.

### Stage 2: Separate real senses from noise

Prompt: "Yes, please" (in reply to the offer to list synset IDs and English glosses and mark plausible senses against noise).

1. Export every synset ID linked to each lemma with its English words, gloss and hypernym.
2. Flag each synset core, plausible or noise by reading the gloss against the Greek sense. These flags are Claude's judgment; AGWN gives every link equal weight.
3. Keep synsets with no English gloss (AGWN-internal or Latin-mapped IDs) as rows with empty gloss fields.
4. Diagnose the noise: find the English gloss word that pulled each wrong synset in.
5. Save all rows, sorted core → plausible → noise, as a CSV.

### Stage 3: Annotate Odyssey 1.123 in FrameNet format

The prompt for this stage is not in the pasted transcript.

1. Mark each frame-evoking word (target) in the passage.
2. Assign an existing FrameNet 1.7 frame to each target; propose no new frame if an existing one fits.
3. Mark frame elements with their Greek filler and 0-based, end-inclusive character offsets.
4. Mark unexpressed frame elements as null instantiations (CNI or DNI), for example pro-dropped subjects.
5. Render as HTML (one card per frame) and as XML in FrameNet's fullTextAnnotation schema, with shared offsets.

### Stage 4: Export as JSON

Prompt: "and a JSON"

1. Write the same annotation as JSON: provenance metadata, then sentences with text, translation and one annotation set per target.
2. Run an integrity check that every span's stored text matches the slice at its offsets.

## Results

### WordNet coverage

| Resource | ξενία | προξενία |
| --- | --- | --- |
| Princeton WordNet | Absent (nearest: hospitality → `cordial_reception.n.01`) | Absent |
| AGWN, synsets linked | 78 | 37 |
| Core | 4 | 5 |
| Plausible | 13 | 11 |
| Noise | 61 | 21 |

The two lemmas share 9 synsets.

### Core senses kept

| Lemma | Synset | Sense |
| --- | --- | --- |
| ξενία | `n#04975139` | hospitality, cordial reception |
| ξενία | `n#07304800` | guest, invitee |
| ξενία | `n#N0002261` | guest, visitor |
| ξενία, προξενία | `n#10038317` | friendship |
| προξενία | `n#05074858` | treaty, pact, accord |
| προξενία | `n#05073898` | covenant, compact |
| προξενία | `n#03707935` | accord, rapport |
| προξενία | `n#06945104` | defender, guardian, protector |

Notable plausible senses: for ξενία, guest-gifts (`n#00703535`, `n#09545388`, `n#04355268`), lodging and stay (`n#00682362`, `n#00682063`, `n#02839091`), foreigner (`n#07273101`, `n#07614356`); for προξενία, foreigner (`n#07273101`, `n#07273655`), state and nation (`n#06074189`, `n#06299747`), legal instrument (`n#00112599`, `n#04864856`).

### Why the noise appears

AGWN was bootstrapped by aligning Greek–English dictionary glosses (LSJ, Middle Liddell, Autenrieth) with Princeton synsets, so every sense of a polysemous English gloss word was attached. Examples: "right" brought right-hand and right-wing; "gold" brought the metal and the colour; "stay" brought a corset stiffener; "state" brought state of matter; "compact" brought compact car. Two links were abbreviation collisions (AN nursing degree, As arsenic).

### Odyssey 1.123 annotation

Five FrameNet 1.7 frames: Guest\_and\_host, Provide\_lodging, Ingestion, Telling, Needing. φιλέω was assigned to Provide\_lodging, so no new frame was proposed. χαῖρε was left unannotated because FrameNet 1.7 has no Greeting frame.

## Outputs

| File | Format | Content |
| --- | --- | --- |
| `xenia_proxenia_synsets_annotated.csv` | CSV | 115 rows: every AGWN synset for both lemmas with English words, gloss, hypernym and core / plausible / noise flag |
| Odyssey 1.123 FrameNet (HTML) | HTML | Passage with colour-coded targets; one card per frame with lexical unit, frame link to Berkeley FrameNet, and frame-element table |
| Odyssey 1.123 FrameNet (XML) | XML | FrameNet fullTextAnnotation schema: one annotationSet per target with Target and FE layers, character offsets, itype CNI/DNI |
| `odyssey_1_123_framenet.json` | JSON | Same annotation: provenance, sentences, annotationSets with luName, frameName, target span and FE list |

All three annotation files share identical offsets: 0-based, end inclusive.

The project file `greek_hospitality_wordnet_annotated.csv` extends the 115-row CSV to 9 lemmas (365 rows) with extra columns `flag_method` and `lemma_note`. That extension happened outside the pasted transcript.

## Caveats and next steps

The flags and the annotation are drafts for team review, not validated data.

- **Flags are model judgment.** Core / plausible / noise was decided by Claude reading each gloss; a team member should confirm at least the core and plausible rows.
- **AGWN links are unreviewed.** Its maintainers describe the lemma–synset mapping as automatic and prone to false positives.
- **Check the Greek text.** Verify the Odyssey 1.123 orthography against an OCT or Teubner edition before reusing the offsets.
- **Annotation is illustrative.** The frame choices for one line are a proposal, not a gold standard.
- **Transcript gap.** The prompt that started the Odyssey annotation is not in the pasted chat.

Next steps offered in the chat and not yet done:

- [ ] Cross-check flagged synsets against the live CHS API (`greekwordnet.chs.harvard.edu/api/lemmas/<lemma>/<pos>/<morpho>`) to see if any were manually validated since the dump.
- [ ] Pull the Latin-side (Minozzi Latin WordNet) alignments for the core senses.
- [ ] Compare coverage in Open Ancient Greek WordNet 0.5 (CNR-ILC, about 22,420 lemmas), a separate distribution.

### Starting your own chat

1. Open a new chat in Claude.
2. Attach `greek_hospitality_wordnet_annotated.csv` (sent with this doc). Attach the Odyssey 1.123 JSON too if you have it; it is optional.
3. Paste the prompt below, replacing the task line with what you want to do.
4. Log what you did and link your chat, so the next person can pick up from there.

```markdown
I am continuing an Ancient Greek FrameNet project on hospitality vocabulary.
The attached CSV links 9 Greek lemmas (ξένος, ξενία, πρόξενος,
προξενία, ἀσυλία, φιλία, ἱκετεία, ἰδιόξενος, φιλότης) to
Ancient Greek WordNet synsets. Columns: translit, greek_lemma, pos,
sense_flag (core / plausible / noise), flag_method (manual / heuristic),
synset_id, english_words, gloss, pwn_hypernym_id, pwn_hypernym_words,
lemma_note.

Method used so far:
- WordNet: Ancient Greek WordNet (Center for Hellenic Studies / Exeter /
  Pavia) database dump, exact lemma match. Princeton WordNet has none of
  these lemmas.
- Flags: each synset judged core, plausible or noise by reading its gloss
  against the Greek sense. AGWN links are auto-generated and noisy.
  Treat "heuristic" flags as unreviewed.
- FrameNet: annotate passages with existing FrameNet 1.7 frames; mark frame
  elements with 0-based, end-inclusive character offsets; use CNI/DNI for
  null instantiation; export as HTML, XML (fullTextAnnotation schema) and
  JSON with shared offsets.

Task: [e.g. review the heuristic flags for ἀσυλία / annotate a new
passage / add a new lemma]

Keep the same CSV columns and annotation conventions, mark anything you
are unsure of, and do not invent Homeric citations.
```
