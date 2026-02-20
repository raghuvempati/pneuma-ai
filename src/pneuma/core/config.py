import os

class PneumaConfig:
    """Single source of truth for all environment variables and infrastructure connections."""
    
    @property
    def openai_api_key(self) -> str:
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("CRITICAL: OPENAI_API_KEY is missing from the environment.")
        return key
    
    @property
    def openai_model(self) -> str:
        return os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        
    @property
    def qdrant_host(self) -> str:
        return os.environ.get("QDRANT_HOST", "localhost")
        
    @property
    def qdrant_port(self) -> int:
        return int(os.environ.get("QDRANT_PORT", 6333))
        
    @property
    def nebula_host(self) -> str:
        return os.environ.get("NEBULA_HOST", "127.0.0.1")
        
    @property
    def nebula_port(self) -> int:
        return int(os.environ.get("NEBULA_PORT", 9669))

# Export a single initialized instance to be imported across the framework
settings = PneumaConfig()