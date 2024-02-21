import subprocess
import time

def run_script(script):
    print(f"Running {script}...")
    return subprocess.Popen(["python", script])

if __name__ == "__main__":
    boostbot_script = 'boostbot.py'
    invitebot_script = 'invitebot.py'

    # Run both scripts as separate processes
    boostbot_process = run_script(boostbot_script)
    invitebot_process = run_script(invitebot_script)

    try:
        # Keep the main script running indefinitely
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Terminate both processes on keyboard interrupt (Ctrl+C)
        boostbot_process.terminate()
        invitebot_process.terminate()

    print("Both scripts terminated.")
