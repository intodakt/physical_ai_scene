# S3 — weeks 10–11: frozen prompts and appearance embeddings

## W10 — prompt freezing and semantic scores (`src/open_vocab/freeze.py`)

| Frozen set | Source | Prompts |
|---|---|---|
| `configs/frozen/desk_v1.json` | `desk.json` | 6 |
| `configs/frozen/generic_tabletop_v1.json` | `generic_tabletop.json` | 69 |

Each file stores the prompts, detector / segmenter and thresholds plus a SHA-256 fingerprint.
`python -m src.open_vocab.freeze --check <S3 run> --frozen <frozen json>` reports frames that used a
different prompt list and the semantic score per label (count, mean, min). From now on the W12
seen / unseen evaluation uses only frozen sets.

## W11 — appearance embeddings (`src/open_vocab/embeddings.py`)

`ColorHistEmbedder` (HSV histogram of the mask, 128-d, no extra dependency) and a `ClipEmbedder`
hook (torch + CLIP; not run in this repository yet). Consistency = mean cosine similarity of the same
object across frames vs. different objects in the same frame.

Synthetic desk sequence (8 frames): same object 1.00 (min 0.998), different objects 0.05 (max 0.24),
gap 0.95 — see `embedding_consistency.json`. The synthetic render has flat colours, so this is an
upper bound; on real frames lighting changes lower it. Run on a real bag (frames exported by the demo):

    python -m src.open_vocab.embeddings --frames data/demo_store/datasets/S1_static_bag/frames

Limit: a colour histogram cannot separate two identical white mugs; that needs CLIP or position (S6).
