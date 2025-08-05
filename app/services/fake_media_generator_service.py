import logging
from typing import List, Optional
from app.services.media_generator_service import MediaGeneratorService

logger = logging.getLogger(__name__)


class FakeMediaGeneratorService(MediaGeneratorService):
    """Fake implementation of MediaGeneratorService for testing and development."""
    
    async def generate_media(
        self, 
        model: str, 
        prompt: str, 
        num_outputs: int = 1,
        seed: Optional[int] = None,
        output_format: Optional[str] = None
    ) -> List[str]:
        """
        Generate fake media URLs for testing purposes.
        
        Returns local static fake image URLs.
        """
        logger.info(f"Generating fake media with model {model}, prompt: {prompt}, num_outputs: {num_outputs}")
        
        base_url = "http://app:8000"
        fake_image_files = ["fake.jpg", "fake1.jpg", "fake2.jpg"]
        
        # Generate URLs cycling through the available fake images
        fake_urls = []
        for i in range(num_outputs):
            image_file = fake_image_files[i % len(fake_image_files)]
            fake_url = f"{base_url}/static/{image_file}"
            fake_urls.append(fake_url)
        
        logger.info(f"Generated {len(fake_urls)} fake media URLs pointing to local static images")
        return fake_urls