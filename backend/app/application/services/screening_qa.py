"""Screening Q&A memory bank — stored as wiki entities (entity_type=screening_qa)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.infrastructure.db.models import DBWikiEntity
from app.schemas.knowledge import WikiEntityCreate
from app.application.services.knowledge import KnowledgeBaseService

ENTITY_TYPE = "screening_qa"


def _normalize_q(q: str) -> str:
    return " ".join((q or "").lower().split())


class ScreeningQAService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.kb = KnowledgeBaseService(db)

    async def list(self, user_id: UUID) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(DBWikiEntity)
            .where(
                DBWikiEntity.user_id == user_id,
                DBWikiEntity.entity_type == ENTITY_TYPE,
            )
            .order_by(DBWikiEntity.updated_at.desc())
        )
        return [self._to_out(e) for e in result.scalars().all()]

    async def create(
        self, user_id: UUID, question: str, answer: str, tags: Optional[list[str]] = None
    ) -> dict[str, Any]:
        question = (question or "").strip()
        answer = (answer or "").strip()
        if not question or not answer:
            raise HTTPException(status_code=400, detail="question and answer required")
        entity = await self.kb.create(
            user_id,
            WikiEntityCreate(
                entity_type=ENTITY_TYPE,
                title=question[:200],
                content={
                    "question": question,
                    "answer": answer,
                    "tags": tags or [],
                    "norm_question": _normalize_q(question),
                },
            ),
            index_vectors=True,
        )
        return self._to_out(entity)

    async def update(
        self,
        user_id: UUID,
        qa_id: UUID,
        *,
        question: Optional[str] = None,
        answer: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        entity = await self._get(user_id, qa_id)
        content = dict(entity.content or {})
        if question is not None:
            q = question.strip()
            entity.title = q[:200]
            content["question"] = q
            content["norm_question"] = _normalize_q(q)
        if answer is not None:
            content["answer"] = answer.strip()
        if tags is not None:
            content["tags"] = tags
        entity.content = content
        await self.db.commit()
        await self.db.refresh(entity)
        return self._to_out(entity)

    async def delete(self, user_id: UUID, qa_id: UUID) -> None:
        entity = await self._get(user_id, qa_id)
        await self.db.delete(entity)
        await self.db.commit()

    async def match(self, user_id: UUID, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Simple keyword/substring match for extension form questions."""
        qn = _normalize_q(query)
        if not qn:
            return []
        items = await self.list(user_id)
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in items:
            nq = _normalize_q(str(item.get("question") or ""))
            score = 0
            if qn == nq:
                score = 100
            elif qn in nq or nq in qn:
                score = 70
            else:
                # token overlap
                qt = set(qn.split())
                nt = set(nq.split())
                if qt and nt:
                    overlap = len(qt & nt) / max(len(qt), 1)
                    if overlap >= 0.5:
                        score = int(40 + overlap * 40)
            if score:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in scored[:limit]]

    DEFAULT_QA: list[tuple[str, str, list[str]]] = [
        (
            "Are you authorized to work in this country / do you require sponsorship?",
            "Yes, I am authorized to work. Please edit this answer for your situation.",
            ["work_auth", "visa"],
        ),
        (
            "What is your notice period / when can you start?",
            "I can start within 2–4 weeks, or sooner if needed.",
            ["notice", "start_date"],
        ),
        (
            "What are your salary expectations?",
            "Open to a competitive range based on role scope and location — happy to discuss.",
            ["salary", "compensation"],
        ),
        (
            "How many years of experience do you have in this field?",
            "See my resume for exact tenure; I have hands-on experience matching this role's stack.",
            ["experience", "years"],
        ),
        (
            "Are you willing to relocate or work remotely?",
            "Open to remote and hybrid; relocation case-by-case for the right role.",
            ["remote", "relocate"],
        ),
        (
            "Why are you interested in this role / company?",
            "The role matches my strengths building product and shipping reliably — excited to contribute.",
            ["motivation"],
        ),
        (
            "What is your current address?",
            "123 Main St, Tech City, ST 12345",
            ["address", "location"],
        ),
        (
            "What is your current or most recent company?",
            "My Current Company Inc.",
            ["company", "employer"],
        ),
        (
            "What is your postal code / zip code / pincode?",
            "12345",
            ["pincode", "zip", "postal"],
        ),
    ]

    async def seed_defaults(self, user_id: UUID) -> dict[str, Any]:
        """Seed common ATS screening answers if the bank is empty or missing keys."""
        existing = await self.list(user_id)
        existing_norms = {
            _normalize_q(str(i.get("question") or "")) for i in existing
        }
        created: list[dict[str, Any]] = []
        for question, answer, tags in self.DEFAULT_QA:
            if _normalize_q(question) in existing_norms:
                continue
            created.append(await self.create(user_id, question, answer, tags))
        return {
            "created": len(created),
            "total": len(existing) + len(created),
            "items": created,
            "note": (
                "Edit answers to match your real work auth, notice, and salary. "
                "Empty bank = extension fills nothing."
            ),
        }

    async def _get(self, user_id: UUID, qa_id: UUID) -> DBWikiEntity:
        result = await self.db.execute(
            select(DBWikiEntity).where(
                DBWikiEntity.id == qa_id,
                DBWikiEntity.user_id == user_id,
                DBWikiEntity.entity_type == ENTITY_TYPE,
            )
        )
        entity = result.scalars().first()
        if not entity:
            raise HTTPException(status_code=404, detail="Screening Q&A not found")
        return entity

    def _to_out(self, entity: DBWikiEntity) -> dict[str, Any]:
        content = entity.content or {}
        return {
            "id": str(entity.id),
            "question": content.get("question") or entity.title,
            "answer": content.get("answer") or "",
            "tags": content.get("tags") or [],
            "created_at": entity.created_at.isoformat() if entity.created_at else None,
            "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        }
