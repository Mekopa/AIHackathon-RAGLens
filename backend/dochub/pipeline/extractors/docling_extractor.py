import logging
import os
from .base import TextExtractor

logger = logging.getLogger(__name__)

class DoclingExtractor(TextExtractor):
    """Text extractor implementation using Mistral OCR API instead of Docling"""

    def extract(self, file_path):
        """Robust text extractor with multiple fallback methods"""
    
    def extract(self, file_path):
        """
        Extract text from documents with automatic fallback mechanisms
        
        Args:
            file_path: Path to document file
            
        Returns:
            str: Extracted text content
        """
        # Get file extension for format-specific handling
        ext = file_path.split(".")[-1].lower()
        logger.info(f"Extracting text from {file_path} (format: {ext})")
        
        # Handle plain text files first (simplest case)
        if ext == "txt":
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                    logger.info(f"Successfully extracted {len(text)} characters from text file")
                    return text
            except UnicodeDecodeError:
                # Try different encoding if UTF-8 fails
                try:
                    with open(file_path, "r", encoding="latin-1") as f:
                        text = f.read()
                        logger.info(f"Successfully extracted {len(text)} characters using latin-1 encoding")
                        return text
                except Exception as e:
                    logger.error(f"Failed to read text file with latin-1 encoding: {str(e)}")
                    return ""
            except Exception as e:
                logger.error(f"Failed to read text file: {str(e)}")
                return ""

        # PDF extraction with multiple fallback options
        if ext == "pdf":
            # Try docling first if available
            try:
                logger.info("Attempting to extract PDF with docling")
                # Import here to avoid errors if docling is not installed
                from docling.document_converter import DocumentConverter, PdfFormatOption
                from docling.datamodel.base_models import InputFormat
                from docling.datamodel.pipeline_options import PdfPipelineOptions
                from docling.models.tesseract_ocr_cli_model import TesseractCliOcrOptions

                # Configure docling options
                ocr_options = TesseractCliOcrOptions()
                pdf_pipeline_options = PdfPipelineOptions(do_ocr=True, ocr_options=ocr_options, dpi=300)
                
                converter_options = {}
                converter_options[InputFormat.PDF] = PdfFormatOption(pipeline_options=pdf_pipeline_options)
                
                # Convert and extract text
                converter = DocumentConverter(format_options=converter_options)
                doc = converter.convert(file_path)
                text = doc.document.export_to_text()
                
                logger.info(f"Successfully extracted {len(text)} characters with docling")
                return text
                
            except ImportError as e:
                logger.warning(f"Docling not available, falling back to pdfminer {e}")
                # Fall back to pdfminer
                try:
                    import pdfminer.high_level
                    with open(file_path, 'rb') as file:
                        text = pdfminer.high_level.extract_text(file)
                        logger.info(f"Successfully extracted {len(text)} characters with pdfminer")
                        return text
                except Exception as pdf_error:
                    logger.error(f"PDF extraction with pdfminer failed: {str(pdf_error)}")
                    
            except Exception as e:
                logger.error(f"Docling PDF extraction failed: {str(e)}")
                # Continue to pdfminer fallback
                try:
                    import pdfminer.high_level
                    with open(file_path, 'rb') as file:
                        text = pdfminer.high_level.extract_text(file)
                        logger.info(f"Successfully extracted {len(text)} characters with pdfminer fallback")
                        return text
                except Exception as pdf_error:
                    logger.error(f"PDF extraction with pdfminer failed: {str(pdf_error)}")
        
        # DOCX extraction
        elif ext == "docx":
            try:
                logger.info("Extracting DOCX with docx2txt")
                import docx2txt
                text = docx2txt.process(file_path)
                logger.info(f"Successfully extracted {len(text)} characters from DOCX")
                return text
            except Exception as docx_error:
                logger.error(f"DOCX extraction failed: {str(docx_error)}")
        
        # Add more file types as needed
        
        # If all extraction methods fail, return empty string
        logger.warning(f"No successful extraction method for {file_path}")
        return ""
