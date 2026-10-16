"""Extract every AGWN synset linked to the cluster-128 lemmas.

Reads the AGWN SQL dump in ../agwn_dump/ (greek_index, english_synset,
common_relation; from github.com/jcuenod/greekwordnet, MultiWordNet 1.5
format) as plain text, and writes output/cluster128_synsets_raw.csv: one row
per (lemma, synset) with English words, gloss and hypernym. Lemmas are matched
exactly (NFC), never as substrings.
"""

import csv
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
DUMP = HERE.parent / "agwn_dump"
LEMMAS = HERE / "input" / "lemmas.csv"
OUT = HERE / "output" / "cluster128_synsets_raw.csv"

POS = {"id_n": "n", "id_v": "v", "id_a": "a", "id_r": "r"}


def nfc(s):
    return unicodedata.normalize("NFC", s)


def parse_values(tuple_text):
    """Split the inside of a SQL VALUES (...) tuple into Python values."""
    vals, i, n = [], 0, len(tuple_text)
    while i < n:
        c = tuple_text[i]
        if c == "'":
            i += 1
            buf = []
            while i < n:
                c = tuple_text[i]
                if c == "\\" and i + 1 < n:
                    buf.append(tuple_text[i + 1])
                    i += 2
                    continue
                if c == "'":
                    if i + 1 < n and tuple_text[i + 1] == "'":
                        buf.append("'")
                        i += 2
                        continue
                    break
                buf.append(c)
                i += 1
            vals.append("".join(buf))
            i += 1
        elif tuple_text.startswith("NULL", i):
            vals.append(None)
            i += 4
        elif c in ", ":
            i += 1
        else:
            j = i
            while j < n and tuple_text[j] not in ",":
                j += 1
            vals.append(tuple_text[i:j].strip())
            i = j
    return vals


def iter_rows(path, table):
    prefix = f"INSERT INTO {table} VALUES ("
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith(prefix):
                yield parse_values(line[len(prefix):].rstrip().rstrip(";")[:-1])


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    with LEMMAS.open(encoding="utf-8") as f:
        lemmas = list(csv.DictReader(f))
    wanted = {}
    for row in lemmas:
        for form in row["agwn_query_forms"].split(";"):
            wanted.setdefault(nfc(form.strip()), []).append(row["lookup_lemma"])

    # lemma -> [(pos, synset_id, matched_form)]
    links, found_form = {}, {}
    for lemma, *ids in iter_rows(DUMP / "greek_index.sql", "greek_index"):
        key = nfc(lemma)
        if key not in wanted:
            continue
        for col, val in zip(POS, ids):
            for sid in (val or "").split():
                for lookup in wanted[key]:
                    links.setdefault(lookup, []).append((POS[col], sid, key))
                    found_form.setdefault(lookup, set()).add(key)

    needed = {sid for v in links.values() for _, sid, _ in v}
    synsets = {}
    for sid, words, _phrase, gloss in iter_rows(DUMP / "english_synset.sql",
                                                "english_synset"):
        if sid in needed:
            # the dump double-escapes quotes inside glosses (\\")
            gloss = re.sub(r'\\+"', '"', gloss or "")
            synsets[sid] = (" ".join((words or "").split()), gloss)

    hyper = {}
    for rtype, src, tgt, _status in iter_rows(DUMP / "common_relation.sql",
                                              "common_relation"):
        if rtype == "@" and src in needed:
            hyper.setdefault(src, tgt)
    hyper_ids = set(hyper.values())
    hyper_words = {}
    for sid, words, _phrase, _gloss in iter_rows(DUMP / "english_synset.sql",
                                                 "english_synset"):
        if sid in hyper_ids:
            hyper_words[sid] = " ".join((words or "").split())

    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["greek_lemma", "matched_form", "pos", "synset_id",
                    "english_words", "gloss", "pwn_hypernym_id",
                    "pwn_hypernym_words"])
        for row in lemmas:
            lemma = row["lookup_lemma"]
            seen = set()
            for pos, sid, form in links.get(lemma, []):
                if sid in seen:
                    continue
                seen.add(sid)
                words, gloss = synsets.get(sid, ("", ""))
                h = hyper.get(sid, "")
                w.writerow([lemma, form, pos, sid, words, gloss, h,
                            hyper_words.get(h, "")])
            print(f"{lemma:12} {len(seen):4} synsets  "
                  f"matched: {', '.join(sorted(found_form.get(lemma, []))) or '—'}")


if __name__ == "__main__":
    main()
