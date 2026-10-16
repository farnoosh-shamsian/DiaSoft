"""Fetch a raw Ancient Greek WordNet snapshot for the cluster-128 lemmas.

Reads input/lemmas.csv and, for each lookup lemma, queries the AGWN API
(https://greekwordnet.chs.harvard.edu/api/lemmas/<lemma>/synsets/) with each
form in `agwn_query_forms` until one returns results. Every response is saved
verbatim to input/agwn_snapshot/<lookup_lemma>.json, plus a manifest.json
recording the date, URLs and HTTP status of each request. Lemmas already in
the snapshot are skipped; --refetch overwrites them.
"""

import csv
import datetime
import json
import sys
import unicodedata
import urllib.parse
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
LEMMAS = HERE / "input" / "lemmas.csv"
OUT = HERE / "input" / "agwn_snapshot"
MANIFEST = OUT / "manifest.json"
BASE = "https://greekwordnet.chs.harvard.edu/api/lemmas/"


def fetch_all(url, session):
    """GET url, following DRF-style `next` links; return (pages, status)."""
    pages = []
    while url:
        r = session.get(url, timeout=60)
        if r.status_code != 200:
            return pages, r.status_code
        data = r.json()
        pages.append(data)
        url = data.get("next") if isinstance(data, dict) else None
    return pages, 200


def has_results(pages):
    return any(isinstance(p, dict) and p.get("results") for p in pages)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    refetch = "--refetch" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = (json.loads(MANIFEST.read_text(encoding="utf-8"))
                if MANIFEST.exists() else {"source": BASE, "lemmas": {}})
    session = requests.Session()

    with LEMMAS.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        lemma = row["lookup_lemma"]
        target = OUT / f"{lemma}.json"
        if target.exists() and not refetch:
            print(f"skip  {lemma} (already in snapshot)")
            continue
        attempts = []
        saved = None
        for form in row["agwn_query_forms"].split(";"):
            form = unicodedata.normalize("NFC", form.strip())
            url = BASE + urllib.parse.quote(form) + "/synsets/"
            try:
                pages, status = fetch_all(url, session)
            except requests.RequestException as e:
                attempts.append({"form": form, "url": url,
                                 "error": type(e).__name__})
                continue
            attempts.append({"form": form, "url": url, "status": status,
                             "found": has_results(pages)})
            if status == 200 and has_results(pages):
                saved = {"lookup_lemma": lemma, "query_form": form,
                         "url": url, "pages": pages}
                break
        if saved:
            target.write_text(json.dumps(saved, ensure_ascii=False, indent=1),
                              encoding="utf-8")
        manifest["lemmas"][lemma] = {
            "fetched": datetime.datetime.now().isoformat(timespec="seconds"),
            "found": bool(saved),
            "attempts": attempts,
        }
        print(f"{'found' if saved else 'MISS '} {lemma}  "
              f"{[a.get('status', a.get('error')) for a in attempts]}")

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    n = sum(1 for v in manifest["lemmas"].values() if v["found"])
    print(f"\n{n}/{len(rows)} lemmas found in AGWN; manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
