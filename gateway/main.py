import os

def handler(event):
    """Ultra-minimal gateway that just echoes back"""
    return {
        "output": {
            "message": "Ultra-minimal gateway working!",
            "echo": event
        }
    }

if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        runpod.serverless.start({"handler": handler})
    else:
        print("Local mode")
