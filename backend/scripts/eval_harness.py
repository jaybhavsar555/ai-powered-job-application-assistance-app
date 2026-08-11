#!/usr/bin/env python
"""Offline LLM eval harness — score resume tailoring for factual consistency.

Usage (Docker):
  docker compose exec api python scripts/eval_harness.py
  docker compose exec api python scripts/eval_harness.py --provider ollama
  docker compose exec api python scripts/eval_harness.py --provider openai

Defaults to Ollama when reachable (Docker service). Never uses mock scores —
LLM failures raise so you know credits/models are missing.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Literal, Optional

import httpx
from pydantic import BaseModel, Field

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.application.agents.resume_optimizer import ResumeOptimizerAgent
from app.infrastructure.llm.client import structured_generate, warm_ollama_model
from app.infrastructure.llm.runtime import get_llm_runtime, set_llm_provider, runtime_status
from app.core.config import get_settings

ProviderName = Literal["openai", "ollama", "mock"]


class EvalScore(BaseModel):
    factual_consistency: int = Field(
        description="0-10 how factual vs base resume (10 = no hallucinations)."
    )
    relevance: int = Field(
        description="0-10 how well it targeted the JD requirements."
    )
    formatting: int = Field(
        description="0-10 adherence to requested resume structure."
    )
    explanation: str = Field(description="Why these scores were given.")


async def _ollama_ready(base_v1: str) -> tuple[bool, list[str]]:
    native = (base_v1 or "http://ollama:11434/v1").replace("/v1", "").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{native}/api/tags")
            r.raise_for_status()
            models = [
                m.get("name") or m.get("model")
                for m in (r.json().get("models") or [])
                if m.get("name") or m.get("model")
            ]
            return True, [m for m in models if m]
    except Exception:
        return False, []


async def _pick_ollama_model(available: list[str]) -> str:
    settings = get_settings()
    preferred = (settings.OLLAMA_MODEL or "").strip()
    if preferred and preferred in available:
        return preferred
    # Prefer whatever is already pulled
    for candidate in ("qwen2.5:3b", "qwen2.5:7b", "llama3.2:3b", "llama3"):
        if candidate in available:
            return candidate
    return preferred or (available[0] if available else "qwen2.5:7b")


async def configure_provider(choice: Optional[str]) -> ProviderName:
    status = runtime_status()
    ollama_base = status.get("ollama_base_url") or "http://ollama:11434/v1"
    ready, models = await _ollama_ready(ollama_base)

    if choice == "mock":
        raise SystemExit(
            "Refusing --provider mock. Eval must use real Ollama or OpenAI "
            "so scores are not silently invented."
        )
    if choice in ("openai", "ollama"):
        provider: ProviderName = choice  # type: ignore[assignment]
    elif ready:
        provider = "ollama"
    elif status.get("openai_configured"):
        provider = "openai"
    else:
        raise SystemExit(
            "No LLM available for eval. Start Ollama (docker compose) or set "
            "OPENAI_API_KEY with credits. Mock eval is disabled."
        )

    model = None
    if provider == "ollama":
        if not ready:
            raise SystemExit(
                f"Ollama not reachable at {ollama_base}. "
                "Run: docker compose up -d ollama"
            )
        model = await _pick_ollama_model(models)
        cfg = set_llm_provider("ollama", model=model)
        warm = await warm_ollama_model(cfg)
        print(
            f"LLM provider=ollama model={cfg.model} "
            f"warmed={warm.get('warmed')} available={models[:5]}"
        )
    else:
        cfg = set_llm_provider(provider, model=model)
        print(f"LLM provider={cfg.provider} model={cfg.model}")

    if provider == "openai":
        print(
            "Note: if OpenAI returns Connection error, check billing credits — "
            "httpx often sees 429 insufficient_quota while the SDK says Connection error."
        )
    return provider


class EvalHarness:
    def __init__(self) -> None:
        self.optimizer = ResumeOptimizerAgent()

    async def evaluate_resume(
        self, base_resume: str, jd: str, tailored_resume: Dict[str, Any]
    ) -> EvalScore:
        tailored_str = json.dumps(tailored_resume, indent=2)
        prompt = dedent(
            f"""
            You are an expert LLM Evaluator for an AI recruitment platform.
            Score a tailored resume output.

            BASE RESUME (Ground Truth):
            {base_resume}

            JOB DESCRIPTION (Target):
            {jd}

            TAILORED RESUME OUTPUT:
            {tailored_str}

            Score based on:
            1. Factual Consistency: claims present in or derived from the Base Resume?
            2. Relevance: emphasizes skills relevant to the JD?
            3. Formatting: clean structured resume JSON?
            """
        ).strip()

        return await structured_generate(
            EvalScore,
            [
                {
                    "role": "system",
                    "content": "You are a strict, objective AI Evaluator. Output scoring JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
        )

    async def run(self) -> None:
        cfg = get_llm_runtime()
        print("Starting LLM Evaluation Harness...")
        print(f"Active runtime: {cfg.provider} / {cfg.model}")

        test_cases = [
            {
                "name": "Backend Role Match",
                "base_resume": "Software Engineer with 5 years of Python, Django, and PostgreSQL experience.",
                "jd": "Senior Backend Engineer. Must have Python, FastAPI, and strong SQL skills. Experience with AWS is a plus.",
                "ats_score": {"missing_skills": ["FastAPI", "AWS"]},
            },
            {
                "name": "Frontend Role Match",
                "base_resume": "Frontend Developer with 3 years of React, Next.js, and Tailwind CSS experience. Good at UI/UX.",
                "jd": "Frontend Web Developer needed. React experience required. Knowing Next.js is highly preferred. Typescript is a plus.",
                "ats_score": {"missing_skills": ["TypeScript"]},
            },
            {
                "name": "Unrelated Role (Rejection Test)",
                "base_resume": "Data Scientist with 2 years of Python, Pandas, and Machine Learning.",
                "jd": "Looking for a seasoned C++ Game Developer with Unreal Engine experience. Zero Python needed.",
                "ats_score": {"missing_skills": ["C++", "Unreal Engine"]},
            }
        ]

        results = []
        has_hallucination = False

        for i, tc in enumerate(test_cases, 1):
            print(f"\nTest Case {i}: {tc['name']}")
            print("Running Resume Optimizer...")
            
            state = {
                "resume_json": tc["base_resume"],
                "job_description": tc["jd"],
                "ats_score": tc["ats_score"],
            }

            result = await self.optimizer.run(state)
            tailored = result.get("optimized_resume") or {}
            if hasattr(tailored, "model_dump"):
                tailored = tailored.model_dump()

            print("Running LLM Evaluator...")
            score = await self.evaluate_resume(tc["base_resume"], tc["jd"], tailored)
            
            print(f"-> Consistency: {score.factual_consistency}/10 | Relevance: {score.relevance}/10 | Formatting: {score.formatting}/10")
            print(f"-> Explanation: {score.explanation}")

            if "Mock evaluator" in (score.explanation or ""):
                raise SystemExit(
                    "Eval used MOCK scores — LLM did not respond. "
                    "Fix provider (ollama/openai) and re-run. Refusing silent success."
                )
            if score.factual_consistency < 8:
                print(f"WARNING: Possible hallucination detected in {tc['name']}!")
                has_hallucination = True

            results.append({
                "test_case": tc["name"],
                "scores": {
                    "factual_consistency": score.factual_consistency,
                    "relevance": score.relevance,
                    "formatting": score.formatting,
                },
                "explanation": score.explanation,
            })

        avg_consistency = sum(r["scores"]["factual_consistency"] for r in results) / len(results)

        report = {
            "timestamp": asyncio.get_event_loop().time(),
            "provider": cfg.provider,
            "model": cfg.model,
            "average_consistency": avg_consistency,
            "passed": not has_hallucination,
            "details": results,
        }

        report_path = Path("eval_report.json")
        report_path.write_text(json.dumps(report, indent=2))
        print("\n=== Evaluation Complete ===")
        print(f"Report saved to {report_path.absolute()}")

        if has_hallucination:
            print("FAILED: Hallucinations detected (Factual Consistency < 8).")
            sys.exit(1)
        else:
            print("PASSED: No hallucinations detected.")


async def _amain(provider: Optional[str]) -> None:
    await configure_provider(provider)
    await EvalHarness().run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Resume tailor eval harness")
    parser.add_argument(
        "--provider",
        choices=("openai", "ollama"),
        default=None,
        help="LLM provider (default: ollama if reachable, else openai)",
    )
    args = parser.parse_args()
    asyncio.run(_amain(args.provider))


if __name__ == "__main__":
    main()
