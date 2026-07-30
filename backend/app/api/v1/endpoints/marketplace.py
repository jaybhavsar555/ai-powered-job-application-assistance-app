from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List

from app.api.dependencies import get_current_user
from app.domain.models import User
from app.marketplace import list_plugin_manifests, set_plugin_enabled

router = APIRouter()


class MarketplacePlugin(BaseModel):
    id: str
    name: str
    title: str
    description: str
    version: str
    author: str
    enabled: bool
    registered: bool


class ToggleRequest(BaseModel):
    enabled: bool


@router.get("/plugins", response_model=List[MarketplacePlugin])
async def list_plugins(current_user: User = Depends(get_current_user)):
    return [MarketplacePlugin(**m) for m in list_plugin_manifests()]


@router.post("/plugins/{plugin_id}/toggle", response_model=MarketplacePlugin)
async def toggle_plugin(
    plugin_id: str,
    data: ToggleRequest,
    current_user: User = Depends(get_current_user),
):
    if (current_user.role or "user") not in ("admin", "demo"):
        raise HTTPException(
            status_code=403,
            detail="Only admin (or demo) can enable marketplace plugins",
        )
    try:
        result = set_plugin_enabled(plugin_id, data.enabled)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    for m in list_plugin_manifests():
        if m["id"] == plugin_id:
            return MarketplacePlugin(**m)
    return MarketplacePlugin(
        id=plugin_id,
        name=result["name"],
        title=result["name"],
        description="",
        version="0.1.0",
        author="community",
        enabled=result["enabled"],
        registered=result["registered"],
    )
