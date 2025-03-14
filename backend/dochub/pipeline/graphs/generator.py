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
                
            # Check if this is a Word document (DOC file)
            is_doc_file = False
            if file_path and file_path.lower().endswith('.doc'):
                is_doc_file = True
                logger.info(f"Detected DOC file, applying special graph processing: {document_name}")
                
            all_entities = []
            all_relationships = []
            
            # Process each chunk
            for i, chunk in enumerate(chunks):
                if not chunk or len(chunk.strip()) < 50:
                    continue
                
                # Clean chunk text for graph processing
                cleaned_chunk = self._clean_chunk_for_graph(chunk, is_doc_file)
                if not cleaned_chunk or len(cleaned_chunk.strip()) < 50:
                    logger.warning(f"Chunk {i} was filtered out after cleaning, skipping")
                    continue
                    
                print(f"Processing chunk {i+1}/{len(chunks)} for document {document_id}")
                result = self.extract_entities_and_relationships(cleaned_chunk, document_id, i)
                
                # Filter out document format-related entities and relationships for DOC files
                if is_doc_file:
                    result = self._filter_doc_metadata_entities(result)
                
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
            
    def _clean_chunk_for_graph(self, chunk, is_doc_file=False):
        """
        Clean a text chunk before using it for graph extraction
        
        Args:
            chunk: The text chunk to clean
            is_doc_file: Whether this chunk is from a DOC file
            
        Returns:
            Cleaned text chunk
        """
        # Basic cleaning for all documents
        cleaned_text = chunk.strip()
        
        # Special handling for DOC files - be more selective in what we filter
        if is_doc_file:
            # Log original chunk length for debugging
            logger.info(f"Original DOC chunk length: {len(cleaned_text)} characters")
            
            # First, check for LibreOffice or other converters' metadata at the beginning
            # This typically appears at the start of the file
            converter_patterns = [
                r'^convert\s+.*?Documents\/.*?\.doc\s+as\s+a\s+Writer\s+document.*?\s+using\s+filter.*?\n',
                r'^LibreOffice.*?converting.*?\n',
                r'^.*?converting\s+to\s+.*?format.*?\n',
            ]
            
            for pattern in converter_patterns:
                cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE | re.MULTILINE)
            
            # Only remove specific metadata patterns that are causing problems
            # We'll be more targeted to preserve meaningful content
            metadata_patterns = [
                r'Microsoft\s+Office\s+Word.*?Document',
                r'Word\.Document\.[0-9\.]+',
                r'MSWordDoc',
                r'VBA_PROJECT_CUR',
                r'Content-Type:.*?application\/msword',
                r'Content_Types\.xml',
                r'_rels\/\.rels',
                r'theme\/theme\/themeManager\.xml',
                r'theme\/theme\/theme[0-9]+\.xml',
                r'_rels\/themeManager\.xml\.rels',
                r'clrMap',
            ]
            
            # Apply just the metadata patterns - more selective approach
            for pattern in metadata_patterns:
                cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
            
            # Instead of filtering whole lines, just remove specific patterns of binary data
            # Remove sequences that look like binary data but preserve normal text
            binary_patterns = [
                r'[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}',  # GUIDs
                r'(?<![a-zA-Z0-9])[a-zA-Z0-9]{30,}(?![a-zA-Z0-9])',  # Very long alphanumeric sequences (likely binary)
                r'\{\\[^{}]+\}',  # RTF-like control sequences
                r'docProps\/.*?\.xml',  # Word XML files
                r'word\/.*?\.xml',      # Word XML files
            ]
            
            for pattern in binary_patterns:
                cleaned_text = re.sub(pattern, ' ', cleaned_text)
            
            # Remove consecutive non-word characters (more than 5 in a row)
            cleaned_text = re.sub(r'[^\w\s,.;:?!()-]{5,}', ' ', cleaned_text)
            
            # Normalize whitespace but preserve paragraph breaks
            cleaned_text = re.sub(r'\s{2,}', ' ', cleaned_text)
            
            # Log cleaned chunk length
            logger.info(f"Cleaned DOC chunk length: {len(cleaned_text)} characters")
            
            # If we've filtered too much, use the original chunk
            if len(cleaned_text.strip()) < 100 and len(chunk.strip()) > 500:
                logger.warning("Cleaning removed too much content, using original chunk with minimal cleaning")
                # Just apply minimal cleaning to the original
                cleaned_text = chunk.strip()
                # Remove only the most problematic patterns
                for pattern in metadata_patterns:
                    cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
            
        return cleaned_text
        
    def _filter_doc_metadata_entities(self, result):
        """
        Filter out document format-related entities and relationships
        
        Args:
            result: The extraction result
            
        Returns:
            Filtered result
        """
        if not result or not isinstance(result, dict):
            return result
            
        # Count original entities and relationships for logging
        original_entity_count = len(result.get('entities', []))
        original_relationship_count = len(result.get('relationships', []))
        
        # List of specific terms that definitely indicate document metadata
        metadata_terms = [
            'microsoft office word', 'msworddoc', 'word.document', 
            'vba_project', 'normal.dot', 'content_types.xml', '_rels/.rels',
            'theme', 'thememanager.xml', 'theme1.xml', 'clrmap',
            'xml', 'rels', 'stylesheet', 'docprops', 'writer', 'convert',
            'libreoffice', 'openoffice'
        ]
        
        # Also exact match patterns that look like Word XML paths
        path_patterns = [
            r'.*\.xml$',
            r'.*\.rels$',
            r'theme\/.*',
            r'_rels\/.*',
            r'word\/.*',
            r'docProps\/.*',
        ]
        
        # Filter entities, but be more permissive
        filtered_entities = []
        filtered_entity_ids = set()
        
        for entity in result.get('entities', []):
            # Check if entity name contains metadata terms
            entity_name = entity.get('name', '').lower()
            entity_id = entity.get('id', '').lower()
            
            # Only filter if the entity matches document format terms or patterns
            should_filter = False
            
            # Check for metadata terms
            for term in metadata_terms:
                if term in entity_name or term in entity_id:
                    logger.info(f"Filtering out document metadata entity (term match): {entity_name}")
                    should_filter = True
                    filtered_entity_ids.add(entity_id)
                    break
                    
            # Check for path patterns
            if not should_filter:
                for pattern in path_patterns:
                    if re.match(pattern, entity_name, re.IGNORECASE) or re.match(pattern, entity_id, re.IGNORECASE):
                        logger.info(f"Filtering out document metadata entity (pattern match): {entity_name}")
                        should_filter = True
                        filtered_entity_ids.add(entity_id)
                        break
            
            # Check if entity type is "Unknown" - likely metadata
            if not should_filter and entity.get('type', '') == 'Unknown':
                logger.info(f"Filtering out entity with Unknown type: {entity_name}")
                should_filter = True
                filtered_entity_ids.add(entity_id)
                    
            if not should_filter:
                filtered_entities.append(entity)
        
        # Filter relationships that reference filtered entities
        filtered_relationships = []
        for rel in result.get('relationships', []):
            source = rel.get('source', '').lower()
            target = rel.get('target', '').lower()
            
            if source not in filtered_entity_ids and target not in filtered_entity_ids:
                filtered_relationships.append(rel)
        
        # Log filtering results
        filtered_entity_count = len(filtered_entities)
        filtered_relationship_count = len(filtered_relationships)
        
        logger.info(f"Entity filtering: {original_entity_count} -> {filtered_entity_count} ({original_entity_count - filtered_entity_count} removed)")
        logger.info(f"Relationship filtering: {original_relationship_count} -> {filtered_relationship_count} ({original_relationship_count - filtered_relationship_count} removed)")
        
        # If we've filtered too much (more than 90% of entities), 
        # keep the original entities as we might have been too aggressive
        if filtered_entity_count < original_entity_count * 0.1 and original_entity_count > 3:
            logger.warning("Filtering removed too many entities, using original entities")
            return result
            
        return {
            'entities': filtered_entities,
            'relationships': filtered_relationships
        }

    def extract_entities_and_relationships(self, text, document_id=None, chunk_index=None):
        try:
            self.pipeline_logger.log_step(document_id, "graph_extraction", "started", details={"chunk_index": chunk_index})
            entity_types_str = ", ".join(ENTITY_TYPES.keys())
            relationship_types_str = ", ".join(RELATIONSHIP_TYPES.keys())
            
            # Determine if this chunk is likely from a Word document (look for patterns)
            is_likely_word_doc = any(term in text.lower() for term in ['microsoft', 'word.document', 'msworddoc'])
            
            # Create a more robust prompt with special instructions for Word docs
            prompt = f"""
            Extract meaningful entities and relationships from the following text.
            
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
            
            {"IMPORTANT: This text appears to be from a Word document. IGNORE any document metadata or formatting information. Focus ONLY on extracting REAL entities and relationships from the content of the document. DO NOT include Microsoft Word, XML, Document, or other document format information as entities." if is_likely_word_doc else ""}
            
            {"If the text appears to contain non-meaningful content or binary data, try to identify any meaningful segments and only extract entities and relationships from those parts." if is_likely_word_doc else ""}
            
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