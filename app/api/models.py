from pydantic import BaseModel, Field

class TTSRequest(BaseModel):
    text: str = Field(..., description="The text to convert to speech", min_length=1)
    voice: str = Field("af_heart", description="The voice to use (e.g., af_heart, af_bella, bf_emma, etc.)")
    speed: float = Field(1.0, description="Speech speed modifier (0.5 to 2.0)", ge=0.5, le=2.0)
    lang_code: str = Field("a", description="Language code (a: American English, b: British English, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hello, welcome to the Kokoro text to speech service.",
                "voice": "af_heart",
                "speed": 1.0,
                "lang_code": "a"
            }
        }
