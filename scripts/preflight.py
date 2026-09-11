#!/usr/bin/env python
"""DISCLAI local preflight: static checks before the final manual run."""
from __future__ import annotations

import importlib.util
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_MODULES = [
    "fastapi", "uvicorn", "pydantic", "pydantic_settings", "sqlalchemy",
    "httpx", "tenacity", "fitz", "jinja2", "requests", "rank_bm25",
]

def main() -> int:
    print("=" * 64)
    print("DISCLAI FINAL LOCAL PREFLIGHT")
    print("=" * 64)
    failed = False

    print("\n1. Required Python modules")
    for name in REQUIRED_MODULES:
        ok = importlib.util.find_spec(name) is not None
        print(f"   [{'OK' if ok else 'MISSING'}] {name}")
        failed |= not ok

    print("\n2. Required project files")
    required = [
        "app/api/main.py", "app/llm/provider.py",
        "app/comparison/engine.py", "app/comparison/service.py",
        "app/comparison/verdict.py", "app/comparison/recommendations.py",
        "app/comparison/disclosure.py", "app/static/assets/app.js",
        "app/static/assets/styles.css", "app/templates/base.html",
        "scripts/test_pipeline.py", "scripts/test_phase2.py",
        "scripts/evaluation.py", "scripts/demo_e2e.py",
        "render.yaml", ".env.example",
    ]
    for rel in required:
        ok = (ROOT / rel).exists()
        print(f"   [{'OK' if ok else 'MISSING'}] {rel}")
        failed |= not ok

    print("\n3. Environment")
    env_file = ROOT / ".env"
    if env_file.exists():
        print("   [OK] .env exists locally")
    else:
        print("   [WARN] .env not found; copy .env.example to .env for real HF testing")

    print("\n4. Port 8000")
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", 8000))
        print("   [OK] Port 8000 is available")
    except OSError:
        print("   [INFO] Port 8000 is already in use; stop the existing DISCLAI server before demo_e2e.py")
    finally:
        sock.close()

    print("\n5. Secret hygiene")
    example = (ROOT / ".env.example").read_text(errors="ignore")
    if "hf_" in example.lower():
        print("   [FAIL] .env.example appears to contain a Hugging Face token")
        failed = True
    else:
        print("   [OK] .env.example contains no HF token")

    print("\n" + "=" * 64)
    if failed:
        print("PREFLIGHT: FAILED — fix the items marked MISSING/FAIL.")
        return 1
    print("PREFLIGHT: PASS")
    print("=" * 64)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
