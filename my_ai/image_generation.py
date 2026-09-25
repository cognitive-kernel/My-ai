from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


IMAGE_ROOT = Path("data/images").resolve()


class ImageGenerationError(RuntimeError):
    pass


def _post_json(url: str, payload: dict, headers: dict[str, str] | None = None, timeout: int = 180) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", **(headers or {})}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ImageGenerationError(f"Image provider HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise ImageGenerationError(f"Image provider unavailable: {exc}") from exc


def _save_b64(value: str, suffix: str = ".png") -> str:
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"image_{int(time.time() * 1000)}{suffix}"
    path = IMAGE_ROOT / filename
    path.write_bytes(base64.b64decode(value))
    return str(path)


def _openai(prompt: str, size: str, quality: str) -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise ImageGenerationError("OPENAI_API_KEY is not configured.")
    model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    result = _post_json(
        "https://api.openai.com/v1/images/generations",
        {"model": model, "prompt": prompt, "size": size, "quality": quality},
        {"Authorization": f"Bearer {key}"},
    )
    data = result.get("data") or []
    if not data or not data[0].get("b64_json"):
        raise ImageGenerationError("OpenAI returned no image data.")
    return _save_b64(data[0]["b64_json"])


def _automatic1111(prompt: str, size: str, negative_prompt: str = "") -> str:
    base = os.getenv("A1111_URL", "http://127.0.0.1:7860").rstrip("/")
    width, height = (int(x) for x in size.split("x", 1))
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "steps": int(os.getenv("A1111_STEPS", "28")),
        "cfg_scale": float(os.getenv("A1111_CFG", "7")),
    }
    result = _post_json(f"{base}/sdapi/v1/txt2img", payload, timeout=300)
    data = result.get("images") or []
    if not data:
        raise ImageGenerationError("Automatic1111 returned no image data.")
    return _save_b64(data[0])


def generate_image(prompt: str, size: str = "1024x1024", quality: str = "high", negative_prompt: str = "") -> dict:
    prompt = prompt.strip()
    if not prompt:
        raise ImageGenerationError("Prompt is required.")
    provider = os.getenv("IMAGE_PROVIDER", "auto").strip().lower()
    if provider == "auto":
        provider = "openai" if os.getenv("OPENAI_API_KEY", "").strip() else "automatic1111"
    if provider in {"openai", "gpt", "gpt-image"}:
        path = _openai(prompt, size, quality)
        provider = "openai"
    elif provider in {"automatic1111", "a1111", "stable-diffusion"}:
        path = _automatic1111(prompt, size, negative_prompt)
        provider = "automatic1111"
    else:
        raise ImageGenerationError("IMAGE_PROVIDER must be auto, openai, or automatic1111.")
    return {"provider": provider, "path": path, "filename": Path(path).name, "prompt": prompt}
