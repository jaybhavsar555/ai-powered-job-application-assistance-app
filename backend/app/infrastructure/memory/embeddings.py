"""
Embedding helpers for long-term memory.

Uses the OpenAI-compatible embeddings API (Ollama: nomic-embed-text, or
OpenAI: text-embedding-3-small). Falls back to a deterministic local hash
vector when no LLM endpoint is available so create/search still work offline.
"""
from __future__ import annotations

import hashlib
import math
import struct
from typing import List

from app.core.config import get_settings
from app.infrastructure.llm.client import get_raw_openai_client


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _hash_embed(text: str, dims: int) -> List[float]:
    """Deterministic fallback embedding (not semantic — offline/dev only)."""
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    values: List[float] = []
    counter = 0
    while len(values) < dims:
        block = hashlib.sha256(seed + struct.pack(">I", counter)).digest()
        for i in range(0, len(block) - 3, 4):
            if len(values) >= dims:
                break
            # Map uint32 to [-1, 1]
            n = struct.unpack(">I", block[i : i + 4])[0]
            values.append((n / 0xFFFFFFFF) * 2.0 - 1.0)
        counter += 1
    return _l2_normalize(values)


async def embed_text(text: str) -> List[float]:
    settings = get_settings()
    dims = settings.EMBEDDING_DIMS
    cleaned = (text or "").strip()
    if not cleaned:
        return _hash_embed("", dims)

    client = get_raw_openai_client()
    if client is None:
        return _hash_embed(cleaned, dims)

    try:
        response = await client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=cleaned,
        )
        vector = list(response.data[0].embedding)
        # Keep collection dimension consistent even if provider differs
        if len(vector) != dims:
            if len(vector) > dims:
                vector = vector[:dims]
            else:
                vector = vector + [0.0] * (dims - len(vector))
            vector = _l2_normalize(vector)
        return vector
    except Exception:
        # Model not pulled / endpoint down — degrade gracefully
        return _hash_embed(cleaned, dims)


def entity_to_embed_text(title: str, entity_type: str, content: dict) -> str:
    parts = [f"Type: {entity_type}", f"Title: {title}"]
    if content:
        parts.append(f"Content: {content}")
    return "\n".join(parts)
