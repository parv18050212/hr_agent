from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class Settings(BaseSettings):
    DATABASE_URL: str
    GOOGLE_API_KEY: SecretStr 
    
    LANGCHAIN_TRACING_V2: str
    LANGCHAIN_ENDPOINT: str
    LANGCHAIN_API_KEY: SecretStr # Switched to Google

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()