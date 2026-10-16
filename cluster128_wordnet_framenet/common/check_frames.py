"""Check frame assignments and passage annotations against FrameNet 1.7.

    py check_frames.py frame <FrameName> [...]   show a frame's definition and FEs
    py check_frames.py search <word> [...]       frames whose name or LUs match
    py check_frames.py csv <assignments.csv>     validate a frame-assignment CSV
    py check_frames.py json <annotation.json>    validate a passage annotation

The CSV check: every row with frame_status "existing (FN1.7)" must name a real
frame, and its frame_core_FEs must be exactly that frame's core FEs. The JSON
check: existing frames and FE names must be real, and every span's stored text
must equal the slice of the sentence at its offsets (0-based, end inclusive).
Uses NLTK's FrameNet 1.7 data.
"""

import csv
import json
import sys

from nltk.corpus import framenet as fn


def core_fes(frame):
    return [n for n, fe in frame.FE.items() if fe.coreType == "Core"]


def get_frame(name):
    try:
        return fn.frame(name)
    except Exception:
        return None


def show(names):
    for name in names:
        f = get_frame(name)
        if not f:
            print(f"{name}: NOT a FrameNet 1.7 frame")
            continue
        print(f"== {f.name}\n{f.definition[:600]}")
        print("core FEs:", ", ".join(core_fes(f)))
        print("non-core FEs:", ", ".join(n for n, fe in f.FE.items()
                                          if fe.coreType != "Core"))
        rel = sorted({f"{r.type.name}: {r.superFrameName} > {r.subFrameName}"
                      for r in f.frameRelations})
        print("relations:", "; ".join(rel[:12]))
        print("LUs:", ", ".join(sorted(f.lexUnit)[:40]), "\n")


def search(words):
    for w in words:
        hits = {lu.frame.name for lu in fn.lus(r"(?i)^" + w + r"\.")}
        hits |= {f.name for f in fn.frames(r"(?i)" + w)}
        print(f"{w}: {', '.join(sorted(hits)) or '—'}")


def check_csv(path):
    errors = 0
    with open(path, encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            if not r["frame_status"].startswith("existing"):
                continue
            fr = get_frame(r["frame"])
            if not fr:
                print(f"line {i}: {r['frame']} is not a FrameNet 1.7 frame")
                errors += 1
                continue
            given = [x.strip() for x in r["frame_core_FEs"].split(",")]
            if sorted(given) != sorted(core_fes(fr)):
                print(f"line {i}: {r['frame']} core FEs are "
                      f"{', '.join(core_fes(fr))}; CSV has {', '.join(given)}")
                errors += 1
    print(f"{path}: {errors} problem(s)")
    return errors


def check_json(path):
    errors = 0
    doc = json.load(open(path, encoding="utf-8"))
    for s in doc["sentences"]:
        text = s["text"]
        for a in s["annotationSets"]:
            spans = [a["target"]] + [fe for fe in a["FEs"] if "start" in fe]
            for sp in spans:
                got = text[sp["start"]:sp["end"] + 1]
                if got != sp["text"]:
                    print(f"sentence {s['id']} set {a['id']}: "
                          f"{sp['name']} offsets give {got!r}, "
                          f"stored {sp['text']!r}")
                    errors += 1
            if a.get("frameStatus") != "existing":
                continue
            fr = get_frame(a["frameName"])
            if not fr:
                print(f"set {a['id']}: {a['frameName']} is not a FN 1.7 frame")
                errors += 1
                continue
            for fe in a["FEs"]:
                if fe["name"] not in fr.FE:
                    print(f"set {a['id']}: {fe['name']} is not an FE of "
                          f"{fr.name}")
                    errors += 1
    print(f"{path}: {errors} problem(s)")
    return errors


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "frame":
        show(args)
    elif cmd == "search":
        search(args)
    elif cmd == "csv":
        sys.exit(1 if check_csv(args[0]) else 0)
    elif cmd == "json":
        sys.exit(1 if check_json(args[0]) else 0)


if __name__ == "__main__":
    main()
