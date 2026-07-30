"""
Agent Marketplace — YAML plugin manifests that register optional agents at runtime.
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.application.agents.registry import agent_registry

PLUGINS_DIR = Path(__file__).parent / "plugins"


def _load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def list_plugin_manifests() -> List[Dict[str, Any]]:
    manifests: List[Dict[str, Any]] = []
    if not PLUGINS_DIR.exists():
        return manifests
    for path in sorted(PLUGINS_DIR.glob("*.yaml")):
        data = _load_yaml(path)
        name = data.get("name") or path.stem
        enabled = bool(data.get("enabled", False))
        registered = name in agent_registry._agents
        manifests.append(
            {
                "id": path.stem,
                "name": name,
                "title": data.get("title") or name,
                "description": data.get("description") or "",
                "version": data.get("version") or "0.1.0",
                "author": data.get("author") or "community",
                "enabled": enabled,
                "registered": registered,
                "entry": data.get("entry"),
                "path": str(path),
            }
        )
    return manifests


def set_plugin_enabled(plugin_id: str, enabled: bool) -> Dict[str, Any]:
    path = PLUGINS_DIR / f"{plugin_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Plugin '{plugin_id}' not found")
    data = _load_yaml(path)
    data["enabled"] = enabled
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    name = data.get("name") or plugin_id
    if enabled:
        _import_entry(data.get("entry"))
    else:
        agent_registry._agents.pop(name, None)

    return {
        "id": plugin_id,
        "name": name,
        "enabled": enabled,
        "registered": name in agent_registry._agents,
    }


def _import_entry(entry: Optional[str]) -> None:
    if not entry:
        return
    # entry like "app.marketplace.plugins.skill_gap_agent"
    importlib.import_module(entry)


def load_enabled_plugins() -> List[str]:
    loaded: List[str] = []
    for m in list_plugin_manifests():
        if not m.get("enabled"):
            continue
        try:
            _import_entry(m.get("entry"))
            loaded.append(m["name"])
        except Exception as exc:
            print(f"[Marketplace] Failed to load {m['id']}: {exc}")
    return loaded
