from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone

TOKEN_RE = re.compile(r"\w+", re.UNICODE)


@dataclass
class ScoredRule:
    page_id: int
    score: float


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


def build_hash_embedding(text: str, dims: int = 128) -> list[float]:
    vec = [0.0] * dims
    for tok in tokenize(text):
        digest = hashlib.sha1(tok.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dims
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def to_json(vec: list[float]) -> str:
    return json.dumps(vec)


def from_json(raw: str) -> list[float]:
    return [float(x) for x in json.loads(raw)]
