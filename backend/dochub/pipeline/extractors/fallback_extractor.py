# dochub/pipeline/extractors/fallback_extractor.py

import os
import logging
from .base import TextExtractor

logger = logging.getLogger(__name__)

class FallbackTextExtractor(TextExtractor):
    """Fallback text extractor when docling is not available"""
    
    def extract(self, file_path):
        """
        Extract text from document files without docling dependency
        
        Args:
            file_path: Path to the document file
            
        Returns:
            str: Extracted text content
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return ""
        
        ext = file_path.split(".")[-1].lower()
        logger.info(f"Extracting text from {file_path} (format: {ext})")
        
        # For plain text files
        if ext == "txt":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                    logger.info(f"Extracted {len(text)} characters from text file")
                    return text
            except UnicodeDecodeError:
                # Try different encoding
                with open(file_path, "r", encoding="latin-1") as f:
                    text = f.read()
                    logger.info(f"Extracted {len(text)} characters with latin-1 encoding")
                    return text
        
        # For PDF files
        if ext == "pdf":
            try:
                # Use pdfminer for PDF extraction
                import pdfminer.high_level
                with open(file_path, 'rb') as file:
                    text = pdfminer.high_level.extract_text(file)
                    logger.info(f"Extracted {len(text)} characters from PDF with pdfminer")
                    if text and len(text.strip()) > 0:
                        return text
                    else:
                        logger.warning("PDFMiner extracted empty text, trying docling fallback")
            except Exception as pdf_error:
                logger.error(f"PDF extraction failed: {str(pdf_error)}")
            
            # If pdfminer fails or returns empty text, try docling as a second option
            try:
                from .docling_extractor import DoclingExtractor
                docling = DoclingExtractor()
                text = docling.extract(file_path)
                logger.info(f"Extracted {len(text)} characters from PDF with docling as fallback")
                return text
            except Exception as docling_error:
                logger.error(f"Docling fallback extraction failed: {str(docling_error)}")
                return ""
        
        # For DOCX files
        if ext == "docx":
            try:
                import docx2txt
                text = docx2txt.process(file_path)
                logger.info(f"Extracted {len(text)} characters from DOCX")
                return text
            except Exception as docx_error:
                logger.error(f"DOCX extraction failed: {str(docx_error)}")
                return ""
        
        # Unsupported file type
        logger.warning(f"Unsupported file format: {ext}")
        return ""
