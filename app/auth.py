import os
import time
import threading
from collections import defaultdict
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader, APIKeyQuery
from app.database import get_db_connection

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)

# Thread-safe sliding window rate-limiter records
rate_limit_lock = threading.Lock()
# Maps identifier (key_value or IP) to list of request timestamps
rate_limit_records = defaultdict(list)

def is_localhost(request: Request) -> bool:
    # Check client IP
    client_host = request.client.host if request.client else None
    if client_host in ("127.0.0.1", "::1", "localhost"):
        return True
        
    # Check Host header (e.g. localhost:8998)
    host_header = request.headers.get("host", "")
    if "localhost" in host_header or "127.0.0.1" in host_header:
        return True
        
    return False

async def verify_api_key_and_rate_limit(
    request: Request,
    api_key_header: str = Security(API_KEY_HEADER),
    api_key_query: str = Security(API_KEY_QUERY)
):
    key = api_key_header or api_key_query
    localhost = is_localhost(request)
    
    client_info = None
    
    # 1. API Key Authentication
    if key:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_keys WHERE key_value = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=401, detail="Invalid API key")
            
        if not row["is_active"]:
            raise HTTPException(status_code=403, detail="API key is suspended")
            
        client_info = {
            "id": row["id"],
            "name": row["name"],
            "key_value": row["key_value"],
            "rate_limit": row["rate_limit"]
        }
    else:
        if not localhost:
            raise HTTPException(
                status_code=401, 
                detail="Authentication failed: X-API-Key header or api_key query parameter required"
            )
        
        # Localhost client bypassed API Key
        client_info = {
            "id": None,
            "name": "Localhost Bypass",
            "key_value": "localhost",
            "rate_limit": int(os.getenv("LOCALHOST_RATE_LIMIT", "120"))
        }

    # 2. Rate Limiting (Sliding Window)
    limit = client_info["rate_limit"]
    if limit > 0:
        # Use API key string if present, otherwise client host IP for rate-limiting localhost
        client_host = request.client.host if request.client else "localhost_ip"
        identifier = client_info["key_value"] if client_info["id"] else f"localhost_{client_host}"
        
        with rate_limit_lock:
            now = time.time()
            timestamps = rate_limit_records[identifier]
            
            # Remove timestamps older than 60 seconds
            while timestamps and timestamps[0] < now - 60:
                timestamps.pop(0)
                
            if len(timestamps) >= limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Maximum allowed is {limit} requests per minute."
                )
                
            # Add current timestamp
            timestamps.append(now)
            
    # Save client info to request state so we can reference it in endpoint logging
    request.state.client_info = client_info
    return client_info

async def verify_admin(request: Request):
    # Retrieve configured admin password
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # Accept header or query param
    provided_password = request.headers.get("X-Admin-Password") or request.query_params.get("admin_password")
    
    if not provided_password:
        raise HTTPException(status_code=401, detail="Admin password required")
        
    if provided_password != admin_password:
        raise HTTPException(status_code=403, detail="Invalid admin password")
        
    return True
