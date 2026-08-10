"""PR D — inbox summary, job ingest → wishlist, message send honesty, prod guards."""

import pytest
from uuid import uuid4

from app.infrastructure.db.models import (
    DBApplication,
    DBJob,
    DBMessage,
    DBRecruiter,
    DBCompany,
    DBUser,
)
from app.schemas.job import JobCreate
from app.application.services.job import JobService
from app.application.services.mail import MailService
from app.core.config import Settings


@pytest.mark.asyncio
async def test_ingest_inbox_and_message_send(monkeypatch):
    from app.infrastructure.db.session import async_session
    from sqlalchemy.future import select
    from app.api.v1.endpoints.inbox import get_inbox_summary
    from app.api.v1.endpoints.messages import send_message
    from app.domain.models import User
    from app.schemas.job import NormalizedJob

    user_id = uuid4()

    async def fake_normalize(self, raw_description, title="", company=""):
        return NormalizedJob(
            role_title=title or "Staff Engineer",
            company_name=company or "Acme",
            required_skills=["Python"],
            nice_to_have_skills=[],
            years_of_experience=5,
            responsibilities=["Build APIs"],
            benefits=[],
        )

    monkeypatch.setattr(
        "app.application.agents.job_intake.JobIntakeAgent.extract_and_normalize",
        fake_normalize,
    )

    async with async_session() as db:
        db.add(
            DBUser(
                id=user_id,
                email=f"prd_{user_id.hex[:8]}@example.com",
                hashed_password="x",
                role="user",
            )
        )
        await db.commit()

        service = JobService(db)
        job = await service.ingest_job(
            user_id,
            JobCreate(
                role_title="Staff Engineer",
                company_name="Acme",
                description_raw="We need a Staff Engineer with Python and FastAPI.",
            ),
        )
        assert job.role_title == "Staff Engineer"
        apps = (
            await db.execute(select(DBApplication).where(DBApplication.job_id == job.id))
        ).scalars().all()
        assert len(apps) == 1
        assert apps[0].stage == "Wishlist"

        # Enrich for inbox next_action
        apps[0].workflow_state = {**(apps[0].workflow_state or {}), "ats_score": 81}
        job.description_normalized = {
            **(job.description_normalized or {}),
            "company_name": "Orbit",
        }
        await db.commit()

        user = User(id=user_id, email="prd@example.com", auth_provider="local")
        summary = await get_inbox_summary(db=db, current_user=user)
        assert summary["wishlist_count"] >= 1
        assert summary["next_action"] is not None
        assert summary["next_action"]["ats_score"] == 81

        company_id = uuid4()
        recruiter_id = uuid4()
        message_id = uuid4()
        db.add(DBCompany(id=company_id, name="Orbit", research_data={}))
        await db.flush()
        db.add(
            DBRecruiter(
                id=recruiter_id,
                company_id=company_id,
                name="Hiring",
                email="hiring@orbit.example",
            )
        )
        job.company_id = company_id
        db.add(
            DBMessage(
                id=message_id,
                application_id=apps[0].id,
                recruiter_id=recruiter_id,
                content="Hello Orbit team",
                message_type="ColdEmail",
                status="Draft",
            )
        )
        await db.commit()

        # Force no-SMTP path regardless of host .env SMTP settings
        monkeypatch.setattr(
            MailService,
            "smtp_configured",
            property(lambda self: False),
        )

        result = await send_message(message_id=message_id, db=db, current_user=user)
        assert result["success"] is False
        assert result["smtp_configured"] is False
        assert "mailto:" in result["mailto"]

        msg = (
            await db.execute(select(DBMessage).where(DBMessage.id == message_id))
        ).scalars().first()
        assert msg.status == "Draft"


def test_mail_service_blocks_mock_in_production(monkeypatch):
    settings = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a" * 40,
        CORS_ORIGINS="https://app.example.com",
        SMTP_HOST="",
    )
    monkeypatch.setattr("app.application.services.mail.get_settings", lambda: settings)
    mail = MailService()
    with pytest.raises(RuntimeError, match="SMTP is not configured"):
        mail.send_email("a@b.com", "Hi", "Body")


def test_production_boot_rejects_weak_secret():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="short",
            CORS_ORIGINS="https://app.example.com",
        ).validate_for_boot()


def test_production_boot_rejects_star_cors():
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 40,
            CORS_ORIGINS="*",
        ).validate_for_boot()


def test_llm_telemetry_records_mock_fallback():
    from app.infrastructure.llm import telemetry as tel

    before = tel.telemetry_snapshot()["mock_fallbacks"]
    tel.record_mock_fallback(reason="unit_test", provider="mock", model="n/a")
    after = tel.telemetry_snapshot()
    assert after["mock_fallbacks"] == before + 1
    assert after["by_reason"].get("unit_test", 0) >= 1


def test_demo_auth_disabled_in_production():
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a" * 40,
        CORS_ORIGINS="https://app.example.com",
    )
    assert s.demo_auth_enabled is False
    assert s.seed_dev_users_enabled is False
