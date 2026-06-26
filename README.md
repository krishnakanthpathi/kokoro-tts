# Kokoro TTS Microservice

A high-performance text-to-speech API microservice powered by Kokoro-82M, featuring built-in API key authorization, sliding window rate limiting, a root welcome message, and an admin dashboard.

---

## Quickstart

### 1. Run with Docker Compose (Recommended)
Build and start the container with persistent database storage:
```bash
docker compose up -d --build
```
The server will start on port `8998`. SQLite database and request logs are persisted under `./data`.

### 2. Run Locally
Activate your virtual environment and start the Uvicorn server:
```bash
source /home/krishnakanth/deployed/kokoro/.venv/bin/activate
uvicorn app.main:app --port 8998 --host 0.0.0.0
```

---

## Authentication

*   **Localhost Bypass**: Requests originating from `localhost` or `127.0.0.1` do not require an API key.
*   **External Requests**: Must provide a valid API key in one of the following ways:
    1.  **HTTP Header**: `X-API-Key: kokoro_sk_...`
    2.  **Query Parameter**: `?api_key=kokoro_sk_...`

---

## API Endpoints

### 1. Root Welcome
*   **Route**: `GET /`
*   **Response**: `{"message": "welcome kokoro service"}`

### 2. Synthesize Speech (POST)
*   **Route**: `POST /tts`
*   **Headers**: 
    *   `Content-Type: application/json`
    *   `X-API-Key: <YOUR_API_KEY>` (if remote)
*   **Request Body**:
    ```json
    {
      "text": "Hello world.",
      "voice": "af_heart",
      "speed": 1.0,
      "lang_code": "a"
    }
    ```
*   **Response**: Audio file byte stream (`audio/wav`)

### 3. Synthesize Speech (GET)
*   **Route**: `GET /tts?text=Hello+world&voice=af_heart&speed=1.0&lang_code=a`
*   **Headers**: `X-API-Key: <YOUR_API_KEY>` (if remote)
*   **Response**: Audio file byte stream (`audio/wav`)

---

## Admin Dashboard

*   **URL**: [http://127.0.0.1:8998/admin](http://127.0.0.1:8998/admin)
*   **Credentials**: Enter password (Default: `admin123`, configured via `ADMIN_PASSWORD` env var).
*   **Features**:
    *   Generate and revoke API keys.
    *   View request logs and error details in real-time.
    *   Monitor total requests, processed characters, average latency, and popular voice profiles.
