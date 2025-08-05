import replicate
import logging
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.services.media_generator_service import MediaGeneratorService

logger = logging.getLogger(__name__)


class ReplicateService(MediaGeneratorService):
    def __init__(self):
        self.client = replicate.Client(api_token=settings.replicate_api_token)
    
    async def generate_media(
        self, 
        model: str, 
        prompt: str, 
        num_outputs: int = 1,
        seed: Optional[int] = None,
        output_format: Optional[str] = None
    ) -> List[str]:
        try:
            input_params = {
                "prompt": prompt,
                "num_outputs": num_outputs
            }
            
            if seed is not None:
                input_params["seed"] = seed
            
            if output_format is not None:
                input_params["output_format"] = output_format
            
            logger.info(f"Generating media with model {model} and params: {input_params}")
            
            output = self.client.run(model, input=input_params)
            
            if isinstance(output, list):
                urls = [str(item) for item in output]
            else:
                urls = [str(output)]
            
            logger.info(f"Successfully generated {len(urls)} media files")
            return urls
            
        except Exception as e:
            logger.error(f"Error generating media with Replicate: {str(e)}")
            raise e

