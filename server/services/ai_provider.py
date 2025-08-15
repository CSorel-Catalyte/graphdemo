"""
AI Provider Service for supporting both OpenAI and Azure OpenAI.

This module provides a unified interface for different AI providers,
allowing seamless switching between OpenAI and Azure OpenAI services.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from enum import Enum

try:
    from openai import AsyncOpenAI, AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None
    AzureOpenAI = None

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    AZURE = "azure"


class AIProviderError(Exception):
    """Base exception for AI provider errors."""
    pass


class AIProviderConfigError(AIProviderError):
    """Exception for AI provider configuration errors."""
    pass


class BaseAIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Create a chat completion."""
        pass
    
    @abstractmethod
    async def create_embedding(
        self,
        input_text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Create an embedding."""
        pass
    
    @abstractmethod
    def get_default_chat_model(self) -> str:
        """Get the default chat model for this provider."""
        pass
    
    @abstractmethod
    def get_default_embedding_model(self) -> str:
        """Get the default embedding model for this provider."""
        pass


class OpenAIProvider(BaseAIProvider):
    """OpenAI provider implementation."""
    
    def __init__(self, api_key: str, chat_model: str = "gpt-3.5-turbo-1106", embedding_model: str = "text-embedding-3-large"):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            chat_model: Default chat model
            embedding_model: Default embedding model
        """
        if not OPENAI_AVAILABLE:
            raise AIProviderConfigError("OpenAI library not available. Please install the openai package.")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        
        logger.info(f"Initialized OpenAI provider with chat model: {chat_model}, embedding model: {embedding_model}")
    
    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Create a chat completion using OpenAI."""
        model = model or self.chat_model
        
        return await self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
    
    async def create_embedding(
        self,
        input_text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Create an embedding using OpenAI."""
        model = model or self.embedding_model
        
        return await self.client.embeddings.create(
            model=model,
            input=input_text,
            **kwargs
        )
    
    def get_default_chat_model(self) -> str:
        """Get the default chat model."""
        return self.chat_model
    
    def get_default_embedding_model(self) -> str:
        """Get the default embedding model."""
        return self.embedding_model


class AzureOpenAIProvider(BaseAIProvider):
    """Azure OpenAI provider implementation."""
    
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        api_version: str = "2024-02-15-preview",
        chat_deployment: str = "gpt-35-turbo",
        embedding_deployment: str = "text-embedding-ada-002"
    ):
        """
        Initialize Azure OpenAI provider.
        
        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            api_version: API version
            chat_deployment: Chat model deployment name
            embedding_deployment: Embedding model deployment name
        """
        if not OPENAI_AVAILABLE:
            raise AIProviderConfigError("OpenAI library not available. Please install the openai package.")
        
        # Use the dedicated AzureOpenAI client for Azure OpenAI
        self.client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=api_key
        )
        self.chat_deployment = chat_deployment
        self.embedding_deployment = embedding_deployment
        self.api_version = api_version
        
        logger.info(f"Initialized Azure OpenAI provider with endpoint: {endpoint}, chat deployment: {chat_deployment}, embedding deployment: {embedding_deployment}")
    
    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Create a chat completion using Azure OpenAI."""
        # For Azure, we use deployment names instead of model names
        model = model or self.chat_deployment
        
        # AzureOpenAI client is sync, so we need to run it in a thread
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
        )
    
    async def create_embedding(
        self,
        input_text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> Any:
        """Create an embedding using Azure OpenAI."""
        # For Azure, we use deployment names instead of model names
        deployment = model or self.embedding_deployment
        
        # AzureOpenAI client is sync, so we need to run it in a thread
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.client.embeddings.create(
                model=deployment,
                input=input_text,
                **kwargs
            )
        )
    
    def get_default_chat_model(self) -> str:
        """Get the default chat deployment name."""
        return self.chat_deployment
    
    def get_default_embedding_model(self) -> str:
        """Get the default embedding deployment name."""
        return self.embedding_deployment


class AIProviderFactory:
    """Factory for creating AI providers based on configuration."""
    
    @staticmethod
    def create_provider() -> BaseAIProvider:
        """
        Create an AI provider based on environment configuration.
        
        Returns:
            Configured AI provider instance
            
        Raises:
            AIProviderConfigError: If configuration is invalid or missing
        """
        provider_type = os.getenv("AI_PROVIDER", "openai").lower()
        
        if provider_type == AIProvider.OPENAI.value:
            return AIProviderFactory._create_openai_provider()
        elif provider_type == AIProvider.AZURE.value:
            return AIProviderFactory._create_azure_provider()
        else:
            raise AIProviderConfigError(f"Unsupported AI provider: {provider_type}")
    
    @staticmethod
    def _create_openai_provider() -> OpenAIProvider:
        """Create OpenAI provider from environment variables."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AIProviderConfigError("OPENAI_API_KEY environment variable is required for OpenAI provider")
        
        chat_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-1106")
        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        
        return OpenAIProvider(
            api_key=api_key,
            chat_model=chat_model,
            embedding_model=embedding_model
        )
    
    @staticmethod
    def _create_azure_provider() -> AzureOpenAIProvider:
        """Create Azure OpenAI provider from environment variables."""
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if not api_key:
            raise AIProviderConfigError("AZURE_OPENAI_API_KEY environment variable is required for Azure provider")
        if not endpoint:
            raise AIProviderConfigError("AZURE_OPENAI_ENDPOINT environment variable is required for Azure provider")
        
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        
        if not chat_deployment:
            raise AIProviderConfigError("AZURE_OPENAI_CHAT_DEPLOYMENT environment variable is required for Azure provider")
        if not embedding_deployment:
            raise AIProviderConfigError("AZURE_OPENAI_EMBEDDING_DEPLOYMENT environment variable is required for Azure provider")
        
        return AzureOpenAIProvider(
            api_key=api_key,
            endpoint=endpoint,
            api_version=api_version,
            chat_deployment=chat_deployment,
            embedding_deployment=embedding_deployment
        )
    
    @staticmethod
    def get_provider_info() -> Dict[str, Any]:
        """
        Get information about the configured AI provider.
        
        Returns:
            Dictionary with provider information
        """
        provider_type = os.getenv("AI_PROVIDER", "openai").lower()
        
        if provider_type == AIProvider.OPENAI.value:
            return {
                "provider": "OpenAI",
                "type": "openai",
                "chat_model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-1106"),
                "embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
                "configured": bool(os.getenv("OPENAI_API_KEY"))
            }
        elif provider_type == AIProvider.AZURE.value:
            return {
                "provider": "Azure OpenAI",
                "type": "azure",
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "Not configured"),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                "chat_deployment": os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "Not configured"),
                "embedding_deployment": os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "Not configured"),
                "configured": bool(os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_ENDPOINT"))
            }
        else:
            return {
                "provider": "Unknown",
                "type": provider_type,
                "configured": False,
                "error": f"Unsupported provider type: {provider_type}"
            }


# Global provider instance (will be initialized on startup)
ai_provider: Optional[BaseAIProvider] = None


def get_ai_provider() -> BaseAIProvider:
    """
    Get the global AI provider instance.
    
    Returns:
        Configured AI provider instance
        
    Raises:
        AIProviderConfigError: If provider is not initialized
    """
    global ai_provider
    
    if ai_provider is None:
        raise AIProviderConfigError("AI provider not initialized. Call initialize_ai_provider() first.")
    
    return ai_provider


def initialize_ai_provider() -> BaseAIProvider:
    """
    Initialize the global AI provider instance.
    
    Returns:
        Configured AI provider instance
        
    Raises:
        AIProviderConfigError: If configuration is invalid
    """
    global ai_provider
    
    try:
        ai_provider = AIProviderFactory.create_provider()
        logger.info("AI provider initialized successfully")
        return ai_provider
    except Exception as e:
        logger.error(f"Failed to initialize AI provider: {e}")
        raise AIProviderConfigError(f"Failed to initialize AI provider: {e}")


def is_ai_provider_available() -> bool:
    """
    Check if an AI provider is available and configured.
    
    Returns:
        True if provider is available, False otherwise
    """
    try:
        provider_info = AIProviderFactory.get_provider_info()
        return provider_info.get("configured", False)
    except Exception:
        return False