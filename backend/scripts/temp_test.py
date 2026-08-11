import asyncio
from app.infrastructure.db.session import SessionLocal
from app.application.services.apply_prefs import ApplyPrefsService
from sqlalchemy.future import select
from app.domain.models import User

async def test():
    async with SessionLocal() as db:
        user = (await db.execute(select(User))).scalars().first()
        res = await ApplyPrefsService(db).save(user.id, {'apply_mode': 'auto_apply', 'auto_consent': True})
        print(res)

asyncio.run(test())
