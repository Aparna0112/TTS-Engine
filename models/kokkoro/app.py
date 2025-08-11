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
        
        request = TTSRequest(**input_data)
        result = loop.run_until_complete(handler_instance.generate_audio(
            text=request.text,
            voice=request.voice,
            speed=request.speed,
            pitch=request.pitch
        ))
        
        return {"output": result}
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if os.getenv('RUNPOD_ENDPOINT_ID'):
        import runpod
        runpod.serverless.start({"handler": handler})
    else:
        uvicorn.run(app, host="0.0.0.0", port=8001)
