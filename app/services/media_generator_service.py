from abc import ABC, abstractmethod
from typing import List, Optional


class MediaGeneratorService(ABC):
    """Abstract interface for media generation services."""
    
    @abstractmethod
    async def generate_media(
        self, 
        model: str, 
        prompt: str, 
        num_outputs: int = 1,
        seed: Optional[int] = None,
        output_format: Optional[str] = None
    ) -> List[str]:
        """
        Generate media using the specified parameters.
        
        Args:
            model: The model identifier to use for generation
            prompt: The text prompt for media generation
            num_outputs: Number of media outputs to generate (default: 1)
            seed: Optional seed for reproducible generation
            output_format: Optional format specification for output
            
        Returns:
            List of URLs pointing to the generated media
        """
        pass