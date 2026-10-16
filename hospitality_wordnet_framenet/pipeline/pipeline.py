"""WordNet + FrameNet pipeline for one gloss-embedding cluster.

Redoes the Ancient Greek hospitality WordNet & FrameNet experiment (July 2026)
with the lemmas of a cluster. Each experiment folder holds an `experiment.json` naming
the cluster, its lemmas (with merges, groups and AGWN spellings) and the
passages to annotate. Steps, in order:

    py pipeline.py prepare  <exp>   common/ inputs + vocabulary table
    py pipeline.py passages <exp>   rank treebank sentences by cluster lemmas
    py pipeline.py extract  <exp>   AGWN synsets of every lemma (from the dump)
    py pipeline.py resolve  <exp>   resolve synsets to PWN 3.0, add sense flags
    py pipeline.py links    <exp>   WordNet layer as HTML
    py pipeline.py render   <exp> <run_output> <A_without_wordnet|B_with_wordnet> [--wordnet]
    py pipeline.py compare  <exp> <original_framenet_csv> <original_odyssey_1_123_json>
    py pipeline.py index    <exp> [<exp> ...]   index.html in the project folder

Sense flags (core / plausible / noise) are a judgment step between `extract`
and `resolve`: AGWN_PWN/sense_flags.csv lists the core and plausible synsets
with a reason; every other synset counts as noise. Frame assignments and
passage annotations come from the two runs (without / with WordNet), each
written to <run_output> by a separate agent following common/FORMAT_SPEC.md.
"""

import collections
import csv
import difflib
import html
import json
import re
import shutil
import sys
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent          # hospitality_wordnet_framenet/
REPO = PROJECT.parent
DUMP = PROJECT / "agwn_dump"
TREEBANKS = [REPO / "homer_corpus" / "iliad_treebank.xml",
             REPO / "homer_corpus" / "odyssey_treebank.xml"]
POS = {"n": "n", "a": "a", "v": "v", "t": "v"}  # participles count as verbs
FLAG_ORDER = {"core": 0, "plausible": 1, "noise": 2}
FN_URL = "https://framenet.icsi.berkeley.edu/frames/"
# tag colours per group, in order (framenet page, links page)
TAG_FN = [("#e1f5ee", "var(--teal)"), ("#eeedfe", "var(--acc)"),
          ("#f1efe8", "var(--mut)"), ("#fdf0e1", "#8a6d0b"),
          ("#fbe9ef", "#9c2b6b"), ("#e6eff8", "#1d5f99"),
          ("#eef3e0", "#5f7a1d"), ("#e4f4f4", "#2b8a8a"),
          ("#f2e9f6", "#7a3fa0")]
TAG_LINKS = [("#e1f5ee", "var(--acc)"), ("#eeedfe", "#534AB7")] + TAG_FN[2:]


# ------------------------------------------------------------------ helpers

class Exp:
    def __init__(self, path):
        self.dir = Path(path).resolve()
        self.cfg = json.loads((self.dir / "experiment.json").read_text(
            encoding="utf-8"))
        self.slug = self.cfg["slug"]
        self.title = self.cfg["title"]
        self.lemmas = self.cfg["lemmas"]
        self.groups = self.cfg["groups"]
        self.common = self.dir / "common"
        self.wn = self.dir / "AGWN_PWN"
        self.raw = self.wn / "agwn_synsets_raw.csv"
        self.flags = self.wn / "sense_flags.csv"
        self.full = self.wn / f"{self.slug}_field_wordnet_full.csv"
        self.examples = self.cfg.get("examples_dir", "Homer_Odyssey_examples")

    def lemma_rows(self):
        return read_csv(self.common / "lemmas.csv")

    def agwn_form(self):
        """The spelling under which AGWN lists each lemma."""
        forms = {l["lemma"]: l["agwn_forms"][0] for l in self.lemmas}
        if self.raw.exists():
            for r in read_csv(self.raw):
                forms[r["greek_lemma"]] = r["matched_form"]
        return forms


def nfc(s):
    return unicodedata.normalize("NFC", s)


def bare(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if not unicodedata.combining(c))
    return s.rstrip("0123456789")


def read_csv(path):
    with Path(path).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def esc(s):
    return html.escape(str(s), quote=True)


def treebank_sentences():
    for path in TREEBANKS:
        root = ET.parse(path).getroot()
        for s in root.iter("sentence"):
            yield s, [w for w in s.iter("word") if w.get("lemma")]


def cite(w):
    return w.get("cite", "").split(":")[-1]


# ------------------------------------------------------------------ prepare

def cluster_block(exp):
    lines = (REPO / exp.cfg["cluster_file"]).read_text(
        encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(lines)
                 if l.startswith(f"cluster {exp.cfg['cluster_id']} "))
    end = next((i for i in range(start + 1, len(lines))
                if not lines[i].startswith("  ")), len(lines))
    return lines[start:end]


def cmd_prepare(exp):
    exp.common.mkdir(exist_ok=True)
    block = cluster_block(exp)
    (exp.common / "cluster.txt").write_text("\n".join(block) + "\n",
                                            encoding="utf-8")
    gloss, count = {}, {}
    for line in block[1:]:
        m = re.match(r"\s+(\S+) \((\d+)\): (.*)", line)
        gloss[m.group(1)], count[m.group(1)] = m.group(3), int(m.group(2))
    listed = {f for l in exp.lemmas for f in l["cluster_forms"]}
    if listed != set(gloss):
        sys.exit(f"experiment.json and cluster differ: "
                 f"{sorted(listed ^ set(gloss))}")
    keys = {bare(nfc(l["lemma"])): l["lemma"] for l in exp.lemmas}
    tags = collections.defaultdict(collections.Counter)
    for _, words in treebank_sentences():
        for w in words:
            k = keys.get(bare(nfc(w.get("lemma"))))
            if k and w.get("postag"):
                tags[k][POS.get(w.get("postag")[0], w.get("postag")[0])] += 1
    rows = []
    for l in exp.lemmas:
        forms = l["cluster_forms"]
        rows.append({
            "greek_lemma": l["lemma"], "translit": l["translit"],
            "pos": tags[l["lemma"]].most_common(1)[0][0],
            "group": l["group"],
            "homer_count": sum(count[f] for f in forms),
            "cluster_forms": ";".join(forms),
            "lsj_glosses": " | ".join(dict.fromkeys(gloss[f] for f in forms)),
        })
    write_csv(exp.common / "lemmas.csv", rows, list(rows[0]))
    write_passages(exp)
    shutil.copy(HERE / "check_frames.py", exp.common / "check_frames.py")
    sources = "; ".join(p["source"].replace("Homer, ", "")
                        for p in exp.cfg["passages"])
    spec = (HERE / "FORMAT_SPEC_template.md").read_text(encoding="utf-8")
    spec = spec.replace("{corpus}", f"Ancient_Greek_hospitality_{exp.slug}")
    spec = spec.replace("{sources}", "Homer, " + sources)
    (exp.common / "FORMAT_SPEC.md").write_text(spec, encoding="utf-8")
    md = [f"# {exp.title}", "",
          "| Category | Term | Ancient Greek | Description | LSJ | Wikipedia "
          "| Wikidata | Wiktionary | Notes |",
          "|---|---|---|---|---|---|---|---|---|"]
    notes = {l["lemma"]: l.get("note", "") for l in exp.lemmas}
    for r in rows:
        md.append(f"| {r['group']} | {r['translit']} | {r['greek_lemma']} | "
                  f"{r['lsj_glosses']} | https://logeion.uchicago.edu/"
                  f"{r['greek_lemma']} |  |  |  | {notes[r['greek_lemma']]} |")
    (exp.dir / f"{exp.slug}_terms_table.md").write_text("\n".join(md) + "\n",
                                                       encoding="utf-8")
    print(block[0])
    print(f"{len(rows)} lemmas; passages: {sources}")


def detok(words):
    text = ""
    for w in words:
        form = nfc(w.get("form"))
        if form in {'"', "[0]"}:
            continue
        if re.fullmatch(r"[,.·;]", form):
            text = text.rstrip() + form + " "
        else:
            text += form + " "
    return text.strip().replace("μη δέ", "μηδέ")


def tokens_with_offsets(text, words):
    out, pos = [], 0
    for w in words:
        form = nfc(w.get("form"))
        if not re.search(r"\w", form):
            continue
        i = text.find(form, pos)
        if i < 0:
            continue
        out.append({"form": form, "lemma": nfc(w.get("lemma")),
                    "postag": w.get("postag"), "cite": cite(w),
                    "start": i, "end": i + len(form) - 1})
        pos = i + len(form)
    return out


def write_passages(exp):
    sentences = []
    for n, p in enumerate(exp.cfg["passages"], start=1):
        words = []
        for _, ws in treebank_sentences():
            if ws and p["work"] in ws[0].get("cite", "") and \
                    {cite(w) for w in ws} & set(p["cites"]):
                words += ws
        text = p.get("text") or detok(words)
        toks = tokens_with_offsets(text, words)
        if len(toks) != sum(1 for w in words if re.search(r"\w", w.get("form"))):
            sys.exit(f"passage {n}: could not place every word")
        sentences.append({"id": n, "source": p["source"],
                          "text_source": p["text_source"], "text": text,
                          "tokens": toks})
    (exp.common / "passages.json").write_text(
        json.dumps({"sentences": sentences}, ensure_ascii=False, indent=1),
        encoding="utf-8")


def cmd_passages(exp, top=15):
    keys = {bare(nfc(f)) for l in exp.lemmas
            for f in l["cluster_forms"] + [l["lemma"]]}
    found = []
    for _, words in treebank_sentences():
        hits = [(w.get("form"), w.get("lemma")) for w in words
                if bare(nfc(w.get("lemma"))) in keys]
        lem = {bare(nfc(l)) for _, l in hits}
        if len(lem) >= 2:
            found.append((len(lem), len(words), cite(words[0]),
                          cite(words[-1]), words[0].get("cite", ""), hits))
    found.sort(key=lambda r: (-r[0], r[1]))
    for n, size, a, b, urn, hits in found[:top]:
        work = "Iliad" if "tlg0012.tlg001" in urn else "Odyssey"
        print(f"{n} lemmas, {size} words  {work} {a}-{b}  {hits}")


# ------------------------------------------------------------------ WordNet

def parse_values(t):
    vals, i, n = [], 0, len(t)
    while i < n:
        c = t[i]
        if c == "'":
            i += 1
            buf = []
            while i < n:
                c = t[i]
                if c == "\\" and i + 1 < n:
                    buf.append(t[i + 1])
                    i += 2
                    continue
                if c == "'":
                    if i + 1 < n and t[i + 1] == "'":
                        buf.append("'")
                        i += 2
                        continue
                    break
                buf.append(c)
                i += 1
            vals.append("".join(buf))
            i += 1
        elif t.startswith("NULL", i):
            vals.append(None)
            i += 4
        elif c in ", ":
            i += 1
        else:
            j = i
            while j < n and t[j] != ",":
                j += 1
            vals.append(t[i:j].strip())
            i = j
    return vals


def iter_rows(path, table):
    prefix = f"INSERT INTO {table} VALUES ("
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith(prefix):
                yield parse_values(line[len(prefix):].rstrip().rstrip(";")[:-1])


def cmd_extract(exp):
    wanted = {}
    for l in exp.lemmas:
        for form in l["agwn_forms"]:
            wanted.setdefault(nfc(form), []).append(l["lemma"])
    links = collections.defaultdict(list)
    for lemma, *ids in iter_rows(DUMP / "greek_index.sql", "greek_index"):
        key = nfc(lemma)
        for lookup in wanted.get(key, []):
            for pos, val in zip("nvar", ids):
                for sid in (val or "").split():
                    links[lookup].append((pos, sid, key))
    needed = {sid for v in links.values() for _, sid, _ in v}
    syn = {}
    for sid, words, _phrase, gloss in iter_rows(DUMP / "english_synset.sql",
                                                "english_synset"):
        if sid in needed:
            syn[sid] = (" ".join((words or "").split()),
                        re.sub(r'\\+"', '"', gloss or ""))
    exp.wn.mkdir(exist_ok=True)
    rows = []
    for l in exp.lemmas:
        seen = set()
        for pos, sid, form in links.get(l["lemma"], []):
            if sid in seen:
                continue
            seen.add(sid)
            words, gloss = syn.get(sid, ("", ""))
            rows.append({"greek_lemma": l["lemma"], "matched_form": form,
                         "pos": pos, "synset_id": sid,
                         "english_words": words, "gloss": gloss})
        forms = sorted({f for _, _, f in links.get(l["lemma"], [])})
        print(f"{l['lemma']:14} {len(seen):5} synsets  "
              f"matched: {', '.join(forms) or '—'}")
    write_csv(exp.raw, rows, ["greek_lemma", "matched_form", "pos",
                              "synset_id", "english_words", "gloss"])
    print(f"{len(rows)} synsets")


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower())).strip()


def resolve_synset(wn, words, gloss, pos):
    wn_pos = {"n": [wn.NOUN], "v": [wn.VERB], "a": [wn.ADJ, wn.ADJ_SAT],
              "r": [wn.ADV]}[pos]
    cands = {}
    for w in words:
        for s in wn.synsets(w):
            if s.pos() in wn_pos:
                cands[s.name()] = s
    cands = list(cands.values())
    if not cands:
        return None, "unresolved"
    target = norm(re.split(r';\s*"|:\s*"', gloss)[0]) if gloss else ""
    wset = {w.lower() for w in words}

    def overlap(s):
        lem = {l.name().lower() for l in s.lemmas()}
        return len(lem & wset) / len(lem | wset)

    def sim(s):
        return difflib.SequenceMatcher(None, target,
                                       norm(s.definition())).ratio()

    if target:
        for s in cands:
            if norm(s.definition()) == target:
                return s, "exact_gloss"
        best = max(cands, key=sim)
        if sim(best) >= 0.6:
            return best, "gloss+lemma"
        return max(cands, key=lambda s: (overlap(s), sim(s))), "lemma_set"
    return max(cands, key=overlap), "lemma_set"


def cmd_resolve(exp):
    from nltk.corpus import wordnet as wn
    translit = {l["lemma"]: l["translit"] for l in exp.lemmas}
    flags = {(r["greek_lemma"], r["synset_id"]): r
             for r in read_csv(exp.flags)}
    raw = read_csv(exp.raw)
    present = {(r["greek_lemma"], r["synset_id"]) for r in raw}
    stray = [k for k in flags if k not in present]
    if stray:
        sys.exit(f"flags for synsets not in the extraction: {stray}")
    by = collections.defaultdict(list)
    for r in raw:
        f = flags.get((r["greek_lemma"], r["synset_id"]))
        by[r["greek_lemma"]].append((r, f["sense_flag"] if f else "noise",
                                     f["reason"] if f else ""))
    out = []
    for l in exp.lemmas:
        for r, flag, reason in sorted(by[l["lemma"]],
                                      key=lambda x: FLAG_ORDER[x[1]]):
            sid = r["synset_id"]
            pos, off = sid.split("#")
            words = r["english_words"].split()
            s, match = resolve_synset(wn, words, r["gloss"], pos)
            key = ""
            if s:
                names = {x.name().lower(): x for x in s.lemmas()}
                key = next((names[w.lower()].key() for w in words
                            if w.lower() in names), s.lemmas()[0].key())
            out.append({
                "translit": translit[l["lemma"]], "greek_lemma": l["lemma"],
                "pos": r["pos"], "agwn_synset_id": sid,
                "english_words": r["english_words"], "agwn_gloss": r["gloss"],
                "pwn30_synset": s.name() if s else "",
                "pwn30_offset": f"{s.offset():08d}-{s.pos()}" if s else "",
                "sense_key": key, "id_match": match, "sense_flag": flag,
                "flag_reason": reason,
                "agwn_synset_url": "https://greekwordnet.chs.harvard.edu/api/"
                                   f"synsets/{pos}/{off}/",
                "pwn_url": ("https://en-word.net/lemma/" + urllib.parse.quote(
                    s.lemmas()[0].name())) if s else "",
            })
    write_csv(exp.full, out, list(out[0]))
    c = collections.Counter((r["sense_flag"]) for r in out)
    m = collections.Counter((r["id_match"]) for r in out)
    print(f"{len(out)} synsets; flags {dict(c)}; matches {dict(m)}")


# ------------------------------------------------------------------ links page

LINKS_CSS = """
:root{--ink:#1a1a17;--mut:#6a6a63;--line:#e2e0d8;--bg:#faf9f5;--card:#fff;--acc:#0f6e56;--coral:#993c1d;--warn:#a32d2d}
*{box-sizing:border-box}body{font-family:'Noto Sans',system-ui,sans-serif;color:var(--ink);background:var(--bg);margin:0;line-height:1.55;font-size:15px}
.wrap{max-width:1080px;margin:0 auto;padding:32px 20px 80px}h1{font-weight:600;font-size:26px;margin:0 0 4px}
.sub{color:var(--mut);margin:0 0 20px}
.bar{position:sticky;top:0;background:var(--bg);padding:12px 0;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;z-index:5;margin-bottom:8px}
.bar input[type=search]{font:inherit;padding:7px 11px;border:1px solid var(--line);border-radius:8px;min-width:200px;background:var(--card)}
.bar label{color:var(--mut);font-size:14px;display:flex;align-items:center;gap:5px;cursor:pointer}
details{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:12px 0;overflow:hidden}
summary{cursor:pointer;padding:14px 18px;font-size:17px;list-style:none;display:flex;flex-wrap:wrap;align-items:baseline;gap:10px}
summary::-webkit-details-marker{display:none}summary::before{content:'▸';color:var(--mut);font-size:13px;transition:.15s}
details[open] summary::before{transform:rotate(90deg)}
.lem{font-family:'Noto Serif',serif;font-weight:500;font-size:22px}.tr{color:var(--mut);font-style:italic}
.tag{font-size:11px;padding:2px 8px;border-radius:20px;font-weight:500}{tags}
.cnt{color:var(--mut);font-size:13px;margin-left:auto}
.wt{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:13.5px}
thead th{text-align:left;color:var(--mut);font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.03em;padding:8px 12px;border-top:1px solid var(--line);background:#f6f5f0}
td{padding:7px 12px;border-top:1px solid var(--line);vertical-align:top}tr.unres td{opacity:.55}tr.noise td{opacity:.6}
.gk{font-family:'Noto Serif',serif}a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}a.pwn{color:var(--coral)}
code{font-family:monospace;font-size:12px;color:var(--mut);background:#f1efe8;padding:1px 5px;border-radius:4px}
.m{font-size:11px;padding:1px 6px;border-radius:4px;background:#f1efe8;color:var(--mut)}.m.unresolved{background:#fcebeb;color:var(--warn)}
.f{font-size:11px;padding:1px 6px;border-radius:4px;font-weight:500}.f.core{background:#e1f5ee;color:var(--acc)}.f.plausible{background:#eeedfe;color:#534AB7}.f.noise{background:#f1efe8;color:var(--mut)}
.note{font-size:12px;color:var(--warn);padding:6px 18px 10px;margin:0}.rel{color:var(--mut);font-size:12.5px}.ext{font-size:10px;vertical-align:1px}
footer{color:var(--mut);font-size:12.5px;margin-top:40px;border-top:1px solid var(--line);padding-top:16px}
"""

LINKS_JS = """
const q=document.getElementById('q'),ro=document.getElementById('ro');
function role(){return document.querySelector('input[name=role]:checked').value}
function apply(){const t=q.value.trim().toLowerCase(),only=ro.checked,rl=role();
 document.querySelectorAll('details').forEach(d=>{const okRole=rl==='all'||d.dataset.role===rl;let shown=0;
  d.querySelectorAll('tbody tr').forEach(tr=>{const okT=!t||tr.dataset.txt.includes(t)||d.dataset.lemma.toLowerCase().includes(t);const okR=!only||tr.dataset.kept==='1';const vis=okRole&&okT&&okR;tr.style.display=vis?'':'none';if(vis)shown++;});
  d.style.display=(okRole&&(shown>0||(!t&&!only)))?'':'none';if(t&&shown>0)d.open=true;});}
q.addEventListener('input',apply);ro.addEventListener('change',apply);
document.querySelectorAll('input[name=role]').forEach(r=>r.addEventListener('change',apply));
"""


def tag_css(exp, palette, links):
    rules = []
    for i, (g, slug) in enumerate(exp.groups.items()):
        bg, fg = palette[i % len(palette)]
        rules.append(f".tag.{slug}{{background:{bg};color:{fg}}}")
    return "".join(rules)


def group_radios(exp):
    return "".join(f'<label><input type="radio" name="role" value="{s}"> '
                   f'{esc(g)}</label>' for g, s in exp.groups.items())


def agwn_lemma_url(form, pos):
    return ("https://greekwordnet.chs.harvard.edu/api/lemmas/"
            f"{urllib.parse.quote(form)}/{pos}/")


def cmd_links(exp):
    rows = read_csv(exp.full)
    lemmas = exp.lemma_rows()
    form = exp.agwn_form()
    by = collections.defaultdict(list)
    for r in rows:
        by[r["greek_lemma"]].append(r)
    n_res = sum(1 for r in rows if r["id_match"] != "unresolved")
    n_kept = sum(1 for r in rows if r["sense_flag"] != "noise")
    css = LINKS_CSS.replace("{tags}", tag_css(exp, TAG_LINKS, True))
    h = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         f'<title>{esc(exp.cfg["page_title"])} — WordNet links</title>',
         '<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
         '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@'
         '400;500;600&family=Noto+Serif:wght@400;500&display=swap" '
         'rel="stylesheet">', f'<style>{css}</style>',
         '</head><body><div class="wrap">',
         f'<h1>{esc(exp.title)} <span style="color:var(--mut);'
         'font-weight:400">· WordNet links</span></h1>',
         f'<p class="sub">{len(lemmas)} lemmata · {len(rows)} AGWN synsets · '
         f'{n_res} resolved to Princeton WordNet 3.0 · {n_kept} kept as core '
         'or plausible senses. Greek links → Ancient Greek WordNet; Princeton '
         'links → Open English WordNet (en-word.net).</p>',
         '<div class="bar"><input type="search" id="q" placeholder="filter by '
         'word or gloss…"><label><input type="checkbox" id="ro"> core &amp; '
         'plausible only</label><label><input type="radio" name="role" '
         'value="all" checked> all</label>' + group_radios(exp) + '</div>']
    for l in lemmas:
        lem, rs = l["greek_lemma"], by.get(l["greek_lemma"], [])
        g = exp.groups[l["group"]]
        res = sum(1 for r in rs if r["id_match"] != "unresolved")
        kept = sum(1 for r in rs if r["sense_flag"] != "noise")
        h.append(f'<details data-lemma="{esc(lem)} {esc(l["translit"])}" '
                 f'data-role="{g}">')
        h.append(f'<summary><span class="lem gk">{esc(lem)}</span> <span '
                 f'class="tr">{esc(l["translit"])}</span> <span class="tag {g}">'
                 f'{esc(l["group"])}</span> <span class="rel">{esc(l["pos"])}'
                 f'</span> <a href="{agwn_lemma_url(form[lem], l["pos"])}" '
                 'target="_blank" rel="noopener">AGWN entry<span class="ext">↗'
                 f'</span></a><span class="cnt">{len(rs)} synsets · {res} '
                 f'linked · {kept} kept</span></summary>')
        if not rs:
            h.append('<p class="note">⚠ In AGWN, but no synsets are linked to '
                     'this lemma.</p></details>')
            continue
        if form[lem] != lem:
            h.append(f'<p class="note" style="color:var(--mut)">AGWN spells '
                     f'this lemma {esc(form[lem])}.</p>')
        h.append('<div class="wt"><table><thead><tr><th>AGWN synset</th><th>'
                 'English</th><th>gloss</th><th>Open English WordNet</th><th>'
                 'sense key</th><th>match</th><th>sense</th></tr></thead>'
                 '<tbody>')
        for r in rs:
            txt = " ".join([lem, r["english_words"].replace("_", " "),
                            r["agwn_gloss"], r["pwn30_synset"]]).lower()
            cls = (["unres"] if r["id_match"] == "unresolved" else []) + \
                (["noise"] if r["sense_flag"] == "noise" else [])
            pwn = (f'<a href="{esc(r["pwn_url"])}" target="_blank" '
                   f'rel="noopener" class="pwn" title="opens '
                   f'{esc(r["pwn30_synset"])} on en-word.net">'
                   f'{esc(r["pwn30_synset"])}<span class="ext">↗</span></a>'
                   if r["pwn30_synset"] else "no PWN 3.0")
            title = f' title="{esc(r["flag_reason"])}"' \
                if r["flag_reason"] else ""
            h.append(
                f'<tr class="{" ".join(cls)}" data-txt="{esc(txt)}" '
                f'data-kept="{0 if r["sense_flag"] == "noise" else 1}"><td>'
                f'<a href="{esc(r["agwn_synset_url"])}" target="_blank" '
                f'rel="noopener" class="gk">{esc(r["agwn_synset_id"])}<span '
                f'class="ext">↗</span></a></td><td>'
                f'{esc(r["english_words"].replace("_", " "))}</td><td>'
                f'{esc(r["agwn_gloss"])}</td><td>{pwn}</td><td>'
                + (f'<code>{esc(r["sense_key"])}</code>' if r["sense_key"]
                   else "") +
                f'</td><td><span class="m {esc(r["id_match"])}">'
                f'{esc(r["id_match"])}</span></td><td><span class="f '
                f'{esc(r["sense_flag"])}"{title}>{esc(r["sense_flag"])}</span>'
                '</td></tr>')
        h.append('</tbody></table></div></details>')
    h.append('<footer>AGWN = Ancient Greek WordNet (Center for Hellenic '
             'Studies); synsets from the AGWN database dump (GitHub '
             '<code>jcuenod/greekwordnet</code>). PWN 3.0 matches made with '
             'NLTK WordNet 3.0. Sense flags: core / plausible / noise, judged '
             'by Claude Opus 5.5 — hover a flag for its reason. Princeton links '
             'resolve through Open English WordNet (<code>en-word.net</code>); '
             'links open the lemma page, use the gloss and <code>sense key'
             '</code> to pick the exact sense.</footer>')
    h.append(f'<script>{LINKS_JS}</script>')
    h.append('</div></body></html>')
    out = exp.wn / f"{exp.slug}_field_links.html"
    out.write_text("\n".join(h) + "\n", encoding="utf-8")
    print(f"{out.name}: {len(rows)} rows")


# ------------------------------------------------------------------ render

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@'
         '400;500;600&family=Noto+Serif:wght@400;500;600&display=swap" '
         'rel="stylesheet">')

FRAMENET_CSS = """
:root{--ink:#1a1a17;--mut:#6a6a63;--line:#e2e0d8;--bg:#faf9f5;--card:#fff;--acc:#534AB7;--teal:#0f6e56;--coral:#993c1d;--new:#7F77DD}
*{box-sizing:border-box}body{font-family:'Noto Sans',system-ui,sans-serif;color:var(--ink);background:var(--bg);margin:0;line-height:1.55;font-size:15px}
.wrap{max-width:980px;margin:0 auto;padding:32px 20px 80px}h1{font-weight:600;font-size:26px;margin:0 0 4px}h2{font-weight:600;font-size:20px;margin:34px 0 10px}
.sub{color:var(--mut);margin:0 0 8px}
.prov{background:#eeedfe;border:0.5px solid #cecbf6;border-radius:10px;padding:10px 14px;font-size:13px;color:#3c3489;margin:14px 0 22px}
.bar{position:sticky;top:0;background:var(--bg);padding:12px 0;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;z-index:5;margin-bottom:8px}
.bar input[type=search]{font:inherit;padding:7px 11px;border:1px solid var(--line);border-radius:8px;min-width:200px;background:var(--card)}
.bar label{color:var(--mut);font-size:14px;display:flex;align-items:center;gap:5px;cursor:pointer}
table.sum{width:100%;border-collapse:collapse;font-size:14px;margin:6px 0 10px}
table.sum td,table.sum th{text-align:left;padding:6px 10px;border-top:1px solid var(--line)}
table.sum th{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.03em}
details{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:10px 0;overflow:hidden}
summary{cursor:pointer;padding:13px 18px;list-style:none;display:flex;flex-wrap:wrap;align-items:baseline;gap:10px}
summary::-webkit-details-marker{display:none}summary::before{content:'▸';color:var(--mut);font-size:13px}details[open] summary::before{content:'▾'}
.lem{font-family:'Noto Serif',serif;font-weight:500;font-size:22px}.tr{color:var(--mut);font-style:italic}
.tag{font-size:11px;padding:2px 8px;border-radius:20px;font-weight:500}{tags}
.pos{color:var(--mut);font-size:12.5px}.aright{margin-left:auto}
.asg{padding:6px 18px 4px}.asg table{width:100%;border-collapse:collapse;font-size:13.5px}
.asg td{padding:6px 10px;border-top:1px solid var(--line);vertical-align:top}
.role-p{font-weight:500;color:var(--acc)}.role-a{color:var(--mut)}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}a.ext::after{content:' ↗';font-size:10px}
.new{color:var(--new);font-weight:500}
.fes{font-size:12.5px;color:var(--mut);padding:2px 18px 6px}
.nt{font-size:12.5px;color:var(--mut);padding:0 18px 8px}
.wn{padding:4px 18px 14px;font-size:13px;border-top:1px dashed var(--line);margin-top:2px}
.wnh{font-weight:500;color:var(--teal)}
.chip{display:inline-block;background:#f1efe8;color:#5f5e5a;border-radius:12px;padding:1px 9px;margin:3px 3px 0 0;font-size:12.5px;border:0.5px solid var(--line)}
.chip.sh{background:#e1f5ee;color:var(--teal);border-color:#9fe1cb}
.chip:hover{text-decoration:none;border-color:var(--teal)}
.framecard{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--new);border-radius:0 12px 12px 0;padding:16px 20px;margin:14px 0}
.framecard h3{margin:0 0 6px;font-size:18px}
.fetab{width:100%;border-collapse:collapse;font-size:13.5px;margin:8px 0}
.fetab td{padding:5px 10px;border-top:1px solid var(--line);vertical-align:top}.fetab .fen{font-weight:500;white-space:nowrap}
.ex{background:#faf9f5;border-radius:8px;padding:8px 12px;margin:6px 0;font-size:13.5px}
.fe{background:#eeedfe;border-radius:4px;padding:0 3px}.fe sub{color:var(--acc);font-size:9px;vertical-align:2px;margin-left:1px}
code{font-family:monospace;font-size:12px;background:#f1efe8;padding:1px 5px;border-radius:4px}
footer{color:var(--mut);font-size:12.5px;margin-top:40px;border-top:1px solid var(--line);padding-top:16px}
"""

FILTER_JS = """
const q=document.getElementById('q');
function role(){return document.querySelector('input[name=role]:checked').value}
function apply(){const t=q.value.trim().toLowerCase(),rl=role();
 document.querySelectorAll('details').forEach(d=>{const okR=rl==='all'||d.dataset.role===rl;const okT=!t||d.dataset.lemma.toLowerCase().includes(t)||d.dataset.txt.includes(t);d.style.display=(okR&&okT)?'':'none';if(t&&okR&&okT)d.open=true;});}
q.addEventListener('input',apply);document.querySelectorAll('input[name=role]').forEach(r=>r.addEventListener('change',apply));
"""

PASSAGE_CSS = """
:root{--ink:#1a1a17;--mut:#6a6a63;--line:#e2e0d8;--bg:#faf9f5;--card:#fff;--acc:#534AB7;--teal:#0f6e56}
*{box-sizing:border-box}body{font-family:'Noto Sans',system-ui,sans-serif;color:var(--ink);background:var(--bg);margin:0;line-height:1.55;font-size:15px}
.wrap{max-width:820px;margin:0 auto;padding:32px 20px 70px}h1{font-weight:600;font-size:23px;margin:0 0 4px}
.sub{color:var(--mut);margin:0 0 18px;font-size:14px}
.passage{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:20px 22px;margin-bottom:8px}
.grk{font-family:'Noto Serif',serif;font-size:22px;line-height:1.85}
.tg{font-weight:600}
.tr{color:var(--mut);font-style:italic;margin-top:10px;font-size:15px}
.src{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em;font-weight:500;margin-bottom:8px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 20px;margin:12px 0}
.hd{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;margin-bottom:4px}
.lu{font-family:'Noto Serif',serif;font-weight:600;font-size:18px}
.fr{background:#eeedfe;color:var(--acc);border-radius:6px;padding:1px 9px;font-size:13px;font-weight:500}
a.ext:hover .fr::after{content:' ↗';font-size:10px}
.badge{font-size:11px;color:var(--teal);background:#e1f5ee;border-radius:12px;padding:1px 8px}
table{width:100%;border-collapse:collapse;font-size:14px;margin-top:6px}
td{padding:5px 10px;border-top:1px solid #f0eee7;vertical-align:top}
.role{font-weight:500;color:var(--teal);white-space:nowrap}.fev{font-family:'Noto Serif',serif}
.ni{color:var(--mut);font-style:italic;font-family:'Noto Sans'}
.off{color:#b3b1a8;font-size:11px;font-family:monospace}
.note{font-size:13px;color:#5a5852;background:#faf9f5;border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin-top:16px}
code{font-family:monospace;font-size:12px;background:#f1efe8;padding:1px 5px;border-radius:4px}
footer{color:var(--mut);font-size:12px;margin-top:26px;border-top:1px solid var(--line);padding-top:14px}
"""

COLOURS = ["#993c1d", "#0f6e56", "#8a6d0b", "#534AB7", "#9c2b6b",
           "#1d5f99", "#5f7a1d", "#b5522b", "#2b8a8a", "#7a3fa0"]
NI = {"CNI": "constructional null (pro-drop)",
      "DNI": "definite null (understood)", "INI": "indefinite null"}


def frame_link(name, status, proposed):
    if status.startswith("PROPOSED") or name in proposed:
        return (f'<a href="#frame-{esc(name)}">{esc(name)}</a> '
                '<span class="new">🆕</span>')
    return (f'<a href="{FN_URL}{esc(name)}" target="_blank" class="ext">'
            f'{esc(name)}</a>')


def example_html(text, lus):
    out = re.sub(r"\[([^\]|]+)\|([^\]]+)\]",
                 r'<span class="fe">\1<sub>\2</sub></span>', esc(text))
    for lu in sorted(lus, key=len, reverse=True):
        out = out.replace(esc(lu), f'<b class="tgt">{esc(lu)}</b>')
    return out


def chips(rows, shared):
    seen, out = set(), []
    for r in rows:
        if not r["pwn30_synset"] or r["pwn30_synset"] in seen:
            continue
        seen.add(r["pwn30_synset"])
        word = r["pwn30_synset"].split(".")[0].replace("_", " ")
        cls = "chip sh" if r["pwn30_synset"] in shared else "chip"
        out.append(f'<a class="{cls}" href="{esc(r["pwn_url"])}" '
                   f'target="_blank" title="{esc(r["pwn30_synset"])} · '
                   f'{esc(r["sense_flag"])}">{esc(word)}</a>')
    return " ".join(out)


def wordnet_by_lemma(exp):
    by = collections.defaultdict(list)
    for r in read_csv(exp.full):
        by[r["greek_lemma"]].append(r)
    return by


def render_framenet(exp, run, dest, with_wn):
    lemmas = exp.lemma_rows()
    form = exp.agwn_form()
    proposed = json.loads((run / "proposed_frames.json").read_text(
        encoding="utf-8"))
    pnames = {p["name"] for p in proposed}
    by_lemma = collections.defaultdict(list)
    for r in read_csv(run / "frame_assignments.csv"):
        by_lemma[r["greek_lemma"]].append(r)
    wn = wordnet_by_lemma(exp) if with_wn else {}
    kept = {l: [r for r in rows if r["sense_flag"] in ("core", "plausible")]
            for l, rows in wn.items()}
    concept_lemmas = collections.Counter()
    for rows in kept.values():
        for s in {r["pwn30_synset"] for r in rows if r["pwn30_synset"]}:
            concept_lemmas[s] += 1
    shared = {s for s, n in concept_lemmas.items() if n > 1}
    n_existing = sum(1 for l in lemmas for r in by_lemma[l["greek_lemma"]]
                     if r["assignment"] == "primary"
                     and r["frame_status"].startswith("existing"))
    n_new = len(lemmas) - n_existing
    sense_src = "LSJ + Ancient Greek WordNet" if with_wn else \
        "LSJ glosses of the cluster (no WordNet)"
    wn_sub = (" — with each lemma’s Ancient Greek WordNet senses (core and "
              "plausible) linked to Princeton WordNet 3.0") if with_wn else ""
    css = FRAMENET_CSS.replace("{tags}", tag_css(exp, TAG_FN, False))
    h = [f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
         f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
         f'<title>{esc(exp.cfg["page_title"])} — FrameNet</title>\n{FONTS}\n'
         f'<style>{css}</style>\n</head><body><div class="wrap">\n'
         f'<h1>{esc(exp.title)} <span style="color:var(--mut);'
         'font-weight:400">· FrameNet layer</span></h1>\n'
         f'<p class="sub">{len(lemmas)} Homeric lemmata from gloss-embedding '
         f'cluster {exp.cfg["cluster_id"]} mapped to FrameNet frames — '
         f'{n_existing} to existing Berkeley FrameNet 1.7 frames, {n_new} to '
         f'newly proposed frames{wn_sub}. Run: <b>'
         f'{"with" if with_wn else "without"} WordNet</b>.</p>\n'
         '<div class="prov"><b>Provenance.</b> Frames = Berkeley FrameNet '
         '(English); links open the frame on <code>framenet.icsi.berkeley.edu'
         '</code>. Existing frames and frame elements checked against the '
         f'FrameNet 1.7 data. Greek senses = {sense_src}. Word-to-frame '
         'pairings are analytical proposals by Claude Opus 5.5. Frames marked '
         '<span class="new">🆕</span> are proposed here.</div>\n'
         '<h2>Primary frame per lemma</h2><table class="sum"><tr><th>Lemma'
         '</th><th>Primary frame</th><th>Status</th></tr>']
    for l in lemmas:
        p = next(r for r in by_lemma[l["greek_lemma"]]
                 if r["assignment"] == "primary")
        st = "proposed" if p["frame_status"].startswith("PROPOSED") \
            else "existing"
        h.append(f'<tr><td class="lem" style="font-size:16px">'
                 f'{esc(l["greek_lemma"])} <span class="tr" style="font-size:'
                 f'13px">{esc(l["translit"])}</span></td><td>'
                 f'{frame_link(p["frame"], p["frame_status"], pnames)}</td>'
                 f'<td class="pos">{st}</td></tr>')
    h.append('</table>\n<div class="bar"><input type="search" id="q" '
             'placeholder="filter by word, frame or concept…">'
             '<label><input type="radio" name="role" value="all" checked> all'
             '</label>' + group_radios(exp) + '</div>\n'
             '<h2>Frame assignments' + (' &amp; WordNet concepts' if with_wn
                                        else '') + ' by lemma</h2>')
    for l in lemmas:
        lem = l["greek_lemma"]
        rows = sorted(by_lemma[lem], key=lambda r: r["assignment"] != "primary")
        g = exp.groups[l["group"]]
        txt = " ".join(f'{r["frame"]} {r["word_sense"]}' for r in rows)
        if with_wn:
            txt += " " + " ".join(r["english_words"].replace("_", " ")
                                  for r in kept.get(lem, []))
        h.append(f'<details data-lemma="{esc(lem)} {esc(l["translit"])}" '
                 f'data-role="{g}" data-txt="{esc(txt.lower())}">\n'
                 f'<summary><span class="lem">{esc(lem)}</span> <span '
                 f'class="tr">{esc(l["translit"])}</span> <span class="tag '
                 f'{g}">{esc(l["group"])}</span> <span class="pos">'
                 f'{esc(l["pos"])}</span> <a class="aright ext" href="'
                 f'{agwn_lemma_url(form[lem], l["pos"])}" target="_blank">'
                 'AGWN entry</a></summary>\n<div class="asg"><table>')
        for r in rows:
            cls, lab = (("role-p", "primary") if r["assignment"] == "primary"
                        else ("role-a", "alt"))
            h.append(f'<tr><td class="{cls}">{lab}</td><td>'
                     f'{frame_link(r["frame"], r["frame_status"], pnames)}'
                     f'</td><td><i>{esc(r["word_sense"])}</i></td><td '
                     f'class="pos">{esc(r["participant_to_FE_mapping"])}</td>'
                     '</tr>')
        p = rows[0]
        h.append(f'</table></div>\n<div class="fes"><b>Core FEs of '
                 f'{esc(p["frame"])}:</b> {esc(p["frame_core_FEs"])}</div>')
        notes = [f'{r["frame"]}: {r["note"]}' for r in rows if r["note"]]
        if notes:
            h.append('<div class="nt">' + "<br>".join(esc(n) for n in notes)
                     + '</div>')
        if with_wn:
            all_rows, k = wn.get(lem, []), kept.get(lem, [])
            res = sum(1 for r in all_rows if r["id_match"] != "unresolved")
            if all_rows:
                h.append(f'<div class="wn"><span class="wnh">Princeton WordNet'
                         f'</span> <span class="pos">({len(k)} of '
                         f'{len(all_rows)} AGWN synsets kept as core or '
                         f'plausible · {res} resolved to PWN 3.0 · links → '
                         f'Open English WordNet)</span><br>{chips(k, shared)}'
                         '</div>')
            else:
                h.append('<div class="wn"><span class="wnh">Princeton WordNet'
                         '</span> <span class="pos">(in AGWN, but no synsets '
                         'linked)</span></div>')
        h.append('</details>')
    if proposed:
        h.append('<h2>Proposed frames (full definitions)</h2>')
    for p in proposed:
        rel = []
        if p.get("inherits"):
            rel.append("Inherits from " + " and ".join(
                f'<a href="{FN_URL}{esc(x)}" target="_blank">{esc(x)}</a>'
                for x in p["inherits"]))
        if p.get("uses"):
            rel.append("uses " + " and ".join(
                f'<a href="{FN_URL}{esc(x)}" target="_blank">{esc(x)}</a>'
                for x in p["uses"]))
        h.append(f'<div class="framecard" id="frame-{esc(p["name"])}"><h3>'
                 f'<span class="new">🆕</span> {esc(p["name"])}</h3><p>'
                 f'{esc(p["definition"])}</p>'
                 + (f'<p class="pos">{"; ".join(rel)}.</p>' if rel else ""))
        for title, key in (("Core frame elements", "core_FEs"),
                           ("Selected non-core FEs", "noncore_FEs")):
            if p.get(key):
                h.append(f'<b style="font-size:13px">{title}</b><table '
                         'class="fetab">' + "".join(
                             f'<tr><td class="fen">{esc(fe["name"])}</td><td>'
                             f'{esc(fe["definition"])}</td></tr>'
                             for fe in p[key]) + '</table>')
        h.append('<b style="font-size:13px">Lexical units</b><table '
                 'class="fetab">' + "".join(
                     f'<tr><td class="fen" style="font-family:Noto Serif,serif">'
                     f'{esc(u["lemma"])}</td><td class="pos">{esc(u["pos"])}'
                     f'</td><td>{esc(u["gloss"])}</td></tr>'
                     for u in p["lexical_units"]) + '</table>')
        if p.get("examples"):
            h.append('<b style="font-size:13px">Annotated examples</b>')
            lus = [u["lemma"] for u in p["lexical_units"]]
            for ex in p["examples"]:
                note = f' <span class="pos">({esc(ex["note"])})</span>' \
                    if ex.get("note") else ""
                h.append(f'<div class="ex">{example_html(ex["text"], lus)}'
                         f'{note}</div>')
        h.append('</div>')
    foot = 'Existing frames link to Berkeley FrameNet. '
    if with_wn:
        foot += ('Princeton WordNet concepts link to Open English WordNet '
                 '(<code>en-word.net</code>); <span class="chip sh" '
                 'style="margin:0">teal chips</span> are concepts shared by two '
                 'or more lemmata in this field; hover a chip for its PWN 3.0 '
                 'synset and flag. ')
    foot += 'Greek lemma links open the Ancient Greek WordNet API.'
    h.append(f'<footer>{foot}</footer>\n<script>{FILTER_JS}</script>\n'
             '</div></body></html>\n')
    (dest / f"{exp.slug}_framenet.html").write_text("\n".join(h),
                                                     encoding="utf-8")


def render_notes(exp, run, dest, with_wn):
    lemmas = exp.lemma_rows()
    form = exp.agwn_form()
    senses = {r["greek_lemma"]: r["sense"]
              for r in read_csv(run / "lemma_senses.csv")}
    by_lemma = collections.defaultdict(list)
    for r in read_csv(run / "frame_assignments.csv"):
        by_lemma[r["greek_lemma"]].append(r)
    wn = wordnet_by_lemma(exp) if with_wn else {}
    groups = collections.defaultdict(list)
    for l in lemmas:
        groups[l["group"]].append(l["greek_lemma"])
    (dest / "Lemmata").mkdir(exist_ok=True)
    for l in lemmas:
        lem = l["greek_lemma"]
        rows = sorted(by_lemma[lem], key=lambda r: r["assignment"] != "primary")
        prim = rows[0]
        front = [f"lemma: {lem}", f"translit: {l['translit']}",
                 f"pos: {l['pos']}", f"group: {l['group']}",
                 f'sense: "{senses.get(lem, "")}"',
                 f"homer_count: {l['homer_count']}"]
        if with_wn:
            all_rows = wn.get(lem, [])
            front += [f"agwn_synsets: {len(all_rows)}",
                      "agwn_kept: " + str(sum(
                          1 for r in all_rows
                          if r["sense_flag"] in ("core", "plausible")))]
        front += [f"primary_frame: {prim['frame']}",
                  f"tags: [{exp.slug}/lemma, {exp.slug}/"
                  f"{exp.groups[l['group']]}]",
                  f"aliases: [{l['translit']}]"]
        md = ["---", *front, "---", "", f"# {lem}  ·  *{l['translit']}*", "",
              "> [!abstract] Sense (LSJ)", f"> {senses.get(lem, '')}", "",
              "## FrameNet",
              f"- **Primary frame:** [[{prim['frame']}]] — "
              f"*{prim['word_sense']}*"]
        for r in rows[1:]:
            md.append(f"- Alternative: [[{r['frame']}]] — *{r['word_sense']}*")
        if with_wn:
            all_rows = wn.get(lem, [])
            k = [r for r in all_rows if r["sense_flag"] in ("core", "plausible")]
            md += ["", "## WordNet"]
            if all_rows:
                md.append(f"- {len(k)} of {len(all_rows)} AGWN synsets kept "
                          "as core or plausible.")
                for r in k:
                    md.append(f"- {r['sense_flag']}: "
                              f"{r['english_words'].replace('_', ' ')} "
                              f"({r['pwn30_synset'] or r['agwn_synset_id']})")
            else:
                md.append("- In AGWN, but no synsets linked.")
            md.append(f"- [Ancient Greek WordNet entry]"
                      f"({agwn_lemma_url(form[lem], l['pos'])})")
        others = [x for x in groups[l["group"]] if x != lem]
        md += ["", "## Related lemmata", ", ".join(f"[[{x}]]" for x in others),
               "", "## References",
               f"- [Logeion (LSJ etc.)](https://logeion.uchicago.edu/"
               f"{urllib.parse.quote(lem)})", ""]
        (dest / "Lemmata" / f"{lem}.md").write_text("\n".join(md),
                                                    encoding="utf-8")


def passage_slug(source):
    m = re.search(r"Homer, (\w+) (\d+)\.(\d+)", source)
    return f"{m.group(1).lower()}_{m.group(2)}_{m.group(3)}_framenet"


def passage_xml(doc, s):
    work = re.search(r"Homer, (\w+)", s["source"]).group(1)
    x = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<!-- FrameNet-style fulltext annotation (approximates the Berkeley '
         'FrameNet annotation schema).',
         f'     Passage: {s["source"]} (public-domain text). Annotation: '
         'illustrative proposal, using only EXISTING FrameNet 1.7 frames. '
         'Offsets are 0-based character positions, end inclusive. -->',
         '<fullTextAnnotation>',
         f'  <header><corpus name="{esc(doc["corpus"])}"><document '
         f'name="{work}"/></corpus></header>',
         f'  <sentence ID="1" source="{esc(s["source"])}">',
         f'    <text>{esc(s["text"])}</text>']
    for a in s["annotationSets"]:
        x.append(f'    <annotationSet ID="{a["id"]}" luName="{esc(a["luName"])}"'
                 f' frameName="{esc(a["frameName"])}" status="proposed">')
        t = a["target"]
        x += ['      <layer name="Target" rank="1">',
              f'        <label name="Target" start="{t["start"]}" '
              f'end="{t["end"]}"/>', '      </layer>',
              '      <layer name="FE" rank="1">']
        for fe in a["FEs"]:
            if "start" in fe:
                x.append(f'        <label name="{esc(fe["name"])}" '
                         f'start="{fe["start"]}" end="{fe["end"]}"/>')
            else:
                x.append(f'        <label name="{esc(fe["name"])}" '
                         f'itype="{esc(fe["itype"])}"/>')
        x += ['      </layer>', '    </annotationSet>']
    x += ['  </sentence>', '</fullTextAnnotation>', '']
    return "\n".join(x)


def passage_html(doc, s):
    text, sets = s["text"], s["annotationSets"]
    colour = {}
    for a in sets:
        colour.setdefault(a["frameName"], COLOURS[len(colour) % len(COLOURS)])
    out, pos = [], 0
    for st, en, a in sorted(((a["target"]["start"], a["target"]["end"], a)
                             for a in sets), key=lambda m: m[0]):
        if st < pos:
            continue
        out.append(esc(text[pos:st]))
        out.append(f'<b class="tg" style="color:{colour[a["frameName"]]}" '
                   f'title="{esc(a["frameName"])}">{esc(text[st:en + 1])}</b>')
        pos = en + 1
    out.append(esc(text[pos:]))
    src = s["source"].replace("-", "–")
    short = src.replace("Homer, ", "")
    h = [f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
         f'<meta name="viewport" content="width=device-width,initial-scale=1">'
         f'\n<title>{esc(short)} — FrameNet annotation</title>\n{FONTS}\n'
         f'<style>{PASSAGE_CSS}</style>\n</head><body><div class="wrap">\n'
         f'<h1>{esc(short)} <span style="color:var(--mut);font-weight:400">· '
         'FrameNet annotation</span></h1>\n'
         '<p class="sub">Annotated with <b>existing</b> Berkeley FrameNet 1.7 '
         'frames only. Colours mark frame-evoking targets.</p>\n'
         f'<div class="passage"><div class="src">{esc(src)}</div><div '
         f'class="grk">{"".join(out)}</div>\n<div class="tr">"'
         f'{esc(s.get("translation", ""))}"</div></div>']
    for a in sets:
        t = a["target"]
        h.append(f'<div class="card"><div class="hd"><span class="lu">'
                 f'{esc(a["luName"].rsplit(".", 1)[0])}</span><a class="ext" '
                 f'target="_blank" href="{FN_URL}{esc(a["frameName"])}"><span '
                 f'class="fr">{esc(a["frameName"])}</span></a><span '
                 f'class="badge">extant</span><span class="off" style="margin-'
                 f'left:auto">target @ {t["start"]}–{t["end"]}</span></div>'
                 '\n<table>')
        for fe in a["FEs"]:
            if "start" in fe:
                h.append(f'<tr><td class="role">{esc(fe["name"])}</td><td '
                         f'class="fev">{esc(fe["text"])} <span class="off">@ '
                         f'{fe["start"]}–{fe["end"]}</span></td></tr>')
            else:
                h.append(f'<tr><td class="role">{esc(fe["name"])}</td><td '
                         f'class="ni">— {esc(fe["itype"])}: '
                         f'{esc(NI.get(fe["itype"], ""))}</td></tr>')
        h.append('</table></div>')
    cav = doc["provenance"].get("caveats", [])
    if cav:
        h.append('<div class="note">' + "<br>".join(esc(c) for c in cav)
                 + '</div>')
    h.append('<footer>Text is public-domain (Homer). Annotation is an '
             'illustrative proposal by Claude Opus 5.5; verify orthography '
             'against a critical edition (OCT / Teubner). Offsets are 0-based '
             'character positions (end inclusive), matching the companion XML. '
             'NI = null instantiation (FE understood but not overtly '
             'expressed).</footer>\n</div></body></html>\n')
    return "\n".join(h)


def render_passages(exp, run, dest):
    doc = json.loads((run / "passage_annotations.json").read_text(
        encoding="utf-8"))
    dest.mkdir(parents=True, exist_ok=True)
    for s in doc["sentences"]:
        slug = passage_slug(s["source"])
        single = {k: v for k, v in doc.items() if k != "sentences"}
        single["provenance"] = dict(doc["provenance"])
        single["provenance"]["text"] = f'public-domain ({s["source"]})'
        single["sentences"] = [dict(s, id=1)]
        (dest / f"{slug}.json").write_text(
            json.dumps(single, ensure_ascii=False, indent=2), encoding="utf-8")
        (dest / f"{slug}.xml").write_text(passage_xml(doc, s), encoding="utf-8")
        (dest / f"{slug}.html").write_text(passage_html(doc, s),
                                           encoding="utf-8")


def cmd_render(exp, run, name, with_wn):
    run = Path(run)
    out = exp.dir / name
    fnd = out / "FrameNet"
    fnd.mkdir(parents=True, exist_ok=True)
    shutil.copy(run / "frame_assignments.csv",
                fnd / f"{exp.slug}_field_framenet_full.csv")
    shutil.copy(run / "proposed_frames.json", fnd / "proposed_frames.json")
    shutil.copy(run / "lemma_senses.csv", fnd / "lemma_senses.csv")
    shutil.copy(run / "method_notes.md", out / "method_notes.md")
    render_framenet(exp, run, fnd, with_wn)
    render_notes(exp, run, fnd, with_wn)
    render_passages(exp, run, out / exp.examples)
    print(f"rendered {name}")


# ------------------------------------------------------------------ compare

def frames_of(rows):
    prim = next((r["frame"] for r in rows if r["assignment"] == "primary"), "")
    return prim, {r["frame"] for r in rows}


def by_lemma(rows):
    d = collections.defaultdict(list)
    for r in rows:
        d[r["greek_lemma"]].append(r)
    return d


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 1.0


def load_run(exp, name):
    d = exp.dir / name
    asg = by_lemma(read_csv(d / "FrameNet" /
                            f"{exp.slug}_field_framenet_full.csv"))
    prop = json.loads((d / "FrameNet" / "proposed_frames.json").read_text(
        encoding="utf-8"))
    passages = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                ["sentences"][0]
                for p in sorted((d / exp.examples).glob("*.json"))}
    return asg, prop, passages


def sets_by_target(sentence):
    return {(a["target"]["start"], a["target"]["end"]): a
            for a in sentence["annotationSets"]}


def fe_names(a):
    return {fe["name"] for fe in a["FEs"]}


def cmd_compare(exp, original_csv, original_json):
    out = exp.dir / "comparison"
    out.mkdir(exist_ok=True)
    lemmas = exp.lemma_rows()
    A, propA, pasA = load_run(exp, "A_without_wordnet")
    B, propB, pasB = load_run(exp, "B_with_wordnet")
    original = by_lemma(read_csv(original_csv))
    original_form = {bare(nfc(l)): l for l in original}
    md = ["# Comparison: run A (without WordNet) vs. run B (with WordNet)", ""]
    rows, same_prim, jac = [], 0, []
    for l in lemmas:
        lem = l["greek_lemma"]
        pa, fa = frames_of(A[lem])
        pb, fb = frames_of(B[lem])
        bf = original_form.get(bare(nfc(lem)))
        pz, fz = frames_of(original[bf]) if bf else ("", set())
        same_prim += pa == pb
        jac.append(jaccard(fa, fb))
        rows.append({
            "greek_lemma": lem, "group": l["group"],
            "A_primary": pa, "B_primary": pb, "same_primary": pa == pb,
            "A_frames": "; ".join(sorted(fa)), "B_frames": "; ".join(sorted(fb)),
            "only_A": "; ".join(sorted(fa - fb)),
            "only_B": "; ".join(sorted(fb - fa)),
            "frame_overlap": f"{jaccard(fa, fb):.2f}",
            "original_primary": pz, "original_frames": "; ".join(sorted(fz)),
        })
    write_csv(out / "lemma_frames.csv", rows, list(rows[0]))
    nA = sum(len(v) for v in A.values())
    nB = sum(len(v) for v in B.values())
    eq = exp.cfg.get("frame_equivalents", {})
    same_concept = sum(1 for r in rows if eq.get(r["A_primary"], r["A_primary"])
                       == eq.get(r["B_primary"], r["B_primary"]))
    md += ["## Frame assignments per lemma", "",
           f"- Rows (sense–frame pairings): A {nA}, B {nB}.",
           f"- Same primary frame: {same_prim} of {len(lemmas)} lemmas"
           + (f" ({same_concept} counting "
              + ", ".join(f"{a} = {b}" for a, b in eq.items())
              + " as the same proposed frame)" if eq else "") + ".",
           f"- Mean overlap of each lemma's frame set (Jaccard): "
           f"{sum(jac) / len(jac):.2f}.",
           f"- Proposed new frames: A {len(propA)} "
           f"({', '.join(p['name'] for p in propA) or 'none'}); B {len(propB)} "
           f"({', '.join(p['name'] for p in propB) or 'none'}).", "",
           "| Lemma | A primary | B primary | Only in A | Only in B |",
           "| --- | --- | --- | --- | --- |"]
    for r in rows:
        mark = "" if r["same_primary"] else " ≠"
        md.append(f"| {r['greek_lemma']} | {r['A_primary']} | "
                  f"{r['B_primary']}{mark} | {r['only_A'] or '–'} | "
                  f"{r['only_B'] or '–'} |")
    prow = []
    md += ["", "## Passage annotations", ""]
    for slug in sorted(set(pasA) | set(pasB)):
        sa, sb = sets_by_target(pasA[slug]), sets_by_target(pasB[slug])
        text = pasA[slug]["text"]
        shared = sa.keys() & sb.keys()
        same_frame = sum(1 for k in shared
                         if sa[k]["frameName"] == sb[k]["frameName"])
        same_fes = sum(1 for k in shared
                       if sa[k]["frameName"] == sb[k]["frameName"]
                       and fe_names(sa[k]) == fe_names(sb[k]))
        md += [f"### {pasA[slug]['source']}", "",
               f"- Targets: A {len(sa)}, B {len(sb)}, both {len(shared)}.",
               f"- Same frame on shared targets: {same_frame} of {len(shared)};"
               f" same frame and same FE labels: {same_fes}.", "",
               "| Target | A frame | B frame |", "| --- | --- | --- |"]
        for k in sorted(sa.keys() | sb.keys()):
            fa = sa[k]["frameName"] if k in sa else "–"
            fb = sb[k]["frameName"] if k in sb else "–"
            md.append(f"| {text[k[0]:k[1] + 1]} | {fa} | {fb} |")
            prow.append({"passage": pasA[slug]["source"],
                         "target": text[k[0]:k[1] + 1], "start": k[0],
                         "end": k[1], "A_frame": fa, "B_frame": fb,
                         "A_FEs": "; ".join(sorted(fe_names(sa[k])))
                         if k in sa else "",
                         "B_FEs": "; ".join(sorted(fe_names(sb[k])))
                         if k in sb else ""})
        md.append("")
    write_csv(out / "passage_targets.csv", prow, list(prow[0]))
    shared_lemmas = [r for r in rows if r["original_primary"]]
    md += ["## Against the original experiment", "",
           f"{len(shared_lemmas)} cluster lemmas were also in the original "
           "experiment.", "",
           "| Lemma | Original primary | A primary | B primary | Original frames "
           "not in A | not in B |", "| --- | --- | --- | --- | --- | --- |"]
    for r in shared_lemmas:
        fz = set(r["original_frames"].split("; "))
        fa = set(r["A_frames"].split("; "))
        fb = set(r["B_frames"].split("; "))
        md.append(f"| {r['greek_lemma']} | {r['original_primary']} | "
                  f"{r['A_primary']} | {r['B_primary']} | "
                  f"{'; '.join(sorted(fz - fa)) or '–'} | "
                  f"{'; '.join(sorted(fz - fb)) or '–'} |")
    bz = json.loads(Path(original_json).read_text(encoding="utf-8"))
    sz = sets_by_target(bz["sentences"][0])
    slug = "odyssey_1_123_framenet"
    if slug in pasA:
        sa, sb = sets_by_target(pasA[slug]), sets_by_target(pasB[slug])
        text = bz["sentences"][0]["text"]
        md += ["", "Odyssey 1.123–124, original annotation vs. the two runs:",
               "", "| Target | Original | A | B |", "| --- | --- | --- | --- |"]
        for k in sorted(sz.keys() | sa.keys() | sb.keys()):
            md.append(f"| {text[k[0]:k[1] + 1]} | "
                      f"{sz[k]['frameName'] if k in sz else '–'} | "
                      f"{sa[k]['frameName'] if k in sa else '–'} | "
                      f"{sb[k]['frameName'] if k in sb else '–'} |")
    (out / "comparison.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


# ------------------------------------------------------------------ index page

GITHUB = "https://github.com/farnoosh-shamsian/DiaSoft"
RUN_NAMES = (("A_without_wordnet", "Without WordNet", "A"),
             ("B_with_wordnet", "With WordNet", "B"))

INDEX_CSS = """
:root{--ink:#1a1a17;--mut:#6a6a63;--line:#e2e0d8;--bg:#faf9f5;--card:#fff;--acc:#534AB7;--teal:#0f6e56;--coral:#993c1d;--new:#7F77DD}
*{box-sizing:border-box}body{font-family:'Noto Sans',system-ui,sans-serif;color:var(--ink);background:var(--bg);margin:0;line-height:1.55;font-size:15px}
.wrap{max-width:1040px;margin:0 auto;padding:36px 20px 80px}
h1{font-weight:600;font-size:28px;margin:0 0 6px}h2{font-weight:600;font-size:21px;margin:40px 0 12px}h3{font-weight:600;font-size:16px;margin:0 0 8px}
.sub{color:var(--mut);margin:0 0 18px;max-width:760px}
.gk{font-family:'Noto Serif',serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0 6px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px}
.tile .n{font-size:26px;font-weight:600;line-height:1.2}.tile .l{color:var(--mut);font-size:13px}
.tile.new .n{color:var(--new)}
ul.key{margin:8px 0 0;padding-left:20px}ul.key li{margin:4px 0}
.cluster{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px 22px;margin:18px 0}
.cluster .head{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 16px;margin-bottom:6px}
.cluster .head h2{margin:0}.mut{color:var(--mut);font-size:13.5px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin-top:14px}
.col{border:1px solid var(--line);border-radius:10px;padding:12px 14px;background:#fcfbf8}
.col h3{display:flex;align-items:baseline;gap:8px}.badge{font-size:11px;border-radius:12px;padding:1px 8px;font-weight:500}
.b-wn{background:#e1f5ee;color:var(--teal)}.b-a{background:#f1efe8;color:var(--mut)}.b-b{background:#eeedfe;color:var(--acc)}.b-c{background:#fdf0e1;color:#8a6d0b}
.col ul{margin:6px 0 0;padding-left:18px;font-size:14px}.col li{margin:3px 0}
.stat{font-size:13px;color:var(--mut);margin-top:4px}
.chip{display:inline-block;background:#eeedfe;color:var(--acc);border-radius:12px;padding:1px 9px;margin:3px 3px 0 0;font-size:12.5px}
.groups{margin-top:8px}.grp{display:inline-block;background:#f1efe8;color:#5f5e5a;border-radius:12px;padding:1px 9px;margin:3px 3px 0 0;font-size:12.5px}
table{width:100%;border-collapse:collapse;font-size:14px;margin:8px 0}
th,td{text-align:left;padding:7px 10px;border-top:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.03em;font-weight:500}
td.c{text-align:center}.yes{color:var(--new);font-weight:600}
.tw{overflow-x:auto}
footer{color:var(--mut);font-size:12.5px;margin-top:44px;border-top:1px solid var(--line);padding-top:16px}
"""


def same_txt(c):
    if c["same_concept"] == c["same_primary"]:
        return str(c["same_primary"])
    return f'{c["same_primary"]} ({c["same_concept"]} by concept)'


def first_sentence(s):
    m = re.match(r"(.+?[.;])(\s|$)", s)
    return m.group(1) if m else s


def gh(path, tree=False):
    """GitHub URL of a path given relative to the project folder."""
    return (f"{GITHUB}/{'tree' if tree else 'blob'}/main/{PROJECT.name}/"
            f"{path}")


def run_stats(exp, name):
    d = exp.dir / name
    if not (d / "FrameNet").exists():
        return None
    asg = read_csv(d / "FrameNet" / f"{exp.slug}_field_framenet_full.csv")
    prop = json.loads((d / "FrameNet" / "proposed_frames.json").read_text(
        encoding="utf-8"))
    prim = {r["greek_lemma"]: r for r in asg if r["assignment"] == "primary"}
    passages = []
    for p in sorted((d / exp.examples).glob("*.json")):
        s = json.loads(p.read_text(encoding="utf-8"))["sentences"][0]
        passages.append((p.stem, s["source"], len(s["annotationSets"])))
    return {"rows": len(asg), "proposed": prop, "primary": prim,
            "primary_new": sum(1 for r in prim.values()
                               if r["frame_status"].startswith("PROPOSED")),
            "frames": {r["frame"] for r in asg}, "passages": passages}


def exp_stats(exp):
    full = read_csv(exp.full)
    lemmas = exp.lemma_rows()
    flags = collections.Counter(r["sense_flag"] for r in full)
    with_syn = {r["greek_lemma"] for r in full}
    runs = {key: run_stats(exp, name) for name, _, key in RUN_NAMES}
    comp = None
    if runs["A"] and runs["B"]:
        A = by_lemma(read_csv(exp.dir / "A_without_wordnet" / "FrameNet" /
                              f"{exp.slug}_field_framenet_full.csv"))
        B = by_lemma(read_csv(exp.dir / "B_with_wordnet" / "FrameNet" /
                              f"{exp.slug}_field_framenet_full.csv"))
        eq = exp.cfg.get("frame_equivalents", {})
        same = sum(1 for l in lemmas
                   if frames_of(A[l["greek_lemma"]])[0]
                   == frames_of(B[l["greek_lemma"]])[0])
        same_concept = sum(1 for l in lemmas
                           if eq.get(frames_of(A[l["greek_lemma"]])[0],
                                     frames_of(A[l["greek_lemma"]])[0])
                           == eq.get(frames_of(B[l["greek_lemma"]])[0],
                                     frames_of(B[l["greek_lemma"]])[0]))
        jac = [jaccard(frames_of(A[l["greek_lemma"]])[1],
                       frames_of(B[l["greek_lemma"]])[1]) for l in lemmas]
        _, _, pa = load_run(exp, "A_without_wordnet")
        _, _, pb = load_run(exp, "B_with_wordnet")
        pas = []
        for slug in sorted(pa):
            sa, sb = sets_by_target(pa[slug]), sets_by_target(pb[slug])
            shared = sa.keys() & sb.keys()
            pas.append((pa[slug]["source"], len(shared), sum(
                1 for k in shared if sa[k]["frameName"] == sb[k]["frameName"])))
        comp = {"same_primary": same, "same_concept": same_concept,
                "jaccard": sum(jac) / len(jac),
                "passages": pas}
    return {"exp": exp, "lemmas": lemmas, "synsets": len(full),
            "core": flags["core"], "plausible": flags["plausible"],
            "no_wn": [l["greek_lemma"] for l in lemmas
                      if l["greek_lemma"] not in with_syn],
            "runs": runs, "comp": comp}


def cmd_index(exps):
    stats = [exp_stats(e) for e in exps]
    rel = lambda e, p: f"{e.dir.relative_to(PROJECT).as_posix()}/{p}"
    # proposed frames across runs
    frames = collections.OrderedDict()
    for st in stats:
        eq = st["exp"].cfg.get("frame_equivalents", {})
        for name, label, key in RUN_NAMES:
            r = st["runs"][key]
            for p in (r["proposed"] if r else []):
                f = frames.setdefault(eq.get(p["name"], p["name"]),
                                      {"def": p["definition"], "in": set(),
                                       "lus": set(), "names": []})
                if p["name"] not in f["names"]:
                    f["names"].append(p["name"])
                f["in"].add((st["exp"].slug, key))
                f["lus"] |= {u["lemma"] for u in p["lexical_units"]}
    cols = [(st["exp"], key) for st in stats for _, _, key in RUN_NAMES]
    n_runs = sum(1 for st in stats for _, _, k in RUN_NAMES if st["runs"][k])
    total_new = sum(len(st["runs"][k]["proposed"]) for st in stats
                    for _, _, k in RUN_NAMES if st["runs"][k])
    h = ['<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>Homeric Hospitality Frames</title>', FONTS,
         f'<style>{INDEX_CSS}</style></head><body><div class="wrap">',
         '<h1>Homeric hospitality clusters <span style="color:var(--mut);'
         'font-weight:400">· WordNet &amp; FrameNet</span></h1>',
         '<p class="sub">The Ancient Greek hospitality WordNet &amp; FrameNet '
         'experiment, redone with word lists from gloss-embedding clusters of '
         'Homeric lemmas. Each cluster was mapped to FrameNet twice: once '
         '<b>without</b> and once <b>with</b> the Ancient Greek WordNet layer, '
         'each run by a separate Claude Opus 5.5 agent. Every page below is '
         'browsable; the data files open on GitHub.</p>',
         '<div class="tiles">',
         f'<div class="tile"><div class="n">{len(stats)}</div><div class="l">'
         'clusters</div></div>',
         f'<div class="tile"><div class="n">{n_runs}</div><div class="l">'
         'runs (with / without WordNet)</div></div>',
         f'<div class="tile new"><div class="n">{len(frames)}</div><div '
         f'class="l">distinct new frames proposed ({total_new} across all '
         'runs)</div></div>']
    for st in stats:
        h.append(f'<div class="tile"><div class="n">{len(st["lemmas"])}</div>'
                 f'<div class="l">lemmas in cluster {st["exp"].cfg["cluster_id"]}'
                 f' ({st["exp"].cfg["clustering"]})</div></div>')
    h.append('</div>')

    # key findings
    key = []
    for st in stats:
        e, rs, c = st["exp"], st["runs"], st["comp"]
        bits = [f'{len(st["lemmas"])} lemmas; {st["core"] + st["plausible"]} '
                f'of {st["synsets"]:,} WordNet synsets kept as real senses']
        for _, label, k in RUN_NAMES:
            if rs[k]:
                names = ", ".join(p["name"] for p in rs[k]["proposed"]) or "none"
                bits.append(f'{label[0].lower() + label[1:]}: {rs[k]["rows"]} sense–frame '
                            f'pairings, {len(rs[k]["proposed"])} new frames '
                            f'({names})')
        if c:
            bits.append(f'same primary frame in both runs for '
                        f'{same_txt(c)} of {len(st["lemmas"])} lemmas')
        key.append(f'<li><b>Cluster {e.cfg["cluster_id"]}</b> — '
                   + "; ".join(bits) + '.</li>')
    h.append('<h2>Summary</h2><ul class="key">' + "".join(key) + '</ul>')

    # one block per cluster
    for st in stats:
        e = st["exp"]
        groups = collections.Counter(l["group"] for l in st["lemmas"])
        label = cluster_block(e)[0].split("|")[-1].strip()
        docs = [f'<a href="{gh(rel(e, p.name))}">{t}</a>' for t, p in
                [("README", e.dir / "README.md")] +
                [("protocol", p) for p in e.dir.glob("protocol_*.md")]
                if p.exists()]
        h.append(f'<div class="cluster" id="{e.slug}"><div class="head"><h2>'
                 f'Cluster {e.cfg["cluster_id"]}</h2><span class="mut">'
                 f'{e.cfg["clustering"]} · “{esc(label)}” · '
                 f'{len(st["lemmas"])} lemmas'
                 + "".join(" · " + d for d in docs) +
                 '</span></div><div class="groups">' + "".join(
                     f'<span class="grp">{esc(g)} {n}</span>'
                     for g, n in groups.items()) + '</div>')
        h.append('<div class="cols">')
        wn_page = rel(e, f"AGWN_PWN/{e.slug}_field_links.html")
        h.append(
            '<div class="col"><h3>WordNet layer <span class="badge b-wn">AGWN → '
            'PWN 3.0</span></h3><ul>'
            f'<li><a href="{wn_page}">WordNet links (browsable)</a></li>'
            f'<li><a href="{gh(rel(e, f"AGWN_PWN/{e.slug}_field_wordnet_full.csv"))}">'
            'all synsets (CSV)</a></li>'
            f'<li><a href="{gh(rel(e, f"{e.slug}_terms_table.md"))}">'
            'vocabulary table</a></li></ul>'
            f'<div class="stat">{st["synsets"]:,} synsets · {st["core"]} core · '
            f'{st["plausible"]} plausible'
            + (f' · no WordNet data: <span class="gk">{esc(", ".join(st["no_wn"]))}'
               '</span>' if st["no_wn"] else "") + '</div></div>')
        for name, label, k in RUN_NAMES:
            r = st["runs"][k]
            badge = "b-a" if k == "A" else "b-b"
            h.append(f'<div class="col"><h3>{label} <span class="badge {badge}">'
                     f'run {k}</span></h3>')
            if not r:
                h.append('<div class="stat">not yet run</div></div>')
                continue
            base = rel(e, name)
            items = [f'<li><a href="{base}/FrameNet/{e.slug}_framenet.html">'
                     'FrameNet layer (browsable)</a></li>']
            for slug, src, n in r["passages"]:
                items.append(f'<li><a href="{base}/{e.examples}/{slug}.html">'
                             f'{esc(src.replace("Homer, ", ""))}</a> '
                             f'<span class="mut">({n} frames)</span></li>')
            items += [
                f'<li><a href="{gh(base + f"/FrameNet/{e.slug}_field_framenet_full.csv")}">'
                'frame assignments (CSV)</a></li>',
                f'<li><a href="{gh(base + "/FrameNet/Lemmata", tree=True)}">'
                'lemma notes (Obsidian)</a></li>',
                f'<li><a href="{gh(base + "/method_notes.md")}">method notes'
                '</a></li>']
            new = "".join(f'<span class="chip">🆕 {esc(p["name"])}</span>'
                          for p in r["proposed"]) or '<span class="mut">none</span>'
            h.append('<ul>' + "".join(items) + '</ul>'
                     f'<div class="stat">{r["rows"]} sense–frame pairings · '
                     f'new frames:</div>{new}</div>')
        c = st["comp"]
        if c:
            pas = "; ".join(f'{src.replace("Homer, ", "")}: {same} of {n}'
                            for src, n, same in c["passages"])
            h.append(
                '<div class="col"><h3>Comparison <span class="badge b-c">A vs B'
                '</span></h3><ul>'
                f'<li><a href="{gh(rel(e, "comparison/comparison.md"))}">'
                'comparison tables</a></li>'
                f'<li><a href="{gh(rel(e, "comparison/lemma_frames.csv"))}">'
                'frames per lemma (CSV)</a></li></ul>'
                f'<div class="stat">same primary frame: {same_txt(c)} of '
                f'{len(st["lemmas"])} lemmas · mean frame-set overlap '
                f'{c["jaccard"]:.2f} · same frame on shared passage targets: '
                f'{esc(pas)}</div></div>')
        h.append('</div></div>')

    # new frames table
    if frames:
        h.append('<h2>New frames proposed</h2><p class="sub">Frames proposed '
                 'where FrameNet 1.7 has none. A tick marks the runs that '
                 'proposed the frame; two names in one row are the same frame '
                 'proposed under different names.</p><div class="tw"><table><tr>'
                 '<th>Frame</th>' + "".join(
                     f'<th>{e.cfg["cluster_id"]} · {"no WN" if k == "A" else "WN"}'
                     '</th>' for e, k in cols) + '<th>Lexical units</th>'
                 '<th>Definition (first run proposing it)</th></tr>')
        for name, f in frames.items():
            h.append(f'<tr><td><b>{" / ".join(esc(n) for n in f["names"])}'
                     '</b></td>' + "".join(
                f'<td class="c">{"<span class=yes>✓</span>" if (e.slug, k) in f["in"] else ""}</td>'
                for e, k in cols) +
                f'<td class="gk">{esc(", ".join(sorted(f["lus"])))}</td>'
                f'<td>{esc(first_sentence(f["def"]))}</td></tr>')
        h.append('</table></div>')

    # comparisons
    h.append('<h2>How the runs differ</h2><div class="tw"><table><tr><th>'
             'Cluster</th><th>Pairings A / B</th><th>New frames A / B</th>'
             '<th>Same primary frame</th><th>Frame-set overlap</th></tr>')
    for st in stats:
        c, rs = st["comp"], st["runs"]
        if not c:
            continue
        h.append(f'<tr><td>{st["exp"].cfg["cluster_id"]}</td><td>'
                 f'{rs["A"]["rows"]} / {rs["B"]["rows"]}</td><td>'
                 f'{len(rs["A"]["proposed"])} / {len(rs["B"]["proposed"])}</td>'
                 f'<td>{same_txt(c)} of {len(st["lemmas"])}</td><td>'
                 f'{c["jaccard"]:.2f}</td></tr>')
    h.append('</table></div>')
    if len(stats) > 1:
        a, b = stats[0], stats[1]
        shared = [l["greek_lemma"] for l in a["lemmas"]
                  if l["greek_lemma"] in {x["greek_lemma"] for x in b["lemmas"]}]
        rows = []
        for _, label, k in RUN_NAMES:
            ra, rb = a["runs"][k], b["runs"][k]
            if ra and rb and shared:
                same = sum(1 for l in shared if ra["primary"][l]["frame"]
                           == rb["primary"][l]["frame"])
                rows.append(f'<tr><td>{label}</td><td>{same} of {len(shared)}'
                            '</td></tr>')
        if rows:
            h.append(f'<p class="sub" style="margin-top:14px">The same '
                     f'{len(shared)} lemmas occur in clusters '
                     f'{a["exp"].cfg["cluster_id"]} and '
                     f'{b["exp"].cfg["cluster_id"]}. Same primary frame for '
                     'them in both clusters:</p><table style="max-width:420px">'
                     '<tr><th>Run</th><th>Same primary</th></tr>'
                     + "".join(rows) + '</table>')
    h.append('<footer>Frames = Berkeley FrameNet 1.7 (English); every existing '
             'frame and frame element was checked against the FrameNet 1.7 '
             'data. Greek senses = LSJ glosses of the cluster, plus the Ancient '
             'Greek WordNet layer in the runs with WordNet. Sense flags, frame '
             'assignments, proposed frames and passage annotations are proposals '
             'by Claude Opus 5.5 for review, not validated data. Pipeline: '
             f'<a href="{gh("pipeline", tree=True)}">pipeline</a>; '
             f'<a href="{gh("README.md")}">project README</a>.</footer></div>'
             '</body></html>')
    out = PROJECT / "index.html"
    out.write_text("\n".join(h) + "\n", encoding="utf-8")
    print(f"wrote {out}")


# ------------------------------------------------------------------ main

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1] == "index":
        return cmd_index([Exp(p) for p in sys.argv[2:]])
    cmd, exp = sys.argv[1], Exp(sys.argv[2])
    args = sys.argv[3:]
    if cmd == "prepare":
        cmd_prepare(exp)
    elif cmd == "passages":
        cmd_passages(exp)
    elif cmd == "extract":
        cmd_extract(exp)
    elif cmd == "resolve":
        cmd_resolve(exp)
    elif cmd == "links":
        cmd_links(exp)
    elif cmd == "render":
        cmd_render(exp, args[0], args[1], "--wordnet" in args)
    elif cmd == "compare":
        cmd_compare(exp, args[0], args[1])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
