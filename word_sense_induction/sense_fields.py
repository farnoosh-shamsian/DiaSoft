# -*- coding: utf-8 -*-
"""
sense_fields.py — Stage-WSI step 3: semantic FIELDS over word senses.

The sense centroids from step 2 are clustered into emergent semantic fields,
reusing DiaSoft's existing Stage-3 machinery (UMAP+HDBSCAN, Ward, c-TF-IDF
naming) from "cluster_gloss_embeddings/gloss_embedding_clusters.py". The only
change from the original field pipeline is the UNIT of clustering: word *senses*
(GreBERTa, contextual) instead of lemma *types* (English-gloss MiniLM). A
polysemous lemma can now land in several fields, one per sense.

Outputs (word_sense_induction/wsi_output/)
  sense_fields.csv     lemma, sense_id, n_occ, field_hdbscan, field_label,
                       field_ward_25, gloss, top_context_lemmas
  fields_hdbscan.txt   one block per HDBSCAN field, senses by centrality
  fields_ward_k*.txt   the Ward cut at each granularity in WARD_CUTS
  field_report.txt     stats, silhouette, polysemy spread, ARI vs FastText run

Run:   py word_sense_induction/sense_fields.py
Dependencies: numpy, pandas, scikit-learn  (+ the gloss module's umap/scipy)
"""

import sys

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, silhouette_score

import wsi_common as C

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def label_for(sid_row):
    return f"{sid_row['lemma']}#{sid_row['sense_id']}"


def write_field_dump(path, header, order, senses, labels, names, vecs, gloss):
    idx_by = gloss.group_indices(labels)
    ranked = gloss.members_by_centrality(idx_by, vecs)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n\n")
        for lab, idx in sorted(ranked.items(), key=lambda kv: -len(kv[1])):
            name = names.get(lab, "(unnamed)")
            f.write(f"FIELD {lab}  |  {len(idx)} senses  |  {name}\n")
            for i in idx:
                r = senses.iloc[i]
                ctx = r["top_context_lemmas"] or ""
                g = (r["gloss"] or "")[:70]
                f.write(f"    {label_for(r):<22} ({r['n_occ']:>3})  {g}"
                        f"{'  | ' + ctx if ctx else ''}\n")
            f.write("\n")


def baseline_ari(senses, hdb):
    """Adjusted Rand Index of the sense-level fields vs the FastText lemma-level
    run, compared at the lemma level (each lemma -> field of its largest sense)."""
    if not C.FASTTEXT_BASELINE.exists():
        return None
    base = pd.read_csv(C.FASTTEXT_BASELINE)
    if "hdbscan_cluster" not in base.columns:
        return None
    tmp = senses.assign(field=hdb)
    tmp = tmp[tmp["field"] != -1]
    if tmp.empty:
        return None
    # per lemma: field of the sense with the most occurrences
    winner = (tmp.sort_values("n_occ", ascending=False)
              .drop_duplicates("lemma").set_index("lemma")["field"])
    base = base[base["hdbscan_cluster"] != -1].set_index("lemma")
    common = winner.index.intersection(base.index)
    if len(common) < 10:
        return None
    ari = adjusted_rand_score(base.loc[common, "hdbscan_cluster"].to_numpy(),
                              winner.loc[common].to_numpy())
    return ari, len(common)


def main():
    if not C.SENSE_CENTROIDS.exists():
        sys.exit("Run wsi_cluster.py first (sense_centroids.npy missing).")
    print("Loading sense centroids + table ...")
    vecs = np.load(C.SENSE_CENTROIDS).astype(np.float64)
    senses = pd.read_csv(C.SENSES_CSV, encoding="utf-8").fillna(
        {"gloss": "", "top_context_lemmas": ""})
    assert len(vecs) == len(senses), "centroids / senses.csv out of sync"
    print(f"   {len(senses):,} senses over {senses['lemma'].nunique():,} lemmas")

    print("Loading reusable clustering machinery (gloss module) ...")
    gloss = C.load_gloss()
    glosses = senses["gloss"].fillna("").tolist()

    print("Clustering senses into fields (UMAP+HDBSCAN, primary) ...")
    hdb = gloss.run_umap_hdbscan(vecs)
    n_fields = len(set(hdb)) - (1 if -1 in hdb else 0)
    n_noise = int((hdb == -1).sum())
    print(f"   {n_fields} fields, {n_noise:,} unassigned "
          f"({n_noise / len(hdb):.0%})")

    print("Ward cross-view + c-TF-IDF field names ...")
    ward = gloss.run_ward(vecs)
    hdb_names = gloss.ctfidf_labels(hdb, glosses)
    ward_names = {k: gloss.ctfidf_labels(lab, glosses) for k, lab in ward.items()}

    # ---- sense_fields.csv --------------------------------------------------
    out = senses[["lemma", "sense_id", "n_occ", "gloss",
                  "top_context_lemmas"]].copy()
    out["field_hdbscan"] = hdb
    out["field_label"] = [hdb_names.get(l, "") for l in hdb]
    ward25 = ward.get(25, ward[min(ward)])
    out["field_ward_25"] = ward25
    out = out[["lemma", "sense_id", "n_occ", "field_hdbscan", "field_label",
               "field_ward_25", "gloss", "top_context_lemmas"]]
    out.to_csv(C.OUTPUT_DIR / "sense_fields.csv", index=False, encoding="utf-8")

    # ---- human-readable dumps ---------------------------------------------
    write_field_dump(C.OUTPUT_DIR / "fields_hdbscan.txt",
                     f"# {n_fields} emergent fields over word senses "
                     f"(GreBERTa contextual centroids; UMAP+HDBSCAN).\n"
                     f"# label = c-TF-IDF of member senses' LSJ glosses; "
                     f"senses by centrality. '#' separates lemma from sense id.",
                     None, senses, hdb, hdb_names, vecs, gloss)
    for k, lab in ward.items():
        write_field_dump(C.OUTPUT_DIR / f"fields_ward_k{k}.txt",
                         f"# Ward cut at K={k} over sense centroids.",
                         None, senses, lab, ward_names[k], vecs, gloss)

    # ---- report ------------------------------------------------------------
    sil = float("nan")
    mask = hdb != -1
    if mask.sum() > 2 and len(set(hdb[mask])) > 1:
        sil = silhouette_score(vecs[mask], hdb[mask], metric="cosine")
    # polysemous lemmas whose senses spread across >=2 assigned fields
    spread = 0
    poly = senses[senses["n_senses_lemma"] > 1]
    for _lemma, g in senses.assign(field=hdb).groupby("lemma"):
        if g["field"].nunique() == 0:
            continue
        fields = set(g.loc[g["field"] != -1, "field"])
        if len(g) > 1 and len(fields) >= 2:
            spread += 1
    ari = baseline_ari(senses, hdb)

    with open(C.OUTPUT_DIR / "field_report.txt", "w", encoding="utf-8") as f:
        f.write("Sense-level semantic fields — report\n")
        f.write("=" * 44 + "\n\n")
        f.write(f"Model              : {C.MODEL_NAME} (contextual, per-occurrence)\n")
        f.write(f"Senses clustered   : {len(senses):,}\n")
        f.write(f"Lemmas             : {senses['lemma'].nunique():,}\n")
        f.write(f"Polysemous lemmas  : {poly['lemma'].nunique():,}\n")
        f.write(f"HDBSCAN fields     : {n_fields}  "
                f"(noise {n_noise:,}, {n_noise/len(hdb):.0%})\n")
        f.write(f"Field silhouette   : {sil:.4f} (cosine, noise excluded)\n")
        f.write(f"Polysemy spread    : {spread:,} lemmas have senses in >=2 fields "
                f"(the payoff of sense-level clustering)\n")
        if ari is not None:
            f.write(f"ARI vs FastText run: {ari[0]:.4f} over {ari[1]:,} shared "
                    f"lemmas (largest sense per lemma vs "
                    f"{C.FASTTEXT_BASELINE.name})\n")
        else:
            f.write("ARI vs FastText run: n/a (baseline not found)\n")
        f.write(f"\nWard cuts          : {gloss.WARD_CUTS}\n")
        f.write("\nMethod: word senses (GreBERTa occurrence clusters) embedded by\n"
                "their centroid, clustered with the same UMAP+HDBSCAN / Ward /\n"
                "c-TF-IDF pipeline as the lemma-type field runs, so results are\n"
                "directly comparable. Fields are the participant inventory that\n"
                "frame slots draw from (see 'frame_induction/').\n")

    print(f"\nSaved sense_fields.csv, fields_hdbscan.txt, "
          f"fields_ward_k*.txt, field_report.txt -> {C.OUTPUT_DIR}")
    print(f"Field silhouette {sil:.4f}; polysemy spread {spread:,} lemmas"
          + (f"; ARI vs FastText {ari[0]:.4f}" if ari else ""))


if __name__ == "__main__":
    main()
