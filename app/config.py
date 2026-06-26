import os

class Settings:
    PROJECT_NAME: str = "Kokoro TTS Microservice"
    VERSION: str = "1.0.0"
    API_V1_STR: str = ""
    
    # TTS defaults
    DEFAULT_VOICE: str = os.getenv("DEFAULT_VOICE", "af_heart")
    DEFAULT_SPEED: float = float(os.getenv("DEFAULT_SPEED", "1.0"))
    DEFAULT_LANG: str = os.getenv("DEFAULT_LANG", "a")
    
    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8998"))

settings = Settings()
