"""Application settings and configuration."""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = Field(default="Azure Semantic Kernel Agent Starter", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=5003, env="API_PORT")
    
    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./app.db", env="DATABASE_URL")
    sync_database_url: str = Field(default="sqlite:///./app.db", env="SYNC_DATABASE_URL")
    database_echo: bool = Field(default=False, env="DATABASE_ECHO")
    
    # OpenAI
    openai_api_key: str = Field(env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    
    # ElevenLabs (optional)
    elevenlabs_api_key: Optional[str] = Field(default=None, env="ELEVENLABS_API_KEY")
    
    # Agent Configuration
    hello_agent_endpoint: str = Field(default="http://localhost:5001/api/message", env="HELLO_AGENT_ENDPOINT")
    goodbye_agent_endpoint: str = Field(default="http://localhost:5002/api/message", env="GOODBYE_AGENT_ENDPOINT")
    math_agent_endpoint: str = Field(default="http://localhost:5004/api/message", env="MATH_AGENT_ENDPOINT")
    
    # MCP Server Configuration
    mcp_server_host: str = Field(default="0.0.0.0", env="MCP_SERVER_HOST")
    mcp_server_port: int = Field(default=5005, env="MCP_SERVER_PORT")
    
    # CORS
    cors_origins: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Session Configuration
    session_expires_hours: int = Field(default=24 * 7, env="SESSION_EXPIRES_HOURS")  # 7 days default
    
    # Container Configuration
    container_mode: bool = Field(default=False, env="CONTAINER_MODE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()