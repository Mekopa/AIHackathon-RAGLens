
"""
Schema definitions for knowledge graph entities and relationships.
Provides standardization of entity and relationship types across the application.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Entity types schema definition
ENTITY_TYPES = {
    "Person": ["person", "individual", "people", "human"],
    "Organization": ["organization", "company", "corporation", "institution", "agency", "firm"],
    "Location": ["location", "place", "country", "city", "region", "area", "territory"],
    "Event": ["event", "occurrence", "happening", "incident"],
    "Date": ["date", "time", "period", "year", "month", "day"],
    "Technology": ["technology", "tech", "application", "system", "platform", "software", "hardware"],
    "Concept": ["concept", "idea", "theory", "notion", "principle"],
    "Product": ["product", "goods", "service", "offering"],
    "Topic": ["topic", "subject", "theme", "field"],
    "Document": ["document", "file", "report", "paper", "publication"]
}

# Relationship types schema definition
RELATIONSHIP_TYPES = {
    "RELATED_TO": ["related to", "associated with", "connected to", "linked to"],
    "PART_OF": ["part of", "belongs to", "member of", "component of", "element of"],
    "CREATED": ["created", "developed", "produced", "made", "built", "designed"],
    "LOCATED_IN": ["located in", "based in", "situated in", "found in"],
    "WORKS_FOR": ["works for", "employed by", "staff of", "personnel of"],
    "OWNED_BY": ["owned by", "belongs to", "property of", "possession of"],
    "KNOWS": ["knows", "familiar with", "acquainted with", "associated with"],
    "HAPPENED_ON": ["happened on", "occurred on", "took place on"],
    "REFERS_TO": ["refers to", "mentions", "cites", "discusses", "describes"],
    "USES": ["uses", "utilizes", "employs", "leverages", "applies"]
}

# Visualization color mapping for entity types
ENTITY_COLORS = {
    "Person": "#E91E63",       # Pink
    "Organization": "#2196F3", # Blue
    "Location": "#4CAF50",     # Green
    "Date": "#FF9800",         # Orange
    "Concept": "#9C27B0",      # Purple
    "Event": "#F44336",        # Red
    "Topic": "#00BCD4",        # Cyan
    "Product": "#FFEB3B",      # Yellow
    "Technology": "#607D8B",   # Blue Grey
    "Document": "#795548",     # Brown
}

# Default color for entities not in the mapping
DEFAULT_ENTITY_COLOR = "#9E9E9E"  # Gray

class SchemaManager:
    """
    Provides utilities for managing the knowledge graph schema.
    """
    
    @staticmethod
    def normalize_entity_type(entity_type: str) -> str:
        """
        Normalize entity type to match schema
        
        Args:
            entity_type: The entity type to normalize
            
        Returns:
            Normalized entity type
        """
        entity_type = entity_type.lower().strip()
        
        # Direct match with main type
        for main_type, synonyms in ENTITY_TYPES.items():
            if entity_type == main_type.lower():
                return main_type
        
        # Match with synonyms
        for main_type, synonyms in ENTITY_TYPES.items():
            if any(synonym == entity_type for synonym in synonyms):
                return main_type
        
        # Partial match with synonyms
        for main_type, synonyms in ENTITY_TYPES.items():
            if any(synonym in entity_type for synonym in synonyms):
                return main_type
        
        # Default to Concept if no match found
        return "Concept"
    
    @staticmethod
    def normalize_relationship_type(relationship_type: str) -> str:
        """
        Normalize relationship type to match schema
        
        Args:
            relationship_type: The relationship type to normalize
            
        Returns:
            Normalized relationship type
        """
        relationship_type = relationship_type.upper().strip()
        
        # Direct match with main type
        for main_type in RELATIONSHIP_TYPES.keys():
            if relationship_type == main_type:
                return main_type
        
        # Convert to lowercase for synonym matching
        relationship_type_lower = relationship_type.lower()
        
        # Match with synonyms
        for main_type, synonyms in RELATIONSHIP_TYPES.items():
            if any(synonym == relationship_type_lower for synonym in synonyms):
                return main_type
        
        # Partial match with synonyms
        for main_type, synonyms in RELATIONSHIP_TYPES.items():
            if any(synonym in relationship_type_lower for synonym in synonyms):
                return main_type
        
        # Default to RELATED_TO if no match found
        return "RELATED_TO"
    
    @staticmethod
    def get_color_for_entity_type(entity_type: str) -> str:
        """
        Return a consistent color for each entity type
        
        Args:
            entity_type: Type/label of the entity
            
        Returns:
            Hex color code
        """
        return ENTITY_COLORS.get(entity_type, DEFAULT_ENTITY_COLOR)
    
    @staticmethod
    def get_all_entity_types() -> List[str]:
        """
        Get all defined entity types
        
        Returns:
            List of entity types
        """
        return list(ENTITY_TYPES.keys())
    
    @staticmethod
    def get_all_relationship_types() -> List[str]:
        """
        Get all defined relationship types
        
        Returns:
            List of relationship types
        """
        return list(RELATIONSHIP_TYPES.keys())