"""Resume Studio list/detail — real versions only, no mock ATS."""

import pytest
from uuid import uuid4

from app.infrastructure.db.models import (
    DBApplication,
    DBJob,
    DBResumeVersion,
    DBUser,
)
from app.application.services.resume_studio import ResumeStudioService


@pytest.fixture
async def studio_app():
    from app.infrastructure.db.session import async_session

    user_id = uuid4()
    job_id = uuid4()
    app_id = uuid4()
    ver_id = uuid4()

    async with async_session() as db:
        user = DBUser(
            id=user_id,
            email=f"studio_{user_id.hex[:8]}@example.com",
            hashed_password="x",
            role="user",
        )
        db.add(user)
        await db.flush()
        job = DBJob(
            id=job_id,
            user_id=user_id,
            role_title="Backend Engineer",
            description_raw="Need FastAPI",
            description_normalized={"company_name": "Nimbus"},
            status="active",
        )
        db.add(job)
        await db.flush()
        app = DBApplication(
            id=app_id,
            user_id=user_id,
            job_id=job_id,
            stage="Researching",
            workflow_state={
                "ats_score": 78,
                "missing_skills": ["Kubernetes"],
                "matching_skills": ["FastAPI"],
                "ats_recommendation": "Add K8s to ops bullets.",
                "apply_package": {
                    "folder": "/tmp/not-real",
                    "base_resume": "/tmp/base.pdf",
                    "files": {},
                },
            },
        )
        db.add(app)
        await db.flush()
        ver = DBResumeVersion(
            id=ver_id,
            application_id=app_id,
            tailored_content={
                "summary": "Tailored for Nimbus",
                "added_keywords": ["FastAPI"],
            },
            ats_score=78,
            feedback=[],
        )
        db.add(ver)
        await db.commit()

    return {"user_id": user_id, "app_id": app_id, "ver_id": ver_id, "job_id": job_id}


@pytest.mark.asyncio
async def test_studio_list_and_detail(studio_app):
    from app.infrastructure.db.session import async_session

    async with async_session() as db:
        service = ResumeStudioService(db)
        data = await service.list_studio(studio_app["user_id"])
        assert data["count"] >= 1
        hit = next(i for i in data["items"] if i["id"] == str(studio_app["ver_id"]))
        assert hit["company"] == "Nimbus"
        assert hit["ats_score"] == 78
        assert hit["approved"] is True
        assert hit["has_package"] is False
        assert "Kubernetes" in hit["missing_skills"]

        detail = await service.get_studio_detail(
            studio_app["user_id"], str(studio_app["ver_id"])
        )
        assert detail["ats"]["score"] == 78
        assert "Tailored for Nimbus" in detail["tailored"]["preview"]
        assert detail["downloads"] == {}
        assert "original" in detail and "text" in detail["original"]
