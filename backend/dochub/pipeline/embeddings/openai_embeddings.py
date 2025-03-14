import os
import logging
import random
import numpy as np
from django.conf import settings
from .base import EmbeddingGenerator
import openai  # Using module-level API

logger = logging.getLogger(__name__)

class OpenAIEmbeddingGenerator(EmbeddingGenerator):
    """Embedding generator implementation using OpenAI API"""
    
    def __init__(self, model="text-embedding-ada-002", batch_size=100):
        """
        Initialize the OpenAI embedding generator.
        
        Args:
            model: OpenAI embedding model name.
            batch_size: Number of chunks to process in one batch.
        """
        self.model_name = model
        self.batch_size = batch_size
        self.testing = getattr(settings, 'USE_MOCK_EMBEDDINGS', False)
        if self.testing:
            logger.info("Using MOCK embeddings for testing")
    
    def generate(self, chunks):
        """
        Generate embeddings for text chunks using OpenAI API.
        
        Args:
            chunks: List of text chunks.
            
        Returns:
            list: List of embeddings.
        """
        if not chunks:
            logger.warning("No chunks provided for embedding generation")
            return []
        if self.testing:
            return self._generate_mock_embeddings(chunks)
        return self._generate_real_embeddings(chunks)
    
    def _generate_mock_embeddings(self, chunks):
        logger.info(f"Generating mock embeddings for {len(chunks)} chunks")
        mock_embeddings = []
        for chunk in chunks:
            seed = hash(chunk) % 10000
            random.seed(seed)
            embedding = [random.uniform(-1, 1) for _ in range(1536)]
            norm = np.sqrt(sum(x * x for x in embedding))
            embedding = [x / norm for x in embedding]
            mock_embeddings.append(embedding)
        logger.info(f"Successfully generated {len(mock_embeddings)} mock embeddings")
        return mock_embeddings
    
    def _generate_real_embeddings(self, chunks):
        openai_api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", None)
        if not openai_api_key:
            logger.error("Missing OPENAI_API_KEY environment variable or setting")
            raise ValueError("Missing OPENAI_API_KEY environment variable or setting")
        try:
            logger.info("Using OpenAI module-level API to generate embeddings")
            openai.api_key = openai_api_key
            # Do not set any proxies here
            
            logger.info(f"Generating OpenAI embeddings for {len(chunks)} chunks using {self.model_name}")
            all_embeddings = []
            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i + self.batch_size]
                for chunk in batch:
                    try:
                        response = openai.embeddings.create(
                            input=chunk,
                            model=self.model_name
                        )
                        # Access using attribute access (Pydantic model)
                        embedding = response.data[0].embedding
                        all_embeddings.append(embedding)
                        logger.debug(f"Generated embedding for chunk with {len(embedding)} dimensions")
                    except Exception as chunk_error:
                        logger.error(f"Error generating embedding for chunk: {str(chunk_error)}")
                        all_embeddings.append([0.0] * 1536)
                logger.debug(f"Processed batch {i // self.batch_size + 1}/{(len(chunks) - 1) // self.batch_size + 1}")
            if len(all_embeddings) != len(chunks):
                logger.warning(f"Mismatch between chunks ({len(chunks)}) and embeddings ({len(all_embeddings)})")
                raise ValueError(f"Got {len(all_embeddings)} embeddings for {len(chunks)} chunks")
            logger.info(f"Successfully generated {len(all_embeddings)} embeddings")
            return all_embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise