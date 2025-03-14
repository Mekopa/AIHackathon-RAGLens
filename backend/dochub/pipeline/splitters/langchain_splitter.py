# dochub/pipeline/splitters/langchain_splitter.py

import logging
import re
from .base import TextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

# Define language specific separators
LANGUAGE_SEPARATORS = {
    'en': ["\n\n", "\n", ". ", "! ", "? ", ";", ":", " ", ""],  # English
    # Lithuanian - with specific punctuation patterns
    'lt': [
        "\n\n", 
        "\n", 
        ". ", 
        "! ", 
        "? ", 
        "; ", 
        ": ", 
        "– ",  # Lithuanian dash
        "— ",  # Lithuanian em dash
        "-",   # Regular hyphen
        " ",   # Space
        ""
    ],
    # Turkish - with specific punctuation patterns
    'tr': [
        "\n\n", 
        "\n", 
        ". ", 
        "! ", 
        "? ", 
        "; ", 
        ": ", 
        "ve ",  # Turkish "and"
        "ile ",  # Turkish "with"
        "için ", # Turkish "for"
        " ", 
        ""
    ],
}

def detect_language_for_splitting(text):
    """
    Detect language of the given text to choose appropriate splitting strategy
    
    Args:
        text: Input text
        
    Returns:
        str: Language code or 'en' as fallback
    """
    if not text or len(text.strip()) < 100:
        return 'en'  # Default to English for very short texts
    
    # First check for Lithuanian-specific word patterns
    # This is especially helpful for DOC files where character encoding might be problematic
    if any(word in text.lower() for word in ['teism', 'lietuv', 'valstyb', 'teisė', 'įstatymas', 'nutartis']):
        logger.info("Found Lithuanian keywords in text, assuming Lithuanian document for splitting")
        return 'lt'

    # Check for specific character markers for Lithuanian and Turkish
    # Check early before other detection methods
    if re.search(r'[\u0104\u0105\u010C\u010D\u0116\u0117\u012E\u012F\u0160\u0161\u016A\u016B\u017D\u017E]', text[:10000]):
        logger.info("Found Lithuanian characters, using Lithuanian language for splitting")
        return 'lt'
    elif re.search(r'[\u00C7\u00E7\u011E\u011F\u0130\u0131\u015E\u015F\u00D6\u00F6\u00DC\u00FC]', text[:10000]):
        logger.info("Found Turkish characters, using Turkish language for splitting")
        return 'tr'
    
    try:
        # Sample multiple parts of the text for more accurate detection
        samples = []
        text_len = len(text)
        
        # Take samples from beginning, middle, and end
        if text_len > 6000:
            samples.append(text[:2000])
            samples.append(text[text_len//2-1000:text_len//2+1000])
            samples.append(text[-2000:])
        else:
            samples.append(text[:min(2000, text_len)])
        
        # Detect language for each sample
        lang_counts = {}
        for sample in samples:
            try:
                lang = detect(sample)
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            except:
                continue
        
        # Find most common language
        if lang_counts:
            most_common_lang = max(lang_counts.items(), key=lambda x: x[1])[0]
        else:
            most_common_lang = 'en'
        
        # Map language detector codes to our codes
        # Lithuanian might be detected as 'lt' by langdetect
        if most_common_lang in ['lt', 'lv', 'et', 'pl']:
            logger.info(f"Detected Baltic/Eastern European language ({most_common_lang}), using Lithuanian for splitting")
            most_common_lang = 'lt'
        # langdetect might falsely identify Lithuanian as other European languages
        elif most_common_lang in ['pt', 'ca', 'ro', 'cs', 'sk', 'sl']:
            # Check for common Lithuanian word patterns
            if any(word in text.lower() for word in ['teism', 'lietuv', 'valstyb', 'teisė', 'įstatymas']):
                logger.info(f"Detected {most_common_lang} but found Lithuanian keywords, overriding to Lithuanian for splitting")
                most_common_lang = 'lt'
            else:
                # Do one more Lithuanian character check
                if len(re.findall(r'[ąčęėįšųūž]', text[:10000])) > 2:
                    logger.info(f"Detected {most_common_lang} but found multiple Lithuanian characters, overriding to Lithuanian")
                    most_common_lang = 'lt'
        
        logger.info(f"Splitter detected language: {most_common_lang}")
        return most_common_lang
    
    except LangDetectException:
        logger.warning("Language detection failed in splitter, checking for specific patterns")
        
        # Check for Lithuanian word patterns
        if any(word in text.lower() for word in ['teism', 'lietuv', 'valstyb', 'teisė', 'įstatymas']):
            logger.info("Found Lithuanian keywords after failed detection in splitter")
            return 'lt'
        
        # One more check for Lithuanian special characters
        if len(re.findall(r'[ąčęėįšųūž]', text[:10000])) > 2:
            logger.info("Found multiple Lithuanian characters after failed detection")
            return 'lt'
            
        logger.warning("No specific language patterns found in splitter, using English as fallback")
        return 'en'

class LangchainSplitter(TextSplitter):
    """Text splitter implementation using LangChain's RecursiveCharacterTextSplitter"""
    
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        """
        Initialize with default chunk size and overlap
        
        Args:
            chunk_size: Default chunk size
            chunk_overlap: Default chunk overlap
        """
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap
    
    def split(self, text, chunk_size=None, chunk_overlap=None):
        """
        Split text into chunks using LangChain's RecursiveCharacterTextSplitter
        
        Args:
            text: Text to split
            chunk_size: Maximum size of each chunk (overrides default)
            chunk_overlap: Overlap between chunks (overrides default)
            
        Returns:
            list: List of text chunks
        """
        if not text:
            logger.warning("Empty text provided to splitter")
            # Splitter should fail with empty text so we know extraction failed
            return []
        
        # Use provided parameters or fall back to defaults
        chunk_size = chunk_size or self.default_chunk_size
        chunk_overlap = chunk_overlap or self.default_chunk_overlap
        
        # Handle very short text (too small to properly chunk)
        if len(text) < 100:
            logger.warning(f"Text is very short ({len(text)} chars), might be insufficient for meaningful processing")
            
            # If text is extremely short (likely extraction failure)
            if len(text.strip()) < 10:
                logger.error(f"Text is too short to be meaningful ({len(text)} chars)")
                return []
            
            # For short but non-empty text, return as single chunk
            return [text]
        
        # Adjust chunk size for smaller texts
        if len(text) < chunk_size:
            adjusted_chunk_size = max(100, len(text))
            adjusted_chunk_overlap = min(20, adjusted_chunk_size // 5)
            logger.info(f"Adjusting chunk parameters for small text: size={adjusted_chunk_size}, overlap={adjusted_chunk_overlap}")
            chunk_size = adjusted_chunk_size
            chunk_overlap = adjusted_chunk_overlap
        
        try:
            # Detect language to use appropriate separators
            lang = detect_language_for_splitting(text)
            
            # Get language-specific separators or default to English
            separators = LANGUAGE_SEPARATORS.get(lang, LANGUAGE_SEPARATORS['en'])
            
            # Log language detection
            logger.info(f"Using language '{lang}' for text splitting")
            
            # Create splitter with specified parameters and language-aware separators
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=separators
            )
            
            # Split text and return chunks
            chunks = splitter.split_text(text)
            
            # If no chunks were created (unusual but possible)
            if not chunks:
                logger.warning("Splitting produced zero chunks, falling back to single chunk")
                return [text]
                
            logger.info(f"Split text into {len(chunks)} chunks (size: {chunk_size}, overlap: {chunk_overlap})")
            return chunks
            
        except Exception as e:
            logger.error(f"Error splitting text with LangChain: {str(e)}")
            
            # Fall back to simple splitting
            try:
                logger.info("Using fallback splitting method")
                simple_chunks = []
                
                # Handle case where text is shorter than chunk_size
                if len(text) <= chunk_size:
                    simple_chunks = [text]
                else:
                    # Basic splitting by character count with overlap
                    for i in range(0, len(text), chunk_size - chunk_overlap):
                        end = min(i + chunk_size, len(text))
                        chunk = text[i:end]
                        if chunk.strip():  # Only add non-empty chunks
                            simple_chunks.append(chunk)
                
                # If we still have no chunks, use text as a single chunk
                if not simple_chunks:
                    logger.warning("Fallback splitting produced no chunks, using single chunk")
                    return [text]
                    
                logger.info(f"Fallback splitting created {len(simple_chunks)} chunks")
                return simple_chunks
                
            except Exception as fallback_error:
                logger.error(f"Fallback splitting failed: {str(fallback_error)}")
                
                # Last resort - if the text exists but we can't split it
                if text and len(text.strip()) > 0:
                    logger.warning("Using text as a single chunk after all splitting methods failed")
                    return [text]
                else:
                    # If we get here, we truly have nothing to work with
                    logger.error("No valid text to split after all attempts")
                    return []