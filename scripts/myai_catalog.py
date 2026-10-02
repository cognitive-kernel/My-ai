#!/usr/bin/env python3
"""Command-line management for the LLM provider/model catalog.

Examples:
  python scripts/myai_catalog.py providers list
  python scripts/myai_catalog.py providers add --name local --protocol openai-compatible --endpoint http://127.0.0.1:8000/v1
  python scripts/myai_catalog.py providers enable --id 1
  python scripts/myai_catalog.py providers health --id 1
  python scripts/myai_catalog.py models list
  python scripts/myai_catalog.py models add --provider-id 1 --model-id my-model
  python scripts/myai_catalog.py models enable --provider-id 1 --model-id my-model
"""
from __future__ import annotations

import argparse
import json
import time
import httpx

from my_ai.provider_catalog import (
    delete_model, delete_provider, list_models, list_providers, upsert_model, upsert_provider,
)


def emit(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def provider_health(provider_id: int) -> dict:
    provider = next((x for x in list_providers() if int(x["id"]) == provider_id), None)
    if not provider:
        raise SystemExit(f"provider {provider_id} not found")
    started = time.perf_counter()
    try:
        response = httpx.get(
            str(provider["endpoint"]).rstrip("/") + "/models",
            timeout=float(provider.get("timeout_seconds") or 30),
        )
        response.raise_for_status()
        return {"provider_id": provider_id, "healthy": True, "status_code": response.status_code,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2)}
    except Exception as exc:
        return {"provider_id": provider_id, "healthy": False,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2), "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="My-AI provider/model catalog administration")
    sub = parser.add_subparsers(dest="group", required=True)

    providers = sub.add_parser("providers")
    psub = providers.add_subparsers(dest="action", required=True)
    psub.add_parser("list")
    add = psub.add_parser("add")
    add.add_argument("--name", required=True)
    add.add_argument("--protocol", default="openai-compatible")
    add.add_argument("--endpoint", required=True)
    add.add_argument("--auth-type", default="none")
    add.add_argument("--secret", default="")
    add.add_argument("--version", default="")
    add.add_argument("--timeout", type=float, default=30)
    for name in ("enable", "disable", "delete", "health"):
        cmd = psub.add_parser(name)
        cmd.add_argument("--id", type=int, required=True)

    models = sub.add_parser("models")
    msub = models.add_subparsers(dest="action", required=True)
    list_cmd = msub.add_parser("list")
    list_cmd.add_argument("--provider-id", type=int)
    madd = msub.add_parser("add")
    madd.add_argument("--provider-id", type=int, required=True)
    madd.add_argument("--model-id", required=True)
    madd.add_argument("--tasks", default="")
    madd.add_argument("--context-length", type=int)
    madd.add_argument("--priority", type=int, default=100)
    madd.add_argument("--version", default="")
    for name in ("enable", "disable", "delete"):
        cmd = msub.add_parser(name)
        cmd.add_argument("--provider-id", type=int, required=True)
        cmd.add_argument("--model-id", required=True)

    args = parser.parse_args()
    if args.group == "providers":
        if args.action == "list":
            emit(list_providers())
        elif args.action == "add":
            emit(upsert_provider(name=args.name, protocol=args.protocol, endpoint=args.endpoint,
                                 auth_type=args.auth_type, secret=args.secret, version=args.version,
                                 timeout_seconds=args.timeout, enabled=True))
        elif args.action in {"enable", "disable"}:
            current = next((x for x in list_providers() if int(x["id"]) == args.id), None)
            if not current:
                raise SystemExit(f"provider {args.id} not found")
            emit(upsert_provider(name=current["name"], protocol=current["protocol"], endpoint=current["endpoint"],
                                 auth_type=current["auth_type"], version=current.get("version", ""),
                                 timeout_seconds=float(current.get("timeout_seconds") or 30),
                                 capabilities=current.get("capabilities", {}), enabled=args.action == "enable"))
        elif args.action == "delete":
            delete_provider(args.id)
            emit({"deleted": args.id})
        else:
            emit(provider_health(args.id))
    else:
        if args.action == "list":
            emit(list_models(provider_id=args.provider_id))
        elif args.action == "add":
            emit(upsert_model(provider_id=args.provider_id, model_id=args.model_id,
                              tasks=[x.strip() for x in args.tasks.split(",") if x.strip()],
                              context_length=args.context_length, priority=args.priority,
                              version=args.version, enabled=True))
        elif args.action in {"enable", "disable"}:
            current = next((x for x in list_models(provider_id=args.provider_id)
                            if x["model_id"] == args.model_id), None)
            if not current:
                raise SystemExit(f"model {args.provider_id}/{args.model_id} not found")
            emit(upsert_model(provider_id=args.provider_id, model_id=args.model_id,
                              tasks=current.get("tasks", []), context_length=current.get("context_length"),
                              limits=current.get("limits", {}), priority=int(current.get("priority", 100)),
                              version=current.get("version", ""), enabled=args.action == "enable"))
        else:
            delete_model(args.provider_id, args.model_id)
            emit({"deleted": {"provider_id": args.provider_id, "model_id": args.model_id}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
