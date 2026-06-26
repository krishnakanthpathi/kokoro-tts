import os

# Helper to load .env manually without external packages
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
env_path = os.path.join(root_dir, ".env")

if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            # Ignore comments and empty lines
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                # Strip spaces and optional quotes around values
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ[key] = val

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
