"""Small provider adapters using Python's built-in HTTPS client."""
from __future__ import annotations

import json
import urllib.error
import urllib.request


def _post(url: str, headers: dict, payload: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:800]
        raise RuntimeError(f"AI service returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach the AI service: {exc.reason}") from exc


def generate_json(provider: str, api_key: str, model: str, prompt: str, base_url: str = "") -> str:
    if provider == "OpenAI":
        url = base_url or "https://api.openai.com/v1/chat/completions"
        result = _post(url, {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                       {"model": model, "temperature": 0, "response_format": {"type": "json_object"},
                        "messages": [{"role": "system", "content": "Careful procurement analyst. Follow the JSON format and never invent proposal evidence."}, {"role": "user", "content": prompt}]})
        return result["choices"][0]["message"]["content"]
    if provider == "Anthropic":
        url = base_url or "https://api.anthropic.com/v1/messages"
        result = _post(url, {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                       {"model": model, "max_tokens": 4000, "temperature": 0,
                        "system": "Careful procurement analyst. Return JSON only and never invent proposal evidence.",
                        "messages": [{"role": "user", "content": prompt}]})
        return "\n".join(part.get("text", "") for part in result.get("content", []))
    if provider == "Gemini":
        url = base_url or f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        result = _post(url, {"Content-Type": "application/json"},
                       {"contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}})
        return result["candidates"][0]["content"]["parts"][0]["text"]
    raise ValueError(f"Unsupported AI provider: {provider}")
