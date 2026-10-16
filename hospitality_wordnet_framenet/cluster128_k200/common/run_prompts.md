# Prompts for runs A and B

The exact prompts that started the two FrameNet runs on October 16, 2026 (run A at 07:29:37 UTC, run B at 07:29:48 UTC), copied from the session transcript. Each run was a separate Claude Code subagent (type `general-purpose`) running Claude Opus 5.5 (`claude-opus-5-5`) with default settings. Claude Code does not expose temperature or a random seed, so a rerun will not give identical output.

The prompts name temporary working folders. Their contents are archived in this repository:

| Path in the prompt | Archived copy |
| --- | --- |
| `runA/input/`, `runB/input/`: `lemmas.csv`, `passages.json`, `FORMAT_SPEC.md`, `check_frames.py` | `common/` (same files, byte for byte) |
| `cluster_128.txt` | `common/cluster.txt` |
| `runB/input/wordnet_layer.csv` | `AGWN_PWN/cluster128_field_wordnet_full.csv` |
| `runB/input/WORDNET_LAYER.md` | `AGWN_PWN/WORDNET_LAYER.md` |
| `runA/output/`, `runB/output/` | rendered into `A_without_wordnet/` and `B_with_wordnet/` |

The isolation rules name the project folders as they were called at the time: `cluster128_wordnet_framenet` is now `hospitality_wordnet_framenet/cluster128_k200`. The rules were instructions to the agents; their file access was not technically restricted.

## Run A: without WordNet

```text
You are carrying out one run of a lexical-semantics experiment on Ancient Greek (Homeric) vocabulary: mapping a group of related lemmas to Berkeley FrameNet 1.7 frames and annotating two Homeric passages in FrameNet full-text format.

INPUT FOLDER (read only these files):
C:/Users/Farnoosh/AppData/Local/Temp/claude/C--Users-Farnoosh-Documents-GitHub-DiaSoft/992c7d43-414e-4ac5-b7cb-321890c4615b/scratchpad/runA/input
- lemmas.csv: the 18 lemmas (a semantic cluster from gloss embeddings: guest/hospitality, escort, attendant/service), with POS, group, Homeric frequency and LSJ glosses (glosses are truncated at ~90 characters)
- cluster_128.txt: the cluster as produced by the clustering
- passages.json: Odyssey 1.123-124 and Odyssey 7.189-196, with each word's lemma, morphological tag and character offsets
- FORMAT_SPEC.md: exactly what to produce and in which format — follow it closely
- check_frames.py: validator and lookup tool for FrameNet 1.7 (uses NLTK's FrameNet data, already installed)

OUTPUT FOLDER (write only here):
C:/Users/Farnoosh/AppData/Local/Temp/claude/C--Users-Farnoosh-Documents-GitHub-DiaSoft/992c7d43-414e-4ac5-b7cb-321890c4615b/scratchpad/runA/output

SOURCES OF SENSE INFORMATION FOR THIS RUN: the LSJ glosses in lemmas.csv and your own knowledge of Ancient Greek. This run deliberately uses NO WordNet data of any kind: do not use Ancient Greek WordNet or Princeton WordNet (including NLTK's wordnet corpus) to decide what the lemmas mean.

ISOLATION RULES (this run is compared against another run, so it must be independent):
- Read nothing outside the input folder, except that you may read C:/Users/Farnoosh/Documents/GitHub/DiaSoft/homer_corpus/iliad_treebank.xml and odyssey_treebank.xml to check Homeric usage or verify a citation.
- In particular do not open anything in the DiaSoft folders wordnet_check_cluster128, cluster128_wordnet_framenet, cluster_gloss_embeddings, or anything on the user's Desktop, and do not search the web.
- Do not modify files outside the output folder.

WHAT TO DO:
1. Read FORMAT_SPEC.md first, then the inputs.
2. For every lemma in lemmas.csv (all 18, including the rare ones), decide its senses and the FrameNet 1.7 frame each sense evokes: one primary frame per lemma plus alternatives for other real senses. Explore candidate frames with `py check_frames.py search <english word>` and `py check_frames.py frame <Name>` (run from the input folder; set PYTHONIOENCODING=utf-8). Propose a new frame only where no existing FrameNet 1.7 frame captures a concept, and define it fully as the spec shows.
3. Annotate both passages with existing FrameNet 1.7 frames only, following the spec (targets, FEs with exact offsets, null instantiations, caveats for words left unannotated).
4. Write the five output files named in the spec, and run both validators (`py check_frames.py csv ...`, `py check_frames.py json ...`) until each reports 0 problems.
5. Never invent Homeric citations; mark examples as illustrative unless verified in the treebank.

When done, reply with a short summary: the primary frame per lemma, any proposed frames (names and one-line definitions), the number of annotation sets per passage, the validator results, and any uncertainties.
```

## Run B: with WordNet

```text
You are carrying out one run of a lexical-semantics experiment on Ancient Greek (Homeric) vocabulary: mapping a group of related lemmas to Berkeley FrameNet 1.7 frames and annotating two Homeric passages in FrameNet full-text format.

INPUT FOLDER (read only these files):
C:/Users/Farnoosh/AppData/Local/Temp/claude/C--Users-Farnoosh-Documents-GitHub-DiaSoft/992c7d43-414e-4ac5-b7cb-321890c4615b/scratchpad/runB/input
- lemmas.csv: the 18 lemmas (a semantic cluster from gloss embeddings: guest/hospitality, escort, attendant/service), with POS, group, Homeric frequency and LSJ glosses (glosses are truncated at ~90 characters)
- cluster_128.txt: the cluster as produced by the clustering
- passages.json: Odyssey 1.123-124 and Odyssey 7.189-196, with each word's lemma, morphological tag and character offsets
- wordnet_layer.csv and WORDNET_LAYER.md: every Ancient Greek WordNet synset linked to each lemma, resolved to Princeton WordNet 3.0 and flagged core / plausible / noise with reasons
- FORMAT_SPEC.md: exactly what to produce and in which format — follow it closely
- check_frames.py: validator and lookup tool for FrameNet 1.7 (uses NLTK's FrameNet data, already installed)

OUTPUT FOLDER (write only here):
C:/Users/Farnoosh/AppData/Local/Temp/claude/C--Users-Farnoosh-Documents-GitHub-DiaSoft/992c7d43-414e-4ac5-b7cb-321890c4615b/scratchpad/runB/output

SOURCES OF SENSE INFORMATION FOR THIS RUN: the LSJ glosses in lemmas.csv, your own knowledge of Ancient Greek, AND the WordNet layer (wordnet_layer.csv). Use the WordNet core and plausible senses systematically as evidence for which senses each lemma has and which frames they evoke; where a WordNet sense leads you to add, keep or reject a frame, say so in the `note` column (cite the synset ID) and in method_notes.md. You may also use the Princeton WordNet 3.0 synsets (pwn30_synset column) to look for FrameNet lexical units.

ISOLATION RULES (this run is compared against another run, so it must be independent):
- Read nothing outside the input folder, except that you may read C:/Users/Farnoosh/Documents/GitHub/DiaSoft/homer_corpus/iliad_treebank.xml and odyssey_treebank.xml to check Homeric usage or verify a citation.
- In particular do not open anything in the DiaSoft folders wordnet_check_cluster128, cluster128_wordnet_framenet, cluster_gloss_embeddings, or anything on the user's Desktop, and do not search the web.
- Do not modify files outside the output folder.

WHAT TO DO:
1. Read FORMAT_SPEC.md first, then the inputs.
2. For every lemma in lemmas.csv (all 18, including the rare ones), decide its senses and the FrameNet 1.7 frame each sense evokes: one primary frame per lemma plus alternatives for other real senses. Explore candidate frames with `py check_frames.py search <english word>` and `py check_frames.py frame <Name>` (run from the input folder; set PYTHONIOENCODING=utf-8). Propose a new frame only where no existing FrameNet 1.7 frame captures a concept, and define it fully as the spec shows.
3. Annotate both passages with existing FrameNet 1.7 frames only, following the spec (targets, FEs with exact offsets, null instantiations, caveats for words left unannotated).
4. Write the five output files named in the spec, and run both validators (`py check_frames.py csv ...`, `py check_frames.py json ...`) until each reports 0 problems.
5. Never invent Homeric citations; mark examples as illustrative unless verified in the treebank.

When done, reply with a short summary: the primary frame per lemma, any proposed frames (names and one-line definitions), the number of annotation sets per passage, the validator results, which frame decisions the WordNet layer changed, and any uncertainties.
```
