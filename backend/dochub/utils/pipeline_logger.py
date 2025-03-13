# backend/dochub/utils/pipeline_logger.py

import os
import json
import time
import logging
import functools
from datetime import datetime
from pathlib import Path
from django.conf import settings

# Configure a special logger for pipeline testing
pipeline_logger = logging.getLogger('dochub.pipeline.test')

class PipelineLogger:
    """
    Logger class for document processing pipeline testing.
    
    This class provides:
    1. Detailed logging of each pipeline step
    2. Performance metrics collection
    3. Artifact storage (e.g., text chunks, embeddings, graph data)
    4. Error tracking for debugging
    """
    
    def __init__(self, document_id=None, log_level=logging.DEBUG, save_artifacts=True):
        """
        Initialize the pipeline logger.
        
        Args:
            document_id: ID of the document being processed
            log_level: Logging level
            save_artifacts: Whether to save intermediate artifacts
        """
        self.document_id = str(document_id) if document_id else "debug"
        self.log_level = log_level
        self.save_artifacts = save_artifacts
        self.metrics = {}
        self.step_times = {}
        self.total_start_time = None
        self.history = []  # Store logs for UI display
        
        # Create artifact directory
        if self.save_artifacts and document_id:
            self.artifact_dir = Path(settings.MEDIA_ROOT) / 'pipeline_tests' / self.document_id
            os.makedirs(self.artifact_dir, exist_ok=True)
    
    def start_pipeline(self):
        """Start timing the full pipeline"""
        self.total_start_time = time.time()
        self.log("Pipeline processing started")
    
    def end_pipeline(self):
        """End timing the full pipeline and log summary"""
        if self.total_start_time:
            total_time = time.time() - self.total_start_time
            self.metrics['total_processing_time'] = total_time
            
            # Log summary
            self.log(f"Pipeline completed in {total_time:.2f} seconds")
            self.log(f"Step times: {json.dumps(self.step_times, indent=2)}")
            
            # Save metrics
            if self.save_artifacts:
                self.save_json('metrics.json', self.metrics)
    
    def log(self, message, level=None):
        """Log a message with the pipeline logger"""
        level = level or self.log_level
        pipeline_logger.log(level, f"[Document {self.document_id}] {message}")
    
    def log_step(self, document_id, stage, status, details=None):
        """
        Log a pipeline step for the UI.
        
        Args:
            document_id: ID of the document being processed
            stage: Pipeline stage (e.g., text_extraction, text_splitting)
            status: Status of the step (e.g., started, completed, error)
            details: Additional details to include in the log (dict)
        """
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            'document_id': document_id,
            'stage': stage,
            'status': status,
            'timestamp': timestamp,
            'details': details or {}
        }
        
        # Add to history for UI display
        self.history.append(log_entry)
        
        # Also log to the standard logger
        status_msg = f"[{stage.upper()}] {status}"
        if details:
            if "message" in details:
                status_msg += f": {details['message']}"
            elif "error" in details:
                status_msg += f": {details['error']}" 
        
        log_level = logging.ERROR if status == 'error' else logging.INFO
        self.log(status_msg, log_level)
        
        return log_entry
    
    def log_step_decorator(self, step_name):
        """Decorator to log and time a pipeline step"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                self.log(f"Starting step: {step_name}")
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Calculate step time
                    step_time = time.time() - start_time
                    self.step_times[step_name] = step_time
                    self.log(f"Completed step: {step_name} in {step_time:.2f} seconds")
                    
                    return result
                except Exception as e:
                    self.log(f"Error in step {step_name}: {str(e)}", logging.ERROR)
                    raise
                    
            return wrapper
        return decorator
    
    def save_text(self, filename, content):
        """Save text content to a file"""
        if not self.save_artifacts:
            return
            
        try:
            file_path = self.artifact_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log(f"Saved text to {file_path}")
        except Exception as e:
            self.log(f"Error saving text to {filename}: {str(e)}", logging.ERROR)
    
    def save_json(self, filename, data):
        """Save JSON data to a file"""
        if not self.save_artifacts:
            return
            
        try:
            file_path = self.artifact_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            self.log(f"Saved JSON to {file_path}")
        except Exception as e:
            self.log(f"Error saving JSON to {filename}: {str(e)}", logging.ERROR)
    
    def log_extracted_text(self, text):
        """Log and save extracted text"""
        text_length = len(text)
        self.metrics['extracted_text_length'] = text_length
        self.log(f"Extracted {text_length} characters of text")
        
        # Save sample of text (first 1000 chars)
        self.log(f"Text sample: {text[:1000]}...")
        
        # Save full text
        if self.save_artifacts:
            self.save_text('extracted_text.txt', text)
    
    def log_text_chunks(self, chunks):
        """Log and save text chunks"""
        chunk_count = len(chunks)
        avg_chunk_size = sum(len(chunk) for chunk in chunks) / max(chunk_count, 1)
        
        self.metrics['chunk_count'] = chunk_count
        self.metrics['avg_chunk_size'] = avg_chunk_size
        
        self.log(f"Split text into {chunk_count} chunks (avg size: {avg_chunk_size:.1f} chars)")
        
        # Log first chunk as sample
        if chunks:
            self.log(f"First chunk sample: {chunks[0][:500]}...")
        
        # Save all chunks
        if self.save_artifacts:
            for i, chunk in enumerate(chunks):
                self.save_text(f'chunk_{i+1}.txt', chunk)
            
            # Save chunk metadata
            chunk_meta = [
                {'chunk_id': i+1, 'length': len(chunk), 'preview': chunk[:100]}
                for i, chunk in enumerate(chunks)
            ]
            self.save_json('chunks_metadata.json', chunk_meta)
    
    def log_embeddings(self, embeddings):
        """Log and save embeddings"""
        count = len(embeddings)
        avg_dimensions = sum(len(emb) for emb in embeddings) / max(count, 1) if embeddings else 0
        
        self.metrics['embedding_count'] = count
        self.metrics['embedding_dimensions'] = int(avg_dimensions)
        
        self.log(f"Generated {count} embeddings (dimensions: {avg_dimensions:.0f})")
        
        # Save embeddings (only if explicitly requested as they can be large)
        if self.save_artifacts:
            # Save embeddings metadata
            embeddings_meta = {
                'count': count,
                'dimensions': int(avg_dimensions),
                'sample': embeddings[0][:10] if embeddings else []
            }
            self.save_json('embeddings_metadata.json', embeddings_meta)
            
            # Optionally save full embeddings (can be large)
            # self.save_json('embeddings.json', embeddings)
    
    def log_openai_request(self, prompt, model="gpt-4o"):
        """Log OpenAI API request for graph generation"""
        self.log(f"Sending request to OpenAI API (model: {model})")
        
        # Save prompt
        if self.save_artifacts:
            self.save_text(f'openai_prompt_{datetime.now().strftime("%H%M%S")}.txt', prompt)
    
    def log_openai_response(self, response_text):
        """Log OpenAI API response for graph generation"""
        self.log(f"Received response from OpenAI API ({len(response_text)} chars)")
        
        # Save response
        if self.save_artifacts:
            self.save_text(f'openai_response_{datetime.now().strftime("%H%M%S")}.txt', response_text)
    
    def log_graph_data(self, entities, relationships):
        """Log and save graph data"""
        entity_count = len(entities)
        relationship_count = len(relationships)
        
        self.metrics['entity_count'] = entity_count
        self.metrics['relationship_count'] = relationship_count
        
        self.log(f"Generated knowledge graph with {entity_count} entities and {relationship_count} relationships")
        
        # Log sample entities and relationships
        if entities:
            sample_entity = entities[0]
            self.log(f"Sample entity: {json.dumps(sample_entity, default=str)}")
        
        if relationships:
            sample_relationship = relationships[0]
            self.log(f"Sample relationship: {json.dumps(sample_relationship, default=str)}")
        
        # Save graph data
        if self.save_artifacts:
            graph_data = {
                'entities': entities,
                'relationships': relationships
            }
            self.save_json('graph_data.json', graph_data)

# Utility function to wrap a service with logging
def with_pipeline_logging(service_class):
    """
    Decorator to add pipeline logging to a service class.
    This injects a logger into the service and wraps key methods with logging.
    """
    original_init = service_class.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.logger = kwargs.get('logger', None)
    
    service_class.__init__ = new_init
    return service_class