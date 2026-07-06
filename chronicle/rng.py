# -*- coding: utf-8 -*-
"""
Created on Wed Jul  1 23:47:16 2026

@author: bruze
"""

"""Deterministic RNG plumbing: independent stream for any hashable key path."""

import hashlib
import numpy as np

from .config import MASTER_SEED


def sub_rng(*key: object) -> np.random.Generator:
    """Reproducible RNG stream derived from (MASTER_SEED, *key).

    Every generator in the codebase draws from its own named stream, so
    adding/removing one system never perturbs another (no shared cursor).
    """
    h = hashlib.sha256(repr((MASTER_SEED,) + key).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], "little"))