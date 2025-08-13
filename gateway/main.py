import os

def handler(event):
    """Gateway handler based on working Kokkoro pattern"""
    try:
        print(f"Gateway received event: {event}")
        
        input_data = event.get('input', {})
        
        if not input_data:
            input_data = event
        
        print(f"Gateway input data: {input_data}")
        
        # Simple test without external calls
        return {
            "output": {
                "message": "Gateway is working!",
                "received_input": input_data,
                "status": "success",
                "model": "gateway"
            }
        }
        
    except Exception as e:
        print(f"Gateway error: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        print("Starting Gateway on RunPod...")
        print(f"RunPod Endpoint ID: {os.getenv('RUNPOD_ENDPOINT_ID')}")
        runpod.serverless.start({"handler": handler})
    else:
        print("Starting Gateway locally...")
