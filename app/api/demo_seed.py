from fastapi import APIRouter, BackgroundTasks
from pathlib import Path
import os
import subprocess
import sys

router = APIRouter(prefix="/api/demo", tags=["demo"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "run_demo_full.py"


def run_demo():
    if not SCRIPT.exists():
        print(f"Demo script not found: {SCRIPT}")
        return

    env = os.environ.copy()

    # IMPORTANT:
    # run_demo_full.py must call the live Render URL from the background task.
    base_url = (
        env.get("DISCLAI_BASE_URL")
        or env.get("RENDER_EXTERNAL_URL")
        or "http://127.0.0.1:8000"
    )

    env["DISCLAI_BASE_URL"] = base_url

    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            timeout=900,
            env=env,
            cwd=str(PROJECT_ROOT),
        )

        print("========== DISCLAI DEMO ==========")
        print(result.stdout[-12000:])
        if result.stderr:
            print("========== DEMO ERRORS ==========")
            print(result.stderr[-12000:])
        print("========== DEMO FINISHED ==========")

    except Exception as exc:
        print(f"Demo execution failed: {exc}")


@router.post("/seed")
async def seed_demo(background_tasks: BackgroundTasks):
    if not SCRIPT.exists():
        return {
            "status": "error",
            "message": f"Demo script not found: {SCRIPT}",
        }

    background_tasks.add_task(run_demo)

    return {
        "status": "started",
        "message": "Northstar vs Vertex demo seeding started in background.",
    }
