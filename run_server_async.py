#!/usr/bin/env python
"""Run the DISCLAI server with proper async event loop handling."""
import asyncio
import sys
import os
from app.api.main import app
import uvicorn

async def main():
    config = uvicorn.Config(
        "app.api.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="debug",
        access_log=True,
    )
    server = uvicorn.Server(config)
    
    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    
    def shutdown():
        print("Shutting down...")
        server.should_exit = True
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:
            pass  # Windows doesn't support add_signal_handler
    
    print("Starting server...")
    await server.serve()
    print("Server stopped")

if __name__ == "__main__":
    import signal
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)