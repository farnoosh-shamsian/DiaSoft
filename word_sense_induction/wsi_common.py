# -*- coding: utf-8 -*-
"""
wsi_common.py — shared plumbing for the Word-Sense-Induction stage.

The two modules this stage reuses live in sibling folders that are not Python
packages ("frame_induction", "cluster_gloss_embeddings"), so a plain `import`
will not find them. We load them by file path via importlib — the exact trick
`frame_induction/frame_induction.py` already uses to borrow the gloss module.

Nothing here trains or downloads anything; it only resolves paths and imports.
"""

import importlib.util
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).parent               # "word_sense_induction"
REPO = HERE.parent
OUTPUT_DIR = HERE / "wsi_output"

# Sibling modules reused (imported by file path, not modified)
TREEBANK_PY = REPO / "frame_induction" / "treebank.py"
GLOSS_PY    = REPO / "cluster_gloss_embeddings" / "gloss_embedding_clusters.py"

# Cached artifacts shared across the three scripts
OCC_VECTORS     = OUTPUT_DIR / "occ_vectors.npy"     # (N, H) float32, L2-normalized
OCC_INDEX       = OUTPUT_DIR / "occ_index.csv"       # one row per occurrence
SENSE_CENTROIDS = OUTPUT_DIR / "sense_centroids.npy" # (S, H) float32, unit vectors
SENSES_CSV      = OUTPUT_DIR / "senses.csv"          # one row per sense

# FastText baseline field run, for the ARI comparison in sense_fields.py
FASTTEXT_BASELINE = (REPO / "clustering_homer" /
                     "semantic_fields_output_HDBSCAN_Leiden" / "lemma_clusters.csv")

MODEL_NAME  = "bowphs/GreBerta"   # SOTA monolingual Ancient-Greek RoBERTa
CONTENT_POS = {"n", "v", "a"}     # nouns, verbs, adjectives (AGLDT postag pos.)
SEED        = 42


def load_module(path, name):
    """Import a .py file by absolute path under a private module name."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                 # so the module can find itself
    spec.loader.exec_module(mod)
    return mod


def load_treebank():
    return load_module(TREEBANK_PY, "tb_mod")


def load_gloss():
    return load_module(GLOSS_PY, "gloss_mod")
