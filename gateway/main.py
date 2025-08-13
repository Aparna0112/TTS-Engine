import os

def handler(event):
    return {
        "output": {
            "message": "Minimal gateway working!",
            "received": event.get("input", {})
        }
    }

if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        runpod.serverless.start({"handler": handler})
