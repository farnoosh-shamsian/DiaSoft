# -*- coding: utf-8 -*-
"""
embed_occurrences.py — Stage-WSI step 1: contextual occurrence embeddings.

Every content token (noun / verb / adjective) of both Homer treebanks is
embedded IN CONTEXT with GreBERTa (bowphs/GreBerta), a monolingual Ancient-Greek
RoBERTa. Unlike the FastText / gloss vectors used elsewhere in DiaSoft — one
vector per lemma *type* — this gives one vector per *occurrence*, which is what
word-sense induction (step 2) needs to tell the senses of a polysemous word apart.

Method
  - Reuse treebank.py (iter_sentences) to get each AGLDT sentence's words in
    text order, with lemma + decomposed POS + book.line already parsed.
  - Reconstruct the surface sentence string, recording each token's char span.
  - One forward pass per sentence; each target token's vector is the mean of its
    sub-word pieces, averaged over the last 4 hidden layers, then L2-normalized.
  - GreBERTa is polytonic-aware, so Homeric diacritics (oxia/tonos) are kept
    as-is (NFC); a startup probe prints the sub-word split of a sample word so
    you can confirm nothing is being stripped.

Outputs (word_sense_induction/wsi_output/)
  occ_vectors.npy   (N, H) float32, one L2-normalized row per occurrence
  occ_index.csv     lemma, pos, work, book, line, sentence_id, word_id, form, row

Run:   py word_sense_induction/embed_occurrences.py            (full corpus)
       py word_sense_induction/embed_occurrences.py --smoke    (Iliad book 1)
Dependencies: torch, transformers  (plus pandas, numpy)
"""

import argparse
import sys
import time

import numpy as np
import pandas as pd

import wsi_common as C

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LAST_N_LAYERS = 4        # hidden layers averaged per sub-word
MAX_LEN       = 512      # RoBERTa position limit; longer sentences are truncated
BATCH_SIZE    = 16


# ---------------------------------------------------------------------------
# Sentence reconstruction (offsets consistent with " ".join of the forms)
# ---------------------------------------------------------------------------
def sentence_text_and_targets(words, tb):
    """Return (text, targets). `targets` holds the char span + metadata for each
    content token that has a surface form. Elided/artificial nodes (empty form)
    contribute nothing and are never targets."""
    text_parts, targets, cursor = [], [], 0
    for w in words:
        form = (w.get("form") or "").strip()
        if not form:
            continue
        if text_parts:
            cursor += 1                      # the space that " ".join inserts
        start, end = cursor, cursor + len(form)
        text_parts.append(form)
        cursor = end
        lemma = w.get("lemma") or ""
        if (w.get("pos") in C.CONTENT_POS and lemma
                and lemma not in tb.ARTIFACTS and tb.GREEK_LETTER.search(lemma)):
            targets.append({
                "start": start, "end": end, "form": form,
                "lemma": lemma, "pos": w.get("pos"), "work": w.get("work"),
                "book": w.get("book"), "line": w.get("line"),
                "sentence_id": w.get("sentence_id"), "word_id": w.get("word_id"),
            })
    return " ".join(text_parts), targets


def load_sentences(tb, smoke=False, max_sentences=None):
    """List of (text, targets) over both treebanks. --smoke keeps only Iliad
    book 1 for a fast end-to-end check."""
    out = []
    for path in tb.TREEBANK_FILES:
        for _meta, words in tb.iter_sentences(path):
            text, targets = sentence_text_and_targets(words, tb)
            if not targets:
                continue
            if smoke:
                t0 = targets[0]
                if not (t0["work"] == "Iliad" and t0["book"] == 1):
                    continue
            out.append((text, targets))
            if max_sentences and len(out) >= max_sentences:
                return out
    return out


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------
def diacritics_probe(tok):
    """Print how GreBERTa splits a few polytonic Homeric words — a visual check
    that oxia/tonos survive tokenization (they should: GreBERTa is polytonic)."""
    samples = ["μῆνιν", "ἄειδε", "θεά", "Ἀχιλῆος", "πολύτλας"]
    print("Diacritics probe (word -> sub-word pieces):")
    for s in samples:
        pieces = tok.tokenize(s)
        print(f"   {s:>10}  ->  {pieces}")


def embed(sentences, model, tok, device, np_torch):
    torch = np_torch
    vectors, rows = [], []
    n_skipped = 0
    t_start = time.time()
    for bi in range(0, len(sentences), BATCH_SIZE):
        batch = sentences[bi:bi + BATCH_SIZE]
        texts = [t for t, _ in batch]
        enc = tok(texts, return_offsets_mapping=True, padding=True,
                  truncation=True, max_length=MAX_LEN, return_tensors="pt")
        offsets = enc.pop("offset_mapping").numpy()
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            out = model(**enc)
        # mean of the last N hidden layers -> (B, T, H)
        hs = torch.stack(out.hidden_states[-LAST_N_LAYERS:], 0).mean(0)
        hs = hs.to("cpu").numpy()
        for k, (_text, targets) in enumerate(batch):
            sub = offsets[k]                          # (T, 2) char spans
            real = sub[:, 1] > sub[:, 0]              # drop special tokens (0,0)
            for tgt in targets:
                mask = real & (sub[:, 0] < tgt["end"]) & (sub[:, 1] > tgt["start"])
                idx = np.nonzero(mask)[0]
                if idx.size == 0:                     # truncated past MAX_LEN
                    n_skipped += 1
                    continue
                vec = hs[k, idx].mean(0)
                nrm = np.linalg.norm(vec)
                if nrm == 0:
                    n_skipped += 1
                    continue
                vectors.append((vec / nrm).astype(np.float32))
                rows.append({
                    "lemma": tgt["lemma"], "pos": tgt["pos"], "work": tgt["work"],
                    "book": tgt["book"], "line": tgt["line"],
                    "sentence_id": tgt["sentence_id"], "word_id": tgt["word_id"],
                    "form": tgt["form"],
                })
        done = min(bi + BATCH_SIZE, len(sentences))
        if done % (BATCH_SIZE * 25) == 0 or done == len(sentences):
            rate = done / max(time.time() - t_start, 1e-6)
            print(f"   {done:>6}/{len(sentences)} sentences "
                  f"({len(vectors):,} occ, {rate:.0f} sent/s)")
    return vectors, rows, n_skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true",
                    help="Iliad book 1 only (fast end-to-end check)")
    ap.add_argument("--max-sentences", type=int, default=None)
    ap.add_argument("--force", action="store_true",
                    help="recompute even if the cache exists")
    args = ap.parse_args()

    C.OUTPUT_DIR.mkdir(exist_ok=True)
    if C.OCC_VECTORS.exists() and not args.force and not args.smoke:
        print(f"Cache present ({C.OCC_VECTORS.name}); use --force to recompute.")
        return

    print("Loading reusable treebank parser ...")
    tb = C.load_treebank()

    print("Reconstructing sentences from the treebanks ...")
    sentences = load_sentences(tb, smoke=args.smoke,
                               max_sentences=args.max_sentences)
    n_targets = sum(len(t) for _, t in sentences)
    print(f"   {len(sentences):,} sentences, {n_targets:,} content-token targets")

    print(f"Loading GreBERTa ({C.MODEL_NAME}) — first run downloads from HF ...")
    import torch
    from transformers import AutoTokenizer, AutoModel
    tok = AutoTokenizer.from_pretrained(C.MODEL_NAME)
    if not tok.is_fast:
        sys.exit("ERROR: a FAST tokenizer is required for offset mapping.")
    model = AutoModel.from_pretrained(C.MODEL_NAME, output_hidden_states=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    print(f"   device={device}, hidden_size={model.config.hidden_size}, "
          f"layers averaged=last {LAST_N_LAYERS}")
    diacritics_probe(tok)

    print("Embedding occurrences ...")
    vectors, rows, n_skipped = embed(sentences, model, tok, device, torch)
    if not vectors:
        sys.exit("ERROR: no occurrences embedded.")
    arr = np.vstack(vectors)
    df = pd.DataFrame(rows)
    df["row"] = np.arange(len(df))

    np.save(C.OCC_VECTORS, arr)
    df.to_csv(C.OCC_INDEX, index=False, encoding="utf-8")
    print(f"\nSaved {arr.shape[0]:,} occurrence vectors (dim {arr.shape[1]}) "
          f"-> {C.OCC_VECTORS.name}")
    print(f"Saved index ({len(df):,} rows) -> {C.OCC_INDEX.name}")
    if n_skipped:
        print(f"Skipped {n_skipped:,} targets (truncated past {MAX_LEN} sub-words)")
    print(f"Distinct content lemmas: {df['lemma'].nunique():,}")


if __name__ == "__main__":
    main()
