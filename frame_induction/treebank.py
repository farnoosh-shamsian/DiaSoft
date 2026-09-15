# Parses the two Ancient Greek Dependency Treebank into (1) a rich per-token table (lemma + decomposed morphology + head + relation + book.line) and (2) predicate-argument tuples, one per verb occurrence.

import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Lazy CLTK normalization: identical treatment to the other DiaSoft scripts so lemmas join cleanly to LSJ / AGWN / FastText vocabularies. Falls back to NFC if CLTK is unavailable.
try:
    from cltk.alphabet.text_normalization import cltk_normalize
except Exception:  # pragma: no cover
    def cltk_normalize(s):
        return unicodedata.normalize("NFC", s)


HERE  = Path(__file__).parent      
REPO  = HERE.parent
CORPUS = REPO / "homer_corpus"
TREEBANK_FILES = [CORPUS / "iliad_treebank.xml",
                  CORPUS / "odyssey_treebank.xml"]

GREEK_LETTER = re.compile(r"[Ͱ-Ͽἀ-῿]")
# English words typed in beta-code Greek letters 
ARTIFACTS = {"θυοτε", "οτηερ", "υνκνοων", "ηψπηεν"}   

POS_NAME = {
    "n": "noun", "v": "verb", "a": "adjective", "d": "adverb", "l": "article",
    "g": "particle", "c": "conjunction", "r": "preposition", "p": "pronoun",
    "m": "numeral", "i": "interjection", "e": "exclamation", "u": "punctuation",
    "x": "irregular",
}
VOICE_NAME = {"a": "active", "p": "passive", "m": "middle",
              "e": "medio-passive", "d": "deponent"}
POSTAG_FIELDS = ["pos", "person", "number", "tense", "mood", "voice",
                 "gender", "case", "degree"]
FILLER_POS = {"n", "p", "a", "m"}     
ARG_SLOTS  = ("SBJ", "OBJ", "PNOM")


# Low-level parsing helpers
def _work_from_urn(urn):
    if not urn:
        return "?"
    if "tlg0012.tlg001" in urn:
        return "Iliad"
    if "tlg0012.tlg002" in urn:
        return "Odyssey"
    return "?"


def _book_line(cite):
    if not cite:
        return None, None
    tail = cite.rsplit(":", 1)[-1]      # '1.1'
    m = re.match(r"^(\d+)\.(\d+)", tail)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def _decode_postag(postag):
    tag = (postag or "").ljust(9, "-")[:9]
    out = {}
    for i, name in enumerate(POSTAG_FIELDS):
        ch = tag[i]
        out[name] = None if ch in "-" else ch
    return out


def _base_relation(rel):
    if not rel:
        return ""
    base = rel
    while base.endswith("_CO") or base.endswith("_AP"):
        base = base[:-3]
    return base


def iter_sentences(path):
    for _event, elem in ET.iterparse(str(path), events=("end",)):
        if elem.tag != "sentence":
            continue
        doc_id = elem.get("document_id", "")
        work = _work_from_urn(doc_id)
        meta = {"sentence_id": elem.get("id"),
                "subdoc": elem.get("subdoc"),
                "work": work,
                "document_id": doc_id}
        words = []
        for w in elem.findall("word"):
            cite = w.get("cite")
            book, line = _book_line(cite)
            lemma_raw = w.get("lemma", "")
            lemma = cltk_normalize(lemma_raw.strip()) if lemma_raw else ""
            rec = {
                "work": work,
                "sentence_id": meta["sentence_id"],
                "subdoc": meta["subdoc"],
                "book": book,
                "line": line,
                "word_id": _safe_int(w.get("id")),
                "head": _safe_int(w.get("head")),
                "relation": w.get("relation", "") or "",
                "form": w.get("form", ""),
                "lemma": lemma,
                "postag": w.get("postag", ""),
            }
            rec.update(_decode_postag(w.get("postag", "")))
            words.append(rec)
        yield meta, words
        elem.clear()    


def _safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _is_content_filler(rec):
    return (rec["pos"] in FILLER_POS
            and rec["lemma"]
            and rec["lemma"] not in ARTIFACTS
            and GREEK_LETTER.search(rec["lemma"]))


# 
# 1. Token table

TOKEN_COLUMNS = ["work", "sentence_id", "subdoc", "book", "line", "word_id",
                 "form", "lemma", "pos", "person", "number", "tense", "mood",
                 "voice", "gender", "case", "degree", "head", "relation",
                 "postag"]


def build_token_table(paths=TREEBANK_FILES):
    """Parse all treebanks into one long token DataFrame."""
    records = []
    for path in paths:
        for _meta, words in iter_sentences(path):
            records.extend(words)
    df = pd.DataFrame.from_records(records)
    return df[TOKEN_COLUMNS]

# 2. Predicate-argument extraction

def _children_index(words):
    idx = defaultdict(list)
    for w in words:
        if w["head"] is not None:
            idx[w["head"]].append(w)
    return idx


def _resolve_oblique(prep_rec, children):

    for c in children.get(prep_rec["word_id"], []):
        if _is_content_filler(c):
            return (prep_rec["lemma"], c["case"], c["lemma"])
    return None


def _collect_args(verb_id, children):

    slots = {s: [] for s in ARG_SLOTS}
    obliques = []
    seen = set()

    def visit(node_id):
        if node_id in seen:              
            return
        seen.add(node_id)
        for c in children.get(node_id, []):
            rel = c["relation"]
            base = _base_relation(rel)
            if base in ("COORD", "APOS"):
                visit(c["word_id"])   
            elif base in ARG_SLOTS:
                if _is_content_filler(c):
                    slots[base].append(c["lemma"])
                if rel != base:         
                    visit(c["word_id"])
            elif base == "AuxP":
                ob = _resolve_oblique(c, children)
                if ob:
                    obliques.append(ob)
            elif base == "ADV" and _is_content_filler(c):
                obliques.append((None, c["case"], c["lemma"]))   # bare oblique
            # ATR / AuxV / AuxY / AuxX / ExD / UNDEFINED etc.: not arguments

    visit(verb_id)
    return slots, obliques


def extract_predicate_arguments(paths=TREEBANK_FILES):
    rows = []
    for path in paths:
        for _meta, words in iter_sentences(path):
            children = _children_index(words)
            for w in words:
                if w["pos"] != "v" or not w["lemma"]:
                    continue
                if w["lemma"] in ARTIFACTS or not GREEK_LETTER.search(w["lemma"]):
                    continue
                slots, obliques = _collect_args(w["word_id"], children)
                rows.append({
                    "work": w["work"],
                    "book": w["book"],
                    "line": w["line"],
                    "sentence_id": w["sentence_id"],
                    "verb_lemma": w["lemma"],
                    "voice": VOICE_NAME.get(w["voice"], w["voice"] or ""),
                    "mood": w["mood"] or "",
                    "tense": w["tense"] or "",
                    "sbj": "|".join(slots["SBJ"]),
                    "obj": "|".join(slots["OBJ"]),
                    "pnom": "|".join(slots["PNOM"]),
                    "obliques": ";".join(
                        f"{p or ''}:{c or ''}:{f}" for p, c, f in obliques),
                    "n_args": sum(len(slots[s]) for s in ARG_SLOTS) + len(obliques),
                })
    return pd.DataFrame.from_records(rows)


def verb_slot_fillers(pa_df, slots=("sbj", "obj")):
    """{verb_lemma: {slot: Counter(filler -> count)}} from the tuple table —
    the argument profile used for frame induction."""
    profiles = defaultdict(lambda: {s: Counter() for s in slots})
    for _i, r in pa_df.iterrows():
        for s in slots:
            cell = r[s]
            if isinstance(cell, str) and cell:
                for filler in cell.split("|"):
                    if filler:
                        profiles[r["verb_lemma"]][s][filler] += 1
    return profiles


 
# CLI self-test 
def _selftest():
    print("Parsing treebanks (work identity from CTS URN, not filename) ...")
    tok = build_token_table()
    print(f"\nToken table: {len(tok):,} tokens, columns = {list(tok.columns)}")
    for work, sub in tok.groupby("work"):
        n_books = sub["book"].dropna().nunique()
        print(f"  {work:8s}: {len(sub):>7,} tokens, {n_books} books, "
              f"{sub['sentence_id'].nunique():,} sentences")

    print("\nSpot-check — Iliad 1.1 (proem), first tokens:")
    proem = tok[(tok.work == "Iliad") & (tok.book == 1) & (tok.line == 1)]
    for _i, r in proem.head(4).iterrows():
        print(f"  {r['form']:12s} lemma={r['lemma']:10s} pos={r['pos']} "
              f"postag={r['postag']} head={r['head']} rel={r['relation']}")

    print("\nExtracting predicate-argument tuples ...")
    pa = extract_predicate_arguments()
    print(f"  {len(pa):,} verb occurrences, "
          f"{pa['verb_lemma'].nunique():,} distinct verb lemmas")

    print("\nProem verb(s) — ἄειδε should govern OBJ μῆνις:")
    proem_pa = pa[(pa.work == "Iliad") & (pa.book == 1) & (pa.line == 1)]
    for _i, r in proem_pa.iterrows():
        print(f"  {r.verb_lemma} (voice={r.voice}, mood={r.mood}) "
              f"SBJ=[{r.sbj}] OBJ=[{r.obj}] obl=[{r.obliques}]")

    print("\nA few high-frequency verbs and their top objects (selectional pref.):")
    prof = verb_slot_fillers(pa)
    top_verbs = pa["verb_lemma"].value_counts().head(6).index
    for v in top_verbs:
        objs = prof[v]["obj"].most_common(5)
        print(f"  {v:12s} obj-> " + ", ".join(f"{o}({c})" for o, c in objs))

    out = HERE / "predicate_arguments.csv"
    pa.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    _selftest()
