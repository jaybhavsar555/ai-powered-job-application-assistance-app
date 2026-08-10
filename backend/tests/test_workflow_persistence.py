"""Unit tests for workflow persistence helpers (no live LLM)."""

import pytest
from uuid import uuid4

from app.infrastructure.db.models import (
    DBApplication,
    DBCompany,
    DBJob,
    DBMessage,
    DBRecruiter,
    DBUser,
)
from app.application.services.workflow_persistence import (
    persist_company_research,
    persist_outreach_draft,
    persist_recruiter_discovery,
    persist_ats_and_approval_flags,
)


@pytest.fixture
async def user_job_app():
    """Create user + job + application for persistence tests."""
    from app.infrastructure.db.session import async_session

    user_id = uuid4()
    job_id = uuid4()
    app_id = uuid4()

    async with async_session() as db:
        user = DBUser(
            id=user_id,
            email=f"pr_a_{user_id.hex[:8]}@example.com",
            hashed_password="x",
            role="user",
        )
        db.add(user)
        await db.flush()
        job = DBJob(
            id=job_id,
            user_id=user_id,
            role_title="Backend Engineer",
            description_raw="Python FastAPI role",
            description_normalized={"company_name": "Acme Labs"},
            status="Imported",
        )
        db.add(job)
        await db.flush()
        app = DBApplication(
            id=app_id,
            user_id=user_id,
            job_id=job_id,
            stage="Wishlist",
            workflow_state={},
        )
        db.add(app)
        await db.commit()

    return {"user_id": user_id, "job_id": job_id, "app_id": app_id}


@pytest.mark.asyncio
async def test_persist_company_recruiter_outreach(user_job_app):
    from app.infrastructure.db.session import async_session
    from sqlalchemy.future import select

    job_id = str(user_job_app["job_id"])

    async with async_session() as db:
        company = await persist_company_research(
            db,
            job_id=job_id,
            research={
                "company_name": "Acme Labs",
                "summary": "Builds APIs",
                "tech_stack": ["Python"],
            },
        )
        assert company is not None
        assert company.name == "Acme Labs"

        recruiter = await persist_recruiter_discovery(
            db,
            job_id=job_id,
            discovery={
                "recruiter_name": "Hiring Team",
                "recruiter_email": "careers@acmelabs.com",
                "confidence": 0.6,
            },
        )
        assert recruiter is not None
        assert recruiter.email == "careers@acmelabs.com"

        message = await persist_outreach_draft(
            db,
            job_id=job_id,
            draft={
                "subject_line": "Hello Acme",
                "body": "I would love to chat about the Backend Engineer role.",
            },
        )
        assert message is not None
        assert message.status == "Draft"
        assert "Hello Acme" in message.content

        await persist_ats_and_approval_flags(
            db,
            job_id=job_id,
            ats_score=88,
            requires_human_approval=True,
        )

    async with async_session() as db:
        job = (
            await db.execute(select(DBJob).where(DBJob.id == user_job_app["job_id"]))
        ).scalars().first()
        assert job.company_id is not None

        app = (
            await db.execute(
                select(DBApplication).where(DBApplication.id == user_job_app["app_id"])
            )
        ).scalars().first()
        assert app.workflow_state.get("ats_score") == 88
        assert app.workflow_state.get("requires_human_approval") is True
        assert app.stage == "Researching"

        msgs = (
            await db.execute(
                select(DBMessage).where(DBMessage.application_id == app.id)
            )
        ).scalars().all()
        assert len(msgs) == 1

        recruiters = (
            await db.execute(select(DBRecruiter).where(DBRecruiter.company_id == job.company_id))
        ).scalars().all()
        assert len(recruiters) >= 1
