"""
Neo4j client module for interfacing with the Neo4j graph database.
Provides functionality to store and retrieve graph data.
"""

import logging
import os
from typing import Dict, List, Any, Optional, Union

from django.conf import settings
from neo4j import GraphDatabase, Driver, Session, Transaction

from .schema import ENTITY_TYPES, RELATIONSHIP_TYPES
from ...utils.pipeline_logger import PipelineLogger

logger = logging.getLogger(__name__)

class Neo4jClient:
    """
    Client for interacting with Neo4j graph database.
    Handles connection, data storage, and queries.
    """
    
    def __init__(self, pipeline_logger=None):
        """
        Initialize Neo4j client with connection parameters from settings.
        
        Args:
            pipeline_logger: Optional PipelineLogger for tracking pipeline progress
        """
        try:
            self.uri = settings.NEO4J_URI
            self.username = settings.NEO4J_USERNAME
            self.password = settings.NEO4J_PASSWORD
            self._driver = None
            self.pipeline_logger = pipeline_logger or PipelineLogger()
        except Exception as e:
            logger.error(f"Error initializing Neo4j client: {str(e)}")
            raise
    
    @property
    def driver(self) -> Driver:
        """Get or create Neo4j driver instance."""
        if self._driver is None:
            try:
                # Check if we should use a mock driver for testing
                mock_driver = getattr(settings, 'USE_MOCK_NEO4J', False)
                
                if mock_driver:
                    # Return a simulated driver for testing
                    from unittest.mock import MagicMock
                    mock = MagicMock()
                    # Create a session method that returns a MagicMock
                    session_mock = MagicMock()
                    # Create a run method that returns a MagicMock
                    run_mock = MagicMock()
                    # Make run_mock.single() return None
                    run_mock.single.return_value = None
                    # Make run_mock iterable and return empty list
                    run_mock.__iter__ = lambda self: iter([])
                    # Set session_mock.run to return run_mock
                    session_mock.run.return_value = run_mock
                    # Set mock.session to return session_mock
                    mock.session.return_value.__enter__.return_value = session_mock
                    mock.session.return_value.__exit__ = lambda *args: None
                    
                    self._driver = mock
                    logger.info("Using MOCK Neo4j driver for testing")
                    self.pipeline_logger.log_step(None, "neo4j_connection", "established",
                                              details={"uri": self.uri, "mock": True})
                else:
                    # Use a real Neo4j driver
                    self._driver = GraphDatabase.driver(
                        self.uri, 
                        auth=(self.username, self.password)
                    )
                    self.pipeline_logger.log_step(None, "neo4j_connection", "established",
                                              details={"uri": self.uri})
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error connecting to Neo4j: {error_msg}")
                self.pipeline_logger.log_step(None, "neo4j_connection", "error",
                                            details={"uri": self.uri, "error": error_msg})
                raise
        return self._driver
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            self.pipeline_logger.log_step(None, "neo4j_connection", "closed")
    
    def create_constraints(self):
        """Create necessary constraints in Neo4j."""
        try:
            self.pipeline_logger.log_step(None, "neo4j_constraints", "started")
            with self.driver.session() as session:
                # Create constraint for Document nodes
                session.run("""
                    CREATE CONSTRAINT document_id IF NOT EXISTS
                    FOR (d:Document) REQUIRE d.id IS UNIQUE
                """)
                
                # Create constraints for each entity type
                for entity_type in ENTITY_TYPES.keys():
                    session.run(f"""
                        CREATE CONSTRAINT {entity_type.lower()}_id IF NOT EXISTS
                        FOR (e:{entity_type}) REQUIRE e.id IS UNIQUE
                    """)
            
            self.pipeline_logger.log_step(None, "neo4j_constraints", "completed", 
                                        details={"entity_types": list(ENTITY_TYPES.keys())})
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error creating Neo4j constraints: {error_msg}")
            self.pipeline_logger.log_step(None, "neo4j_constraints", "error", 
                                        details={"error": error_msg})
            raise
    
    def store_document_node(self, document_id: str, document_name: str, folder_id: str = None) -> None:
        """
        Store a document node in Neo4j.
        
        Args:
            document_id: Document UUID
            document_name: Document name
            folder_id: Optional folder UUID
        """
        try:
            self.pipeline_logger.log_step(document_id, "neo4j_store_document", "started")
            
            with self.driver.session() as session:
                cypher = """
                    MERGE (d:Document {id: $id})
                    SET d.name = $name
                """
                
                params = {
                    "id": str(document_id),
                    "name": document_name
                }
                
                if folder_id:
                    cypher += ", d.folder_id = $folder_id"
                    params["folder_id"] = str(folder_id)
                
                session.run(cypher, **params)
            
            self.pipeline_logger.log_step(document_id, "neo4j_store_document", "completed")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error storing document node: {error_msg}")
            self.pipeline_logger.log_step(document_id, "neo4j_store_document", "error", 
                                        details={"error": error_msg})
            raise
    
    def store_entities_and_relationships(self, 
                                         entities: List[Dict], 
                                         relationships: List[Dict], 
                                         document_id: str = None) -> None:
        """
        Store entities and relationships in Neo4j.
        
        Args:
            entities: List of entity dictionaries
            relationships: List of relationship dictionaries
            document_id: Optional document ID to link entities and relationships to
        """
        try:
            log_id = document_id or "bulk_import"
            self.pipeline_logger.log_step(log_id, "neo4j_store_graph", "started", 
                                        details={"entity_count": len(entities), 
                                                "relationship_count": len(relationships)})
            
            # Store entities
            entity_count = 0
            for entity in entities:
                self._store_entity(entity, document_id)
                entity_count += 1
                
                # Log progress for large batches
                if entity_count % 50 == 0:
                    self.pipeline_logger.log_step(log_id, "neo4j_store_graph", "entities_progress", 
                                                details={"processed": entity_count, "total": len(entities)})
            
            # Store relationships
            rel_count = 0
            for rel in relationships:
                self._store_relationship(rel, document_id)
                rel_count += 1
                
                # Log progress for large batches
                if rel_count % 50 == 0:
                    self.pipeline_logger.log_step(log_id, "neo4j_store_graph", "relationships_progress", 
                                                details={"processed": rel_count, "total": len(relationships)})
            
            self.pipeline_logger.log_step(log_id, "neo4j_store_graph", "completed")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error storing entities and relationships: {error_msg}")
            self.pipeline_logger.log_step(log_id, "neo4j_store_graph", "error", 
                                        details={"error": error_msg})
            raise
    
    def _store_entity(self, entity: Dict, document_id: str = None) -> None:
        """
        Store a single entity in Neo4j.
        
        Args:
            entity: Entity dictionary
            document_id: Optional document ID to link entity to
        """
        with self.driver.session() as session:
            # Extract entity data
            entity_id = entity.get("id")
            entity_type = entity.get("type")
            entity_name = entity.get("name")
            properties = entity.get("properties", {})
            
            # Create entity node
            cypher = f"""
                MERGE (e:{entity_type} {{id: $id}})
                SET e.name = $name
            """
            
            # Add custom properties
            params = {
                "id": entity_id,
                "name": entity_name
            }
            
            # Add any additional properties
            for key, value in properties.items():
                if key not in ["id", "name"]:
                    cypher += f"SET e.{key} = ${key}\n"
                    params[key] = value
            
            # Link to document if provided
            if document_id:
                cypher += """
                    WITH e
                    MATCH (d:Document {id: $document_id})
                    MERGE (e)-[:APPEARS_IN]->(d)
                """
                params["document_id"] = str(document_id)
            
            # Execute query
            session.run(cypher, **params)
    
    def _store_relationship(self, rel: Dict, document_id: str = None) -> None:
        """
        Store a single relationship in Neo4j.
        
        Args:
            rel: Relationship dictionary
            document_id: Optional document ID to link relationship to
        """
        with self.driver.session() as session:
            # Extract relationship data
            source_id = rel.get("source")
            target_id = rel.get("target")
            rel_type = rel.get("type")
            properties = rel.get("properties", {})
            
            # Create params dict
            params = {
                "source_id": source_id,
                "target_id": target_id,
                "document_id": str(document_id) if document_id else None
            }
            
            # Add properties to params
            for key, value in properties.items():
                params[key] = value
            
            # Build property string for relationship creation
            prop_string = ""
            if properties:
                prop_parts = []
                for key in properties.keys():
                    if key != "document_id":  # Skip document_id as it's handled separately
                        prop_parts.append(f"{key}: ${key}")
                
                if prop_parts:
                    prop_string = "{" + ", ".join(prop_parts) + "}"
            
            # Create relationship
            cypher = f"""
                MATCH (source) WHERE source.id = $source_id
                MATCH (target) WHERE target.id = $target_id
                MERGE (source)-[r:{rel_type} {prop_string}]->(target)
            """
            
            # Link to document if provided
            if document_id:
                cypher += """
                    WITH r
                    SET r.document_id = $document_id
                """
            
            # Execute query
            session.run(cypher, **params)
    
    def get_document_graph(self, document_id: str) -> List[Dict]:
        """
        Get graph data for a document.
        
        Args:
            document_id: Document UUID
            
        Returns:
            List of path records containing nodes and relationships
        """
        try:
            self.pipeline_logger.log_step(document_id, "neo4j_get_document_graph", "started")
            
            with self.driver.session() as session:
                result = session.run("""
                    MATCH path = (e1)-[r]-(e2)
                    WHERE r.document_id = $document_id
                    RETURN path
                """, document_id=str(document_id))
                
                records = list(result)
                
                self.pipeline_logger.log_step(document_id, "neo4j_get_document_graph", "completed", 
                                            details={"record_count": len(records)})
                
                return records
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting document graph: {error_msg}")
            self.pipeline_logger.log_step(document_id, "neo4j_get_document_graph", "error", 
                                        details={"error": error_msg})
            return []
    
    def get_folder_graph(self, folder_id: str) -> List[Dict]:
        """
        Get graph data for documents in a folder.
        
        Args:
            folder_id: Folder UUID
            
        Returns:
            List of path records containing nodes and relationships
        """
        try:
            self.pipeline_logger.log_step(folder_id, "neo4j_get_folder_graph", "started")
            
            with self.driver.session() as session:
                # First get all documents in the folder
                result = session.run("""
                    MATCH (d:Document)
                    WHERE d.folder_id = $folder_id
                    RETURN d.id AS document_id
                """, folder_id=str(folder_id))
                
                document_ids = [record["document_id"] for record in result]
                
                self.pipeline_logger.log_step(folder_id, "neo4j_get_folder_graph", "documents_found", 
                                            details={"document_count": len(document_ids)})
                
                if not document_ids:
                    return []
                
                # Then get the graph for all documents
                result = session.run("""
                    MATCH path = (e1)-[r]-(e2)
                    WHERE r.document_id IN $document_ids
                    RETURN path
                """, document_ids=document_ids)
                
                records = list(result)
                
                self.pipeline_logger.log_step(folder_id, "neo4j_get_folder_graph", "completed", 
                                            details={"record_count": len(records)})
                
                return records
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting folder graph: {error_msg}")
            self.pipeline_logger.log_step(folder_id, "neo4j_get_folder_graph", "error", 
                                        details={"error": error_msg})
            return []
    
    def get_entity_relationships(self, entity_name: str, entity_type: str = None) -> List[Dict]:
        """
        Get relationships for a specific entity.
        
        Args:
            entity_name: Name of the entity
            entity_type: Optional entity type to filter by
            
        Returns:
            List of records containing related entities and relationships
        """
        try:
            log_id = f"entity_{entity_name}"
            self.pipeline_logger.log_step(log_id, "neo4j_get_entity_relationships", "started", 
                                        details={"entity_name": entity_name, "entity_type": entity_type})
            
            with self.driver.session() as session:
                cypher = """
                    MATCH (e)-[r]-(related)
                    WHERE e.name = $name
                """
                
                if entity_type:
                    cypher += f" AND e:{entity_type}"
                
                cypher += " RETURN e, r, related"
                
                result = session.run(cypher, name=entity_name)
                
                records = list(result)
                
                self.pipeline_logger.log_step(log_id, "neo4j_get_entity_relationships", "completed", 
                                            details={"record_count": len(records)})
                
                return records
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting entity relationships: {error_msg}")
            self.pipeline_logger.log_step(log_id, "neo4j_get_entity_relationships", "error", 
                                        details={"error": error_msg})
            return []
    
    def get_entity_by_id(self, entity_id: str) -> Optional[Dict]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity record or None if not found
        """
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (e)
                    WHERE e.id = $id
                    RETURN e
                """, id=entity_id)
                
                record = result.single()
                return record["e"] if record else None
        except Exception as e:
            logger.error(f"Error getting entity by ID: {str(e)}")
            return None
    
    def delete_document_data(self, document_id: str) -> None:
        """
        Delete all graph data for a document.
        
        Args:
            document_id: Document UUID
        """
        try:
            self.pipeline_logger.log_step(document_id, "neo4j_delete_document", "started")
            
            with self.driver.session() as session:
                # Delete relationships with this document_id
                relationship_result = session.run("""
                    MATCH ()-[r]-()
                    WHERE r.document_id = $document_id
                    WITH count(r) as rel_count
                    MATCH ()-[r]-()
                    WHERE r.document_id = $document_id
                    DELETE r
                    RETURN rel_count
                """, document_id=str(document_id))
                
                rel_count = relationship_result.single()["rel_count"] if relationship_result.single() else 0
                
                # Delete the document node
                document_result = session.run("""
                    MATCH (d:Document {id: $document_id})
                    WITH count(d) as doc_count
                    MATCH (d:Document {id: $document_id})
                    DETACH DELETE d
                    RETURN doc_count
                """, document_id=str(document_id))
                
                doc_count = document_result.single()["doc_count"] if document_result.single() else 0
                
                self.pipeline_logger.log_step(document_id, "neo4j_delete_document", "completed", 
                                            details={"relationships_deleted": rel_count,
                                                    "documents_deleted": doc_count})
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error deleting document data: {error_msg}")
            self.pipeline_logger.log_step(document_id, "neo4j_delete_document", "error", 
                                        details={"error": error_msg})
            raise
    
    def __enter__(self):
        """Context manager enter method."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit method."""
        self.close()