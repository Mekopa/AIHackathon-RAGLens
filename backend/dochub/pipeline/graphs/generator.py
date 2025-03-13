# backend/dochub/pipeline/generator.py

import json
import logging
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from django.conf import settings
from .schema import SchemaManager, ENTITY_TYPES, RELATIONSHIP_TYPES
from .client import Neo4jClient
from ...utils.pipeline_logger import PipelineLogger
from openai import OpenAI  # Use the new client interface

logger = logging.getLogger(__name__)

class GraphGenerator:
    """
    Responsible for generating knowledge graphs from text.
    Extracts entities and relationships and normalizes them according to schema.
    """
    
    def __init__(self, pipeline_logger=None):
        self.pipeline_logger = pipeline_logger or PipelineLogger()
        self.neo4j_client = Neo4jClient(pipeline_logger=self.pipeline_logger)
    
    def process_document(self, document_id, document_name, user_id, text, 
                         file_path=None, folder_path=None, folder_id=None, 
                         metadata=None, chunks=None) -> Dict[str, Any]:
        try:
            self.pipeline_logger.log_step(document_id, "graph_generation", "started", details={"document_name": document_name})
            try:
                self.neo4j_client.store_document_node(document_id, document_name, folder_id)
            except Exception as neo4j_error:
                logger.warning(f"Neo4j document storage failed but continuing: {str(neo4j_error)}")
                self.pipeline_logger.log_step(document_id, "neo4j_warning", "continuing_without_document_node",
                                               details={"error": str(neo4j_error)})
            if not chunks:
                chunks = [text]
            all_entities = []
            all_relationships = []
            for i, chunk in enumerate(chunks):
                if not chunk or len(chunk.strip()) < 50:
                    continue
                print(f"Processing chunk {i+1}/{len(chunks)} for document {document_id}")
                result = self.extract_entities_and_relationships(chunk, document_id, i)
                all_entities.extend(result.get("entities", []))
                all_relationships.extend(result.get("relationships", []))
                self.pipeline_logger.log_step(document_id, "graph_generation", "chunk_processed",
                                              details={"chunk_index": i, "entity_count": len(result.get("entities", [])),
                                                       "relationship_count": len(result.get("relationships", []))})
            try:
                self.neo4j_client.store_entities_and_relationships(all_entities, all_relationships, document_id)
                related_documents = 0
            except Exception as neo4j_error:
                logger.warning(f"Neo4j operation failed but continuing: {str(neo4j_error)}")
                self.pipeline_logger.log_step(document_id, "neo4j_warning", "continuing_without_neo4j",
                                               details={"error": str(neo4j_error)})
                related_documents = 0
            self.pipeline_logger.log_step(document_id, "graph_generation", "completed",
                                          details={"entity_count": len(all_entities),
                                                   "relationship_count": len(all_relationships),
                                                   "related_documents": related_documents})
            return {"document_id": document_id, "entities_count": len(all_entities),
                    "relationships_count": len(all_relationships), "related_documents": related_documents}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generating knowledge graph: {error_msg}")
            self.pipeline_logger.log_step(document_id, "graph_generation", "error", details={"error": error_msg})
            raise

    def extract_entities_and_relationships(self, text, document_id=None, chunk_index=None):
        try:
            self.pipeline_logger.log_step(document_id, "graph_extraction", "started", details={"chunk_index": chunk_index})
            entity_types_str = ", ".join(ENTITY_TYPES.keys())
            relationship_types_str = ", ".join(RELATIONSHIP_TYPES.keys())
            prompt = f"""
            Extract entities and relationships from the following text.
            
            Entity types: {entity_types_str}
            Relationship types: {relationship_types_str}
            
            For each entity, provide:
            1. A unique identifier (name of the entity with no spaces)
            2. The entity type (one from the list above)
            3. The full name or description of the entity
            
            For each relationship, provide:
            1. The source entity identifier
            2. The relationship type (one from the list above)
            3. The target entity identifier
            
            Return the results in JSON format as follows:
            
            {{
                "entities": [
                    {{"id": "entity_id", "type": "EntityType", "name": "Full Entity Name", "properties": {{"key": "value"}} }}
                ],
                "relationships": [
                    {{"source": "source_entity_id", "type": "RELATIONSHIP_TYPE", "target": "target_entity_id" }}
                ]
            }}
            
            Ensure that relationship source and target names match exactly with the entity names.
            
            Text to analyze:
            {text}
            """
            self.pipeline_logger.log_step(document_id, "graph_extraction", "calling_openai",
                                          details={"chunk_index": chunk_index, "prompt_length": len(prompt)})
            openai_api_key = os.getenv("OPENAI_API_KEY") or getattr(settings, "OPENAI_API_KEY", None)
            if not openai_api_key:
                raise ValueError("Missing OPENAI_API_KEY environment variable or setting")
            
            # Instantiate a client and use the new API:
            client = OpenAI(api_key=openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o",  # Adjust model if needed
                messages=[
                    {"role": "system", "content": "You are a knowledge graph extraction tool that identifies entities and relationships in text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
            )
            # Access response content using attribute access:
            result_text = response.choices[0].message.content
            self.pipeline_logger.log_step(document_id, "graph_extraction", "received_response",
                                          details={"chunk_index": chunk_index, "response_length": len(result_text)})
            json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)
            else:
                json_match = re.search(r'(\{.*\})', result_text, re.DOTALL)
                if json_match:
                    result_text = json_match.group(1)
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response from OpenAI: {result_text[:200]}...")
                result = {"entities": [], "relationships": []}
            if document_id:
                for entity in result.get("entities", []):
                    if "properties" not in entity:
                        entity["properties"] = {}
                    entity["properties"]["document_id"] = document_id
                    if chunk_index is not None:
                        entity["properties"]["chunk_index"] = chunk_index
                for relationship in result.get("relationships", []):
                    if "properties" not in relationship:
                        relationship["properties"] = {}
                    relationship["properties"]["document_id"] = document_id
                    if chunk_index is not None:
                        relationship["properties"]["chunk_index"] = chunk_index
            for entity in result.get("entities", []):
                original_type = entity["type"]
                entity["type"] = SchemaManager.normalize_entity_type(entity["type"])
                if original_type != entity["type"]:
                    self.pipeline_logger.log_step(document_id, "graph_extraction", "entity_normalized",
                                                  details={"chunk_index": chunk_index, "original_type": original_type, "normalized_type": entity["type"]})
            for relationship in result.get("relationships", []):
                original_type = relationship["type"]
                relationship["type"] = SchemaManager.normalize_relationship_type(relationship["type"])
                if original_type != relationship["type"]:
                    self.pipeline_logger.log_step(document_id, "graph_extraction", "relationship_normalized",
                                                  details={"chunk_index": chunk_index, "original_type": original_type, "normalized_type": relationship["type"]})
            entity_count = len(result.get("entities", []))
            relationship_count = len(result.get("relationships", []))
            self.pipeline_logger.log_step(document_id, "graph_extraction", "completed",
                                          details={"chunk_index": chunk_index, "entity_count": entity_count, "relationship_count": relationship_count})
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error extracting entities and relationships: {error_msg}")
            self.pipeline_logger.log_step(document_id, "graph_extraction", "error",
                                          details={"chunk_index": chunk_index, "error": error_msg})
            return {"entities": [], "relationships": [], "error": error_msg}