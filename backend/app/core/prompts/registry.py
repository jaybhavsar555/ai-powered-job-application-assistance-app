import yaml
from pathlib import Path
from typing import Optional

class PromptRegistry:
    """
    Loads and serves system prompts from YAML or Markdown files.
    Allows for easy version control and modification of agent personalities.
    """
    def __init__(self):
        self.prompts_dir = Path(__file__).parent
        self._cache = {}

    def get_prompt(self, agent_name: str) -> str:
        if agent_name in self._cache:
            return self._cache[agent_name]

        # Look for YAML or MD files
        yaml_path = self.prompts_dir / f"{agent_name}.yaml"
        md_path = self.prompts_dir / f"{agent_name}.md"

        if yaml_path.exists():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                prompt = data.get("system_prompt", "")
                self._cache[agent_name] = prompt
                return prompt
                
        if md_path.exists():
            with open(md_path, 'r', encoding='utf-8') as f:
                prompt = f.read()
                self._cache[agent_name] = prompt
                return prompt

        # Fallback empty prompt
        print(f"[PromptRegistry] Warning: No prompt found for {agent_name}")
        return "You are a helpful AI assistant."

    def set_prompt(self, agent_name: str, prompt: str, *, persist: bool = True) -> str:
        """Update in-memory prompt; optionally write back to YAML for local dev."""
        cleaned = (prompt or "").strip()
        if not cleaned:
            raise ValueError("Prompt cannot be empty")
        self._cache[agent_name] = cleaned
        if persist:
            yaml_path = self.prompts_dir / f"{agent_name}.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    {"system_prompt": cleaned},
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    width=100,
                )
        return cleaned

    def invalidate(self, agent_name: Optional[str] = None) -> None:
        if agent_name:
            self._cache.pop(agent_name, None)
        else:
            self._cache.clear()


prompt_registry = PromptRegistry()
