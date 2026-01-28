#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 26 18:17:26 2026

@author: sethbruzewski

Deterministic random number generation for procedural content.
Ensures the same coordinates always produce the same results.
"""

import hashlib
import random
from typing import Protocol, Any, TypeVar, Sequence

T = TypeVar("T")

class RNG(Protocol):
    """Minimal RNG interface this project expects.
    random.Random also matches.
    """
    def random(self) -> float: ...
    def randint(self, a: int, b: int) -> int: ...
    def uniform(self, a: float, b: float) -> float: ...
    def choice(self, seq: Sequence[T]) -> T: ...
    def choices(self, population: Sequence[T], weights: Sequence[float] | None = None) -> list[T]: ...

class DeterministicRNG:
    """Wrapper around random that ensures deterministic generation"""
    
    @staticmethod
    def create_seed(*components: Any) -> int:
        """Create a deterministic seed from arbitrary inputs"""
        # Convert all components to strings and hash them
        combined = "|".join(str(c) for c in components)
        # Use SHA256 for good distribution, take first 8 bytes as seed
        hash_bytes = hashlib.sha256(combined.encode()).digest()
        return int.from_bytes(hash_bytes[:8], 'big')
    
    @staticmethod
    def seeded_random(*components: Any):
        """Return a Random instance seeded by the components"""
        seed = DeterministicRNG.create_seed(*components)
        return random.Random(seed)