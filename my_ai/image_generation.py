from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .settings_store import get_bool, get_int, get_setting
from .access_policy import assert_mutation_allowed


IMAGE_ROOT = Path("data/images").resolve()


class ImageGenerationError(RuntimeError):
    pass


def _setting(name: str, env_name: str, default: str) -> str:
    value = str(get_setting(name, os.getenv(env_name, default)) or "").strip()
    return value or default


def _post_json(url: str, payload: dict, timeout: int = 300) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ImageGenerationError(f"Local image provider HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise ImageGenerationError(f"Local image provider unavailable: {exc}") from exc


def _get_json(url: str, timeout: int = 15) -> dict | list:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ImageGenerationError(f"Local image provider HTTP {exc.code}: {detail[:1000]}") from exc
    except urllib.error.URLError as exc:
        raise ImageGenerationError(f"Local image provider unavailable: {exc}") from exc


def _save_b64(value: str, suffix: str = ".png") -> str:
    assert_mutation_allowed("generated image")
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    filename = f"image_{int(time.time() * 1000)}{suffix}"
    path = IMAGE_ROOT / filename
    raw = value.split(",", 1)[-1]
    path.write_bytes(base64.b64decode(raw))
    return str(path)


def _local_url() -> str:
    url = _setting("image.url", "A1111_URL", "http://127.0.0.1:7860").rstrip("/")
    if not url.startswith(("http://127.0.0.1:", "http://localhost:", "http://[::1]:")):
        raise ImageGenerationError("برای حالت آفلاین، آدرس موتور تصویر باید فقط روی localhost/127.0.0.1 باشد.")
    return url


def local_image_status() -> dict:
    base = _local_url()
    options = _get_json(f"{base}/sdapi/v1/options")
    models = _get_json(f"{base}/sdapi/v1/sd-models")
    current = options.get("sd_model_checkpoint") if isinstance(options, dict) else None
    names = [str(x.get("title") or x.get("model_name") or "") for x in (models if isinstance(models, list) else [])]
    return {"connected": True, "url": base, "model": current, "models": [x for x in names if x]}


def _automatic1111(prompt: str, size: str, negative_prompt: str = "") -> str:
    base = _local_url()
    try:
        width, height = (int(x) for x in size.lower().split("x", 1))
    except Exception as exc:
        raise ImageGenerationError("اندازه تصویر باید مثل 1024x1024 باشد.") from exc
    if not 256 <= width <= 2048 or not 256 <= height <= 2048:
        raise ImageGenerationError("عرض و ارتفاع تصویر باید بین 256 و 2048 باشند.")

    steps = max(1, min(150, get_int("image.steps", int(os.getenv("A1111_STEPS", "32")))))
    cfg = max(1.0, min(30.0, float(get_setting("image.cfg", os.getenv("A1111_CFG", "7")))))
    sampler = _setting("image.sampler", "A1111_SAMPLER", "DPM++ 2M Karras")
    model = str(get_setting("image.model", os.getenv("A1111_MODEL", "")) or "").strip()
    use_hires = get_bool("image.hires", True)
    hires_scale = max(1.0, min(2.0, float(get_setting("image.hires_scale", "1.5"))))
    denoise = max(0.1, min(1.0, float(get_setting("image.denoise", "0.35"))))

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt or str(get_setting("image.negative_prompt", "")),
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg,
        "sampler_name": sampler,
        "save_images": False,
    }
    if use_hires:
        payload.update({
            "enable_hr": True,
            "hr_scale": hires_scale,
            "hr_upscaler": _setting("image.hr_upscaler", "A1111_HR_UPSCALER", "Latent"),
            "denoising_strength": denoise,
        })
    if model:
        payload["override_settings"] = {
            "sd_model_checkpoint": model,
            "override_settings_restore_afterwards": True,
        }

    result = _post_json(f"{base}/sdapi/v1/txt2img", payload, timeout=900)
    data = result.get("images") or []
    if not data:
        raise ImageGenerationError("Automatic1111 تصویر تولید نکرد.")
    return _save_b64(data[0])


def generate_image(prompt: str, size: str | None = None, quality: str = "high", negative_prompt: str = "") -> dict:
    prompt = prompt.strip()
    if not prompt:
        raise ImageGenerationError("Prompt is required.")
    if not get_bool("image.enabled", True):
        raise ImageGenerationError("تولید تصویر آفلاین در تنظیمات غیرفعال است.")

    # Deliberately no cloud provider exists in this path.
    provider = str(get_setting("image.provider", "automatic1111")).strip().lower()
    if provider not in {"automatic1111", "a1111", "stable-diffusion"}:
        raise ImageGenerationError("فقط موتور محلی Automatic1111 برای حالت آفلاین مجاز است.")

    final_size = (size or str(get_setting("image.default_size", "1024x1024"))).strip()
    path = _automatic1111(prompt, final_size, negative_prompt)
    return {
        "provider": "automatic1111-local",
        "path": path,
        "filename": Path(path).name,
        "prompt": prompt,
        "size": final_size,
    }
