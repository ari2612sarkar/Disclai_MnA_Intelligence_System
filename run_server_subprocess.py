import subprocess
import sys
import time
import signal
import os

def run_server():
    """Run the server in a subprocess and keep it alive."""
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    # Run uvicorn directly as a subprocess
    proc = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app.api.main:app', 
         '--host', '127.0.0.1', '--port', '8000', '--log-level', 'debug'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    
    print(f"Server started with PID: {proc.pid}")
    
    # Read output in real-time
    try:
        for line in proc.stdout:
            print(line.rstrip())
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    run_server()