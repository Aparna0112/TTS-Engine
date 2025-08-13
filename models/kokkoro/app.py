import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from handler import KokkoroHandler

app = FastAPI(title="Kokkoro TTS", version="1.0.0")
handler_instance = KokkoroHandler()

class TTSRequest(BaseModel):
    text: str
    voice: str = "default"
    speed: float = 1.0
    pitch: float = 1.0

@app.get("/")
async def root():
    return {"message": "Kokkoro TTS Model", "status": "ready"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": "kokkoro"}

@app.post("/synthesize")
async def synthesize(request: TTSRequest):
    try:
        result = await handler_instance.generate_audio(
            text=request.text,
            voice=request.voice,
            speed=request.speed,
            pitch=request.pitch
        )
        return {
            "audio_url": result["audio_url"],
            "audio_base64": result.get("audio_base64"),
            "audio_data_url": result.get("audio_data_url"),
            "model_used": "kokkoro",
            "duration": result.get("duration"),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# RunPod handler
def handler(event):
    try:
        input_data = event.get('input', {})
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(handler_instance.generate_audio(
            text=input_data.get('text', 'Hello World'),
            voice=input_data.get('voice', 'default'),
            speed=input_data.get('speed', 1.0),
            pitch=input_data.get('pitch', 1.0)
        ))
        
        return {"output": result}
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        print("Starting Kokkoro TTS on RunPod...")
        runpod.serverless.start({"handler": handler})
    else:
        print("Starting Kokkoro TTS locally...")
        uvicorn.run(app, host="0.0.0.0", port=8001)
