import logging
from app.core.config import settings
from app.services.media_generator_service import MediaGeneratorService
from app.services.replicate_service import ReplicateService
from app.services.fake_media_generator_service import FakeMediaGeneratorService

logger = logging.getLogger(__name__)


class MediaGeneratorFactory:
    """Factory for creating media generator service instances."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> MediaGeneratorService:
        """
        Get the appropriate media generator service instance based on configuration.
        
        Returns:
            MediaGeneratorService instance based on the configured provider
        """
        if cls._instance is None:
            provider = settings.media_generator_provider.lower()
            
            if provider == "replicate":
                logger.info("Creating ReplicateService instance")
                cls._instance = ReplicateService()
            elif provider == "fake":
                logger.info("Creating FakeMediaGeneratorService instance")
                cls._instance = FakeMediaGeneratorService()
            else:
                logger.warning(f"Unknown media generator provider '{provider}', defaulting to ReplicateService")
                cls._instance = ReplicateService()
        
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance. Useful for testing."""
        cls._instance = None


def get_media_generator_service() -> MediaGeneratorService:
    """Convenience function to get the media generator service instance."""
    return MediaGeneratorFactory.get_instance()