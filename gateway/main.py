import os

def handler(event):
    """Minimal working handler"""
    return {
        "output": {
            "message": "Gateway is alive!",
            "input_received": event.get("input", {}),
            "status": "working"
        }
    }

if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        print("Starting minimal gateway...")
        runpod.serverless.start({"handler": handler})
