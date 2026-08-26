#!/usr/bin/env python3
"""LLM field extractor for Legally Subjective (Module 2b).

Talks to any OpenAI-compatible chat-completions endpoint (base URL, model
and API key come from the environment — see .env.example). The prompt is
frozen here so that every run — ours or a replicator's — asks the same
questions in the same words (MANIFEST R9).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

EXTRACTION_SYSTEM_PROMPT = (
    "You are a precise legal data extraction assistant. You extract "
    "structured fields from US appellate court opinions. You never invent "
    "information: if a field is not determinable from the text, you return "
    "null for it. You answer with strict JSON only, no commentary."
)

EXTRACTION_USER_TEMPLATE = """Extract the following fields from this New York
appellate decision (criminal appeal). Answer as strict JSON:

{{
  "facts": "3-5 sentence factual summary: parties, the crime, what happened "
           "at trial, and the procedural posture of the appeal. You MUST NOT "
           "reveal or hint at the appellate outcome (affirmed/reversed/etc.).",
  "charge": "the conviction(s) under appeal, as stated in the text "
            "(e.g. 'criminal possession of a weapon in the second degree'); "
            "null if not determinable",
  "crime_type": "exactly one of: violent, drug, property, financial, "
                "sexual, weapons, dui_traffic, other",
  "defendant_gender": "male, female, or unknown (only if explicitly stated "
                      "or unambiguous from the text)",
  "outcome_check": "the single main disposition of the appeal, exactly one "
                   "of: affirmed, reversed, vacated, modified, dismissed, "
                   "mixed, unknown"
}}

Decision text (possibly truncated):
"""


class LLMExtractor:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.base_url = (os.environ.get(cfg["base_url_env"],
                                        cfg["default_base_url"])).rstrip("/")
        self.model = os.environ.get(cfg["model_env"], cfg["default_model"])
        self.api_key = os.environ.get(cfg["api_key_env"], "")
        self.temperature = float(cfg.get("temperature", 0.0))
        self.max_output_tokens = int(cfg.get("max_output_tokens", 700))
        self.timeout = float(cfg.get("timeout_seconds", 90))
        self.max_retries = int(cfg.get("max_retries", 3))
        if not self.api_key:
            raise RuntimeError(
                f"missing API key: set ${cfg['api_key_env']} "
                f"(see .env.example)")

    @property
    def backend_name(self) -> str:
        return f"openai-compatible:{self.model}@{self.base_url}"

    def extract(self, case_text: str, max_chars: int) -> dict[str, Any]:
        """Run the frozen extraction prompt on one decision."""
        prompt = (EXTRACTION_USER_TEMPLATE
                  + case_text[:max_chars].strip())
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    json=payload, headers=headers, timeout=self.timeout)
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    return parse_json_block(content)
                if resp.status_code in (429, 500, 502, 503, 504):
                    last_error = RuntimeError(f"HTTP {resp.status_code}")
                else:
                    raise RuntimeError(
                        f"LLM endpoint error {resp.status_code}: "
                        f"{resp.text[:200]}")
            except requests.RequestException as exc:
                last_error = exc
            if attempt < self.max_retries:
                time.sleep(3 * attempt)
        raise RuntimeError(f"LLM extraction failed: {last_error}")


def parse_json_block(content: str) -> dict[str, Any]:
    """Parse a JSON object from a model answer (tolerates code fences)."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model answer: {content[:200]}")
    return json.loads(content[start:end + 1])
