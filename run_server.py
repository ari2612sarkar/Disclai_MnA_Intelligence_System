#!/usr/bin/env python
"""Run the DISCLAI server with proper signal handling."""
import uvicorn
import signal
import sys
import asyncio
from app.api.main import app

def signal_handler(sig, frame):
    print(f"Received signal {sig}, shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="debug",
        access_log=True,
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    
    try:
        asyncio.run(server.serve())
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)