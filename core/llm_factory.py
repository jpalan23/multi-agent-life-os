import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LLMFactory:
    """
    A factory class to generate LLM connections for the Multi-Agent Life-OS.
    Supports local Ollama instances and LM Studio.
    """

    @staticmethod
    def get_ollama(model: str = None, temperature: float = 0.0):
        """
        Returns a ChatOllama instance.
        """
        from langchain_ollama import ChatOllama
        
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model_name = model or os.getenv("OLLAMA_DEFAULT_MODEL", "llama3")
        
        return ChatOllama(
            base_url=base_url,
            model=model_name,
            temperature=temperature
        )

    @staticmethod
    def get_lm_studio(model: str = None, temperature: float = 0.0):
        """
        Returns a ChatOpenAI instance configured for LM Studio.
        """
        from langchain_openai import ChatOpenAI
        
        base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
        model_name = model or os.getenv("LM_STUDIO_DEFAULT_MODEL", "local-model")
        
        return ChatOpenAI(
            base_url=base_url,
            api_key="lm-studio", # LM Studio requires a placeholder API key
            model=model_name,
            temperature=temperature
        )

    @classmethod
    def get_default_llm(cls, temperature: float = 0.0):
        """
        Returns the default LLM based on the DEFAULT_LLM_PROVIDER env variable.
        """
        provider = os.getenv("DEFAULT_LLM_PROVIDER", "ollama").lower()
        if provider == "lm_studio":
            return cls.get_lm_studio(temperature=temperature)
        return cls.get_ollama(temperature=temperature)

# Expose a default instance or function for easy importing
def get_llm(temperature: float = 0.0):
    return LLMFactory.get_default_llm(temperature=temperature)
