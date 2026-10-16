"""Merge the extracted synsets with the sense flags into the final CSV.

Inputs:  output/cluster128_synsets_raw.csv (from extract_synsets.py)
         output/agent_flags.csv  (core / plausible flags with reasons; every
                                  synset not listed there was reviewed and
                                  judged noise)
         input/greek_hospitality_wordnet_annotated.csv (for the ξενία check)
Output:  output/cluster128_wordnet_flagged.csv, in the columns of
         greek_hospitality_wordnet_annotated.csv, sorted per lemma
         core -> plausible -> noise; and output/summary.txt.
"""

import collections
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "output" / "cluster128_synsets_raw.csv"
FLAGS = HERE / "output" / "agent_flags.csv"
LEMMAS = HERE / "input" / "lemmas.csv"
REF = HERE / "input" / "greek_hospitality_wordnet_annotated.csv"
OUT = HERE / "output" / "cluster128_wordnet_flagged.csv"
SUMMARY = HERE / "output" / "summary.txt"

TRANSLIT = {
    "ξένος": "xenos", "ξένιος": "xenios", "ξενίζω": "xenizo",
    "ξενία": "xenia", "ξενοσύνη": "xenosyne", "ξεινήιον": "xeineion",
    "ὑποδεξίη": "hypodexie", "φιλόξενος": "philoxenos",
    "δαιτυμών": "daitymon", "πομπή": "pompe", "πομπός": "pompos",
    "πομπεύς": "pompeus", "πομπεύω": "pompeuo", "θεραπεύω": "therapeuo",
    "ἀμφιπολεύω": "amphipoleuo", "οἰνοχόος": "oinochoos",
    "ὑποδρηστήρ": "hypodrester", "ταμίας": "tamias",
}
COLUMNS = ["translit", "greek_lemma", "pos", "sense_flag", "flag_method",
           "synset_id", "english_words", "gloss", "pwn_hypernym_id",
           "pwn_hypernym_words", "lemma_note"]
ORDER = {"core": 0, "plausible": 1, "noise": 2}


def read(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    lemmas = read(LEMMAS)
    raw = read(RAW)
    flags = {(r["greek_lemma"], r["synset_id"]): r["sense_flag"]
             for r in read(FLAGS)}

    present = {(r["greek_lemma"], r["synset_id"]) for r in raw}
    stray = [k for k in flags if k not in present]
    if stray:
        sys.exit(f"flags for synsets not in the extraction: {stray}")

    by_lemma = collections.defaultdict(list)
    for r in raw:
        flag = flags.get((r["greek_lemma"], r["synset_id"]), "noise")
        by_lemma[r["greek_lemma"]].append({**r, "sense_flag": flag})

    out_rows, lines = [], []
    lines.append(f"{'lemma':12} {'group':18} {'synsets':>7} {'core':>5} "
                 f"{'plaus.':>6} {'noise':>6}")
    for row in lemmas:
        lemma = row["lookup_lemma"]
        rows = sorted(by_lemma.get(lemma, []),
                      key=lambda r: ORDER[r["sense_flag"]])
        note = row["note"]
        if not rows:
            note = "; ".join(x for x in (note, "in AGWN but no synsets linked")
                             if x)
        c = collections.Counter(r["sense_flag"] for r in rows)
        lines.append(f"{lemma:12} {row['subgroup']:18} {len(rows):7} "
                     f"{c['core']:5} {c['plausible']:6} {c['noise']:6}")
        for r in rows:
            out_rows.append({
                "translit": TRANSLIT[lemma], "greek_lemma": lemma,
                "pos": r["pos"], "sense_flag": r["sense_flag"],
                "flag_method": "agent", "synset_id": r["synset_id"],
                "english_words": r["english_words"], "gloss": r["gloss"],
                "pwn_hypernym_id": r["pwn_hypernym_id"],
                "pwn_hypernym_words": r["pwn_hypernym_words"],
                "lemma_note": note,
            })

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out_rows)

    c = collections.Counter(r["sense_flag"] for r in out_rows)
    lines.append(f"{'TOTAL':12} {'':18} {len(out_rows):7} {c['core']:5} "
                 f"{c['plausible']:6} {c['noise']:6}")

    # check against the protocol's flags for the lemmas both files share
    ref = read(REF)
    for lemma in ("ξενία", "ξένος"):
        theirs = {r["synset_id"]: (r["sense_flag"], r["flag_method"])
                  for r in ref if r["greek_lemma"] == lemma}
        mine = {r["synset_id"]: r["sense_flag"] for r in out_rows
                if r["greek_lemma"] == lemma}
        shared = theirs.keys() & mine.keys()
        agree = sum(1 for s in shared if theirs[s][0] == mine[s])
        method = {m for _, m in theirs.values()}
        lines.append("")
        lines.append(f"{lemma} vs. protocol ({'/'.join(sorted(method))} "
                     f"flags): {len(shared)} shared synsets, {agree} same "
                     f"flag ({agree / len(shared):.0%})")
        tab = collections.Counter((theirs[s][0], mine[s]) for s in shared)
        for (t, m), n in sorted(tab.items()):
            if t != m:
                lines.append(f"   protocol {t:9} -> agent {m:9} {n}")

    text = "\n".join(lines)
    SUMMARY.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
