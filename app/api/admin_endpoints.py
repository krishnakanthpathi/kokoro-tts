import secrets
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from app.database import get_db_connection
from app.auth import verify_admin
from app.api.models import TTSRequest
from app.core.tts_engine import tts_engine

router = APIRouter()

class KeyCreate(BaseModel):
    name: str = Field(..., description="Descriptive name for the API key client")
    rate_limit: int = Field(60, description="Allowed requests per minute (RPM)", ge=0)

@router.get("/stats")
def get_dashboard_stats(admin_auth: bool = Depends(verify_admin)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Total Requests
        cursor.execute("SELECT COUNT(*) FROM usage_logs")
        total_requests = cursor.fetchone()[0]
        
        # 2. Total Characters
        cursor.execute("SELECT SUM(characters_count) FROM usage_logs")
        total_characters = cursor.fetchone()[0] or 0
        
        # 3. Active Keys
        cursor.execute("SELECT COUNT(*) FROM api_keys WHERE is_active = 1")
        active_keys = cursor.fetchone()[0]
        
        # 4. Average Latency (synthesis duration)
        cursor.execute("SELECT AVG(duration_seconds) FROM usage_logs WHERE duration_seconds > 0")
        avg_latency = cursor.fetchone()[0] or 0.0
        
        # 5. Rate Limit Blocked Requests (429s)
        cursor.execute("SELECT COUNT(*) FROM usage_logs WHERE status_code = 429")
        rate_limit_hits = cursor.fetchone()[0]
        
        # 6. Popular Voices
        cursor.execute("""
            SELECT voice, COUNT(*) as count 
            FROM usage_logs 
            WHERE voice IS NOT NULL AND status_code = 200
            GROUP BY voice 
            ORDER BY count DESC 
            LIMIT 5
        """)
        voice_rows = cursor.fetchall()
        voice_distribution = {row["voice"]: row["count"] for row in voice_rows}
        
        # 7. Request History / Daily Trends (Last 7 Days)
        cursor.execute("""
            SELECT date(timestamp) as day, COUNT(*) as count, SUM(characters_count) as characters
            FROM usage_logs
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY day
            ORDER BY day ASC
        """)
        trend_rows = cursor.fetchall()
        daily_trends = [
            {"day": row["day"], "requests": row["count"], "characters": row["characters"] or 0}
            for row in trend_rows
        ]
        
        conn.close()
        
        return {
            "total_requests": total_requests,
            "total_characters": total_characters,
            "active_keys": active_keys,
            "average_latency": round(avg_latency, 3),
            "rate_limit_hits": rate_limit_hits,
            "voice_distribution": voice_distribution,
            "daily_trends": daily_trends
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database stats error: {str(e)}")

@router.get("/keys")
def list_api_keys(admin_auth: bool = Depends(verify_admin)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Retrieve all keys with aggregate counts of request usage from usage_logs
        cursor.execute("""
            SELECT k.id, k.name, k.key_value, k.rate_limit, k.is_active, k.created_at,
                   COUNT(l.id) as total_calls, SUM(l.characters_count) as total_chars
            FROM api_keys k
            LEFT JOIN usage_logs l ON k.id = l.api_key_id
            GROUP BY k.id
            ORDER BY k.created_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        keys = []
        for row in rows:
            keys.append({
                "id": row["id"],
                "name": row["name"],
                "key_value": row["key_value"],
                "rate_limit": row["rate_limit"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
                "total_calls": row["total_calls"],
                "total_characters": row["total_chars"] or 0
            })
        return keys
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

@router.post("/keys")
def create_api_key(key_data: KeyCreate, admin_auth: bool = Depends(verify_admin)):
    try:
        # Generate prefix token (kokoro_sk_...)
        token = f"kokoro_sk_{secrets.token_hex(16)}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO api_keys (name, key_value, rate_limit, is_active)
            VALUES (?, ?, ?, 1)
        """, (key_data.name, token, key_data.rate_limit))
        key_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "id": key_id,
            "name": key_data.name,
            "key_value": token,
            "rate_limit": key_data.rate_limit,
            "is_active": True
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Key generation collision, try again")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insert error: {str(e)}")

@router.put("/keys/{key_id}/toggle")
def toggle_api_key_status(key_id: int, admin_auth: bool = Depends(verify_admin)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM api_keys WHERE id = ?", (key_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="API key not found")
            
        new_status = 0 if row["is_active"] else 1
        cursor.execute("UPDATE api_keys SET is_active = ? WHERE id = ?", (new_status, key_id))
        conn.commit()
        conn.close()
        
        return {"id": key_id, "is_active": bool(new_status)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database update error: {str(e)}")

@router.delete("/keys/{key_id}")
def delete_api_key(key_id: int, admin_auth: bool = Depends(verify_admin)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM api_keys WHERE id = ?", (key_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="API key not found")
            
        cursor.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        conn.commit()
        conn.close()
        
        return {"id": key_id, "status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database delete error: {str(e)}")

@router.get("/logs")
def list_logs(
    limit: int = Query(50, ge=1, le=200),
    admin_auth: bool = Depends(verify_admin)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, api_key_name, timestamp, endpoint, ip_address, status_code, characters_count, voice, duration_seconds, error_message
            FROM usage_logs
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            logs.append({
                "id": row["id"],
                "api_key_name": row["api_key_name"] or "Localhost Bypass",
                "timestamp": row["timestamp"],
                "endpoint": row["endpoint"],
                "ip_address": row["ip_address"],
                "status_code": row["status_code"],
                "characters_count": row["characters_count"],
                "voice": row["voice"],
                "duration_seconds": round(row["duration_seconds"], 3) if row["duration_seconds"] else 0.0,
                "error_message": row["error_message"]
            })
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database log retrieval error: {str(e)}")

@router.post("/tts")
async def admin_generate_tts(
    tts_request: TTSRequest,
    admin_auth: bool = Depends(verify_admin)
):
    if not tts_request.text.strip():
        raise HTTPException(status_code=400, detail="Text parameter cannot be empty")
        
    try:
        # Run heavy TTS synthesis in a thread pool to avoid blocking the event loop
        wav_bytes = await asyncio.to_thread(
            tts_engine.synthesize,
            text=tts_request.text,
            voice=tts_request.voice,
            speed=tts_request.speed,
            lang_code=tts_request.lang_code
        )
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation error: {str(e)}")
