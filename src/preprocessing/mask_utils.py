"""Binary mask <-> run-length encoding (COCO-style, uncompressed, column-major).

S3 may send masks as raw arrays, ``.npy``/``.png`` files, or RLE dicts::

    {"size": [height, width], "counts": [n0, n1, n2, ...]}

``counts`` alternates runs of 0s and 1s, starting with 0s, over the mask
flattened in column-major (Fortran) order — the same convention as
pycocotools uncompressed RLE, so S3 can use either implementation.
"""

from __future__ import annotations

import numpy as np


def rle_encode(mask: np.ndarray) -> dict:
    flat = np.asarray(mask, dtype=bool).flatten(order="F").astype(np.uint8)
    # Positions where the value changes
    change = np.flatnonzero(np.diff(flat)) + 1
    bounds = np.concatenate(([0], change, [flat.size]))
    runs = np.diff(bounds).tolist()
    if flat.size and flat[0] == 1:
        runs = [0] + runs
    return {"size": [int(mask.shape[0]), int(mask.shape[1])], "counts": runs}


def rle_decode(rle: dict) -> np.ndarray:
    h, w = rle["size"]
    flat = np.zeros(h * w, dtype=bool)
    pos, val = 0, False
    for run in rle["counts"]:
        if val:
            flat[pos : pos + run] = True
        pos += run
        val = not val
    return flat.reshape((h, w), order="F")
