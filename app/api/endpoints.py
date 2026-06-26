import asyncio
import time
from fastapi import APIRouter, HTTPException, Query, Response, Request, Depends
from app.api.models import TTSRequest
from app.core.tts_engine import tts_engine
from app.config import settings
from app.auth import verify_api_key_and_rate_limit
from app.database import log_request

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "device": tts_engine.device,
        "pipelines_loaded": list(tts_engine.pipelines.keys())
    }

@router.post("/tts")
async def generate_tts(
    tts_request: TTSRequest,
    request: Request,
    client_info: dict = Depends(verify_api_key_and_rate_limit)
):
    ip_address = request.client.host if request.client else "unknown"
    
    if not tts_request.text.strip():
        log_request(
            api_key_id=client_info["id"],
            api_key_name=client_info["name"],
            endpoint="POST /tts",
            ip_address=ip_address,
            status_code=400,
            characters_count=0,
            voice=tts_request.voice,
            duration_seconds=0.0,
            error_message="Text parameter cannot be empty"
        )
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty")
        
    start_time = time.time()
    try:
        # Run heavy TTS synthesis in a thread pool to avoid blocking the event loop
        wav_bytes = await asyncio.to_thread(
            tts_engine.synthesize,
            text=tts_request.text,
            voice=tts_request.voice,
            speed=tts_request.speed,
            lang_code=tts_request.lang_code
        )
        duration = time.time() - start_time
        
        log_request(
            api_key_id=client_info["id"],
            api_key_name=client_info["name"],
            endpoint="POST /tts",
            ip_address=ip_address,
            status_code=200,
            characters_count=len(tts_request.text),
            voice=tts_request.voice,
            duration_seconds=duration
        )
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        duration = time.time() - start_time
        log_request(
            api_key_id=client_info["id"],
            api_key_name=client_info["name"],
            endpoint="POST /tts",
            ip_address=ip_address,
            status_code=500,
            characters_count=len(tts_request.text),
            voice=tts_request.voice,
            duration_seconds=duration,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"TTS generation error: {str(e)}")

@router.get("/tts")
async def generate_tts_get(
    request: Request,
    text: str = Query(..., description="Text to convert to speech"),
    voice: str = Query(None, description="Voice to use"),
    speed: float = Query(None, description="Speech speed modifier (0.5 to 2.0)"),
    lang_code: str = Query(None, description="Language code (e.g. a, b)"),
    client_info: dict = Depends(verify_api_key_and_rate_limit)
):
    ip_address = request.client.host if request.client else "unknown"
    
    # Use defaults if query params are not provided
    voice = voice or settings.DEFAULT_VOICE
    speed = speed if speed is not None else settings.DEFAULT_SPEED
    lang_code = lang_code or settings.DEFAULT_LANG
    
    if not text.strip():
        log_request(
            api_key_id=client_info["id"],
            api_key_name=client_info["name"],
            endpoint="GET /tts",
            ip_address=ip_address,
            status_code=400,
            characters_count=0,
            voice=voice,
            duration_seconds=0.0,
            error_message="Text parameter cannot be empty"
        )
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty")
        
    start_time = time.time()
    try:
        wav_bytes = await asyncio.to_thread(
            tts_engine.synthesize,
            text=text,
            voice=voice,
            speed=speed,
            lang_code=lang_code
        )
        duration = time.time() - start_time
        
        log_request(
            api_key_id=client_info["id"],
            api_key_name=client_info["name"],
            endpoint="GET /tts",
            ip_address=ip_address,
            status_code=200,
            characters_count=len(text),
            voice=voice,
            duration_seconds=duration
        )
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        duration = time.time() - start_time
        log_request(
            api_key_id=client_info["id"],
            api_key_name=client_info["name"],
            endpoint="GET /tts",
            ip_address=ip_address,
            status_code=500,
            characters_count=len(text),
            voice=voice,
            duration_seconds=duration,
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"TTS generation error: {str(e)}")
