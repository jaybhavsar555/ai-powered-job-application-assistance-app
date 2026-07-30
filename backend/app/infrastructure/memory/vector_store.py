"""
Qdrant-backed long-term memory for WikiEntity semantic retrieval.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import get_settings


COLLECTION = "wiki_entities"


class VectorMemory:
    def __init__(self, client: Optional[QdrantClient] = None):
        settings = get_settings()
        self.client = client or QdrantClient(url=settings.QDRANT_URL, timeout=10)
        self.dims = settings.EMBEDDING_DIMS
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        try:
            existing = {c.name for c in self.client.get_collections().collections}
            if COLLECTION not in existing:
                self.client.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=qmodels.VectorParams(
                        size=self.dims,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
        except Exception:
            # Qdrant may be down during boot; callers handle upsert/search failures
            pass

    def upsert_entity(
        self,
        *,
        vector_id: UUID,
        user_id: UUID,
        entity_id: UUID,
        entity_type: str,
        title: str,
        vector: List[float],
    ) -> UUID:
        self._ensure_collection()
        self.client.upsert(
            collection_name=COLLECTION,
            points=[
                qmodels.PointStruct(
                    id=str(vector_id),
                    vector=vector,
                    payload={
                        "user_id": str(user_id),
                        "entity_id": str(entity_id),
                        "entity_type": entity_type,
                        "title": title,
                    },
                )
            ],
        )
        return vector_id

    def search(
        self,
        *,
        user_id: UUID,
        query_vector: List[float],
        limit: int = 8,
        entity_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_collection()
        must = [
            qmodels.FieldCondition(
                key="user_id",
                match=qmodels.MatchValue(value=str(user_id)),
            )
        ]
        if entity_type:
            must.append(
                qmodels.FieldCondition(
                    key="entity_type",
                    match=qmodels.MatchValue(value=entity_type),
                )
            )

        hits = self.client.search(
            collection_name=COLLECTION,
            query_vector=query_vector,
            query_filter=qmodels.Filter(must=must),
            limit=limit,
            with_payload=True,
        )
        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                {
                    "vector_id": hit.id,
                    "score": float(hit.score),
                    "entity_id": payload.get("entity_id"),
                    "entity_type": payload.get("entity_type"),
                    "title": payload.get("title"),
                }
            )
        return results

    def delete_by_vector_id(self, vector_id: UUID) -> None:
        try:
            self.client.delete(
                collection_name=COLLECTION,
                points_selector=qmodels.PointIdsList(points=[str(vector_id)]),
            )
        except Exception:
            pass


_vector_memory: Optional[VectorMemory] = None


def get_vector_memory() -> VectorMemory:
    global _vector_memory
    if _vector_memory is None:
        _vector_memory = VectorMemory()
    return _vector_memory


def new_vector_id() -> UUID:
    return uuid4()
