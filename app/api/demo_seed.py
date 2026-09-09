from fastapi import APIRouter
from pathlib import Path
import subprocess
import sys

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/seed")
async def seed_demo():
    script = Path("scripts/demo_e2e.py")

    if not script.exists():
        return {"status": "error", "message": "Demo script not found"}

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=900,
    )

    return {
        "status": "success" if result.returncode == 0 else "error",
        "return_code": result.returncode,
        "output": result.stdout[-12000:],
        "errors": result.stderr[-4000:],
    }