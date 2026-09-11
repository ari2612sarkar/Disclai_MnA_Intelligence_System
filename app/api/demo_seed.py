from fastapi import APIRouter
from pathlib import Path
import subprocess
import sys

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/seed")
async def seed_demo():
    script = Path("scripts/run_demo_full.py")

    if not script.exists():
        return {"status": "error", "message": "Demo script not found"}

    env = os.environ.copy()
    env.setdefault("DISCLAI_BASE_URL", env.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:8000"))

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=900,
        env=env,
    )

    return {
        "status": "success" if result.returncode == 0 else "error",
        "return_code": result.returncode,
        "output": result.stdout[-12000:],
        "errors": result.stderr[-4000:],
    }