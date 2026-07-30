import os
import yaml
from pathlib import Path

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
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)
                prompt = data.get("system_prompt", "")
                self._cache[agent_name] = prompt
                return prompt
                
        if md_path.exists():
            with open(md_path, 'r') as f:
                prompt = f.read()
                self._cache[agent_name] = prompt
                return prompt

        # Fallback empty prompt
        print(f"[PromptRegistry] Warning: No prompt found for {agent_name}")
        return "You are a helpful AI assistant."

prompt_registry = PromptRegistry()
