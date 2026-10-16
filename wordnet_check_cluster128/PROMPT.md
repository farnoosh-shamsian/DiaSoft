Recreate the "WordNet Check" stage of the protocol in
wordnet_check_cluster128/input/protocol_wordnet_framenet_xenia_proxenia.md
on my own cluster, so that the result is reproducible by script rather than
by model judgment. Work only inside wordnet_check_cluster128/.

Input (all in wordnet_check_cluster128/input/)
- cluster_128.txt: cluster 128 ("guest, hospitality, escort, attendant",
  20 lemmas) from the Ward k=200 gloss-embedding clustering, no frequency
  limit. The full clustering is clusters_ward_k200_no-freq-limit.txt.
  Each line is: lemma (Homeric frequency): LSJ glosses.
- lemmas.csv: the 18 AGWN lookups after merging duplicates
  (ξένος/ξένος2, τάμιας/ταμίας), with sub-group and the query forms to try.
- agwn_snapshot/: raw Ancient Greek WordNet API responses, one JSON per
  lemma, plus manifest.json. If it is empty or incomplete, run
  `py fetch_agwn.py` (in wordnet_check_cluster128/) first and report which
  lemmas AGWN does not have.
- greek_hospitality_wordnet_annotated.csv: colleagues' output from the
  protocol. Its ξενία rows (flag_method = manual) are the check set.

Steps
1. Read the synsets only from agwn_snapshot/ (never the live API), with
   synset ID, English words, gloss and hypernym.
2. Flag each synset core / plausible / noise with a written, deterministic
   rule based on the cluster's own LSJ gloss vocabulary from cluster_128.txt:
   core = the synset's English words overlap the cluster vocabulary;
   plausible = only its hypernym overlaps; noise = neither.
   Put the rule in the script and in the report. Set flag_method = "rule".
3. Validate: compare the rule's flags for ξενία with the colleagues' manual
   flags; report agreement and list every disagreement.
4. Write to wordnet_check_cluster128/output/:
   - flag_synsets.py, rerunnable with one command, identical output each run
   - cluster128_wordnet_flagged.csv with the colleagues' columns:
     translit, greek_lemma, pos, sense_flag, flag_method, synset_id,
     english_words, gloss, pwn_hypernym_id, pwn_hypernym_words, lemma_note
   - report.md: lemmas found / missing in AGWN, synset counts per flag and
     sub-group, the rule, the ξενία agreement, and which rows need human
     review.

Do not hand-flag anything yourself; mark uncertain cases for review instead.
Leave FrameNet annotation for a later step.
