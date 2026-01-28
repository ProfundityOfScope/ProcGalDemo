#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jan 10 01:35:11 2026

@author: sethbruzewski
"""

MASK64 = (1 << 64) - 1
TILE_DOMAIN = 0x54_49_4C_45  # "TILE"
STAR_DOMAIN = 0x53_54_41_52  # "STAR"

def splitmix64(x: int) -> int:
    x = (x + 0x9E3779B97F4A7C15) & MASK64
    z = x
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9 & MASK64
    z = (z ^ (z >> 27)) * 0x94D049BB133111EB & MASK64
    return (z ^ (z >> 31)) & MASK64

def hash64(*vals: int) -> int:
    h = 0xA0761D6478BD642F
    for v in vals:
        h = splitmix64(h ^ (v & MASK64))
    return h

def u01(seed: int, tag: int) -> float:
    x = splitmix64(seed ^ ((tag * 0xD6E8FEB86659FD93) & MASK64))
    return ((x >> 11) & ((1 << 53) - 1)) / float(1 << 53)

def tile_key(world_seed: int, depth: int, x: int, y: int) -> int:
    return hash64(TILE_DOMAIN, world_seed, depth, x, y)

def star_id(tile_key_: int, i: int) -> int:
    return hash64(STAR_DOMAIN, tile_key_, i)
