"""
Attachment processor for handling multi-modal files (images, documents, logs).
"""

import os
import logging
import mimetypes
from typing import Dict, Any, List, Optional, Union, BinaryIO
from pathlib import Path
import base64
import hashlib

try:
    from PIL import Image
    import pytesseract
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import pandas as pd
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False


class AttachmentProcessor:
    """
    Processes various types of attachments for the RAG system.
    
    Handles images, documents, logs, and other file types with appropriate
    text extraction and metadata generation.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize attachment processor.
        
        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available."""
        if not PIL_AVAILABLE:
            self.logger.warning("PIL/Pillow not available. Image processing disabled.")
        if not PDF_AVAILABLE:
            self.logger.warning("pdfplumber not available. PDF processing disabled.")
        if not DOCX_AVAILABLE:
            self.logger.warning("python-docx not available. Word document processing disabled.")
        if not EXCEL_AVAILABLE:
            self.logger.warning("pandas not available. Excel processing disabled.")
    
    def get_file_type(self, file_path: str, mime_type: Optional[str] = None) -> str:
        """
        Determine file type from path or MIME type.
        
        Args:
            file_path: Path to the file
            mime_type: MIME type if known
            
        Returns:
            File type category ('image', 'document', 'text', 'spreadsheet', 'binary')
        """
        if mime_type:
            mime_type = mime_type.lower()
        else:
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type:
                mime_type = mime_type.lower()
        
        if not mime_type:
            return 'binary'
        
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('text/'):
            return 'text'
        elif mime_type in ['application/pdf']:
            return 'document'
        elif mime_type in [
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]:
            return 'document'
        elif mime_type in [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/csv'
        ]:
            return 'spreadsheet'
        elif mime_type in ['application/json', 'application/xml']:
            return 'text'
        else:
            return 'binary'
    
    def calculate_file_hash(self, file_data: bytes) -> str:
        """
        Calculate SHA-256 hash of file data.
        
        Args:
            file_data: File content as bytes
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(file_data).hexdigest()
    
    def process_image(self, image_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Process image file and extract text using OCR.
        
        Args:
            image_data: Image file data as bytes
            filename: Original filename
            
        Returns:
            Dictionary with processed image information
        """
        if not PIL_AVAILABLE:
            return {
                'type': 'image',
                'filename': filename,
                'size': len(image_data),
                'error': 'PIL/Pillow not available for image processing'
            }
        
        try:
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            result = {
                'type': 'image',
                'filename': filename,
                'size': len(image_data),
                'format': image.format,
                'mode': image.mode,
                'width': image.width,
                'height': image.height,
                'extracted_text': '',
                'ocr_confidence': 0
            }
            
            # Extract text using OCR if available
            if pytesseract:
                try:
                    extracted_text = pytesseract.image_to_string(image)
                    result['extracted_text'] = extracted_text.strip()
                    
                    # Get OCR confidence if available
                    try:
                        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                        if confidences:
                            result['ocr_confidence'] = sum(confidences) / len(confidences)
                    except:
                        pass
                    
                    self.logger.debug(f"OCR extracted {len(result['extracted_text'])} characters from {filename}")
                except Exception as e:
                    self.logger.warning(f"OCR failed for {filename}: {e}")
                    result['ocr_error'] = str(e)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process image {filename}: {e}")
            return {
                'type': 'image',
                'filename': filename,
                'size': len(image_data),
                'error': str(e)
            }
    
    def process_pdf(self, pdf_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Process PDF file and extract text content.
        
        Args:
            pdf_data: PDF file data as bytes
            filename: Original filename
            
        Returns:
            Dictionary with processed PDF information
        """
        if not PDF_AVAILABLE:
            return {
                'type': 'document',
                'filename': filename,
                'size': len(pdf_data),
                'error': 'pdfplumber not available for PDF processing'
            }
        
        try:
            import io
            
            result = {
                'type': 'document',
                'filename': filename,
                'size': len(pdf_data),
                'format': 'pdf',
                'pages': 0,
                'extracted_text': '',
                'page_texts': []
            }
            
            with pdfplumber.open(io.BytesIO(pdf_data)) as pdf:
                result['pages'] = len(pdf.pages)
                all_text = []
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            page_text = page_text.strip()
                            all_text.append(page_text)
                            result['page_texts'].append({
                                'page': page_num + 1,
                                'text': page_text
                            })
                    except Exception as e:
                        self.logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                
                result['extracted_text'] = '\n\n'.join(all_text)
            
            self.logger.debug(f"Extracted {len(result['extracted_text'])} characters from PDF {filename}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process PDF {filename}: {e}")
            return {
                'type': 'document',
                'filename': filename,
                'size': len(pdf_data),
                'error': str(e)
            }
    
    def process_docx(self, docx_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Process Word document and extract text content.
        
        Args:
            docx_data: DOCX file data as bytes
            filename: Original filename
            
        Returns:
            Dictionary with processed document information
        """
        if not DOCX_AVAILABLE:
            return {
                'type': 'document',
                'filename': filename,
                'size': len(docx_data),
                'error': 'python-docx not available for Word document processing'
            }
        
        try:
            import io
            
            result = {
                'type': 'document',
                'filename': filename,
                'size': len(docx_data),
                'format': 'docx',
                'extracted_text': '',
                'paragraphs': []
            }
            
            doc = docx.Document(io.BytesIO(docx_data))
            all_text = []
            
            for paragraph in doc.paragraphs:
                para_text = paragraph.text.strip()
                if para_text:
                    all_text.append(para_text)
                    result['paragraphs'].append(para_text)
            
            result['extracted_text'] = '\n\n'.join(all_text)
            
            self.logger.debug(f"Extracted {len(result['extracted_text'])} characters from DOCX {filename}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process DOCX {filename}: {e}")
            return {
                'type': 'document',
                'filename': filename,
                'size': len(docx_data),
                'error': str(e)
            }
    
    def process_excel(self, excel_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Process Excel file and extract data.
        
        Args:
            excel_data: Excel file data as bytes
            filename: Original filename
            
        Returns:
            Dictionary with processed spreadsheet information
        """
        if not EXCEL_AVAILABLE:
            return {
                'type': 'spreadsheet',
                'filename': filename,
                'size': len(excel_data),
                'error': 'pandas not available for Excel processing'
            }
        
        try:
            import io
            
            result = {
                'type': 'spreadsheet',
                'filename': filename,
                'size': len(excel_data),
                'format': 'excel',
                'sheets': [],
                'extracted_text': ''
            }
            
            # Determine file format
            if filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(excel_data.decode('utf-8')))
                sheet_data = {
                    'name': 'Sheet1',
                    'rows': len(df),
                    'columns': len(df.columns),
                    'data': df.to_string()
                }
                result['sheets'].append(sheet_data)
                result['extracted_text'] = sheet_data['data']
            else:
                # Excel file
                excel_file = pd.ExcelFile(io.BytesIO(excel_data))
                all_text = []
                
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    sheet_data = {
                        'name': sheet_name,
                        'rows': len(df),
                        'columns': len(df.columns),
                        'data': df.to_string()
                    }
                    result['sheets'].append(sheet_data)
                    all_text.append(f"Sheet: {sheet_name}\n{sheet_data['data']}")
                
                result['extracted_text'] = '\n\n'.join(all_text)
            
            self.logger.debug(f"Extracted data from Excel file {filename}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process Excel file {filename}: {e}")
            return {
                'type': 'spreadsheet',
                'filename': filename,
                'size': len(excel_data),
                'error': str(e)
            }
    
    def process_text_file(self, text_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Process text file and extract content.
        
        Args:
            text_data: Text file data as bytes
            filename: Original filename
            
        Returns:
            Dictionary with processed text information
        """
        try:
            # Try to decode as UTF-8 first
            try:
                text_content = text_data.decode('utf-8')
            except UnicodeDecodeError:
                # Try other encodings
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        text_content = text_data.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # Fallback to UTF-8 with error handling
                    text_content = text_data.decode('utf-8', errors='replace')
            
            result = {
                'type': 'text',
                'filename': filename,
                'size': len(text_data),
                'format': 'text',
                'extracted_text': text_content,
                'lines': len(text_content.splitlines()),
                'characters': len(text_content)
            }
            
            # Detect if it's a log file
            if any(keyword in filename.lower() for keyword in ['log', 'trace', 'debug']):
                result['subtype'] = 'log'
                result['log_patterns'] = self._extract_log_patterns(text_content)
            
            self.logger.debug(f"Processed text file {filename}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process text file {filename}: {e}")
            return {
                'type': 'text',
                'filename': filename,
                'size': len(text_data),
                'error': str(e)
            }
    
    def _extract_log_patterns(self, text_content: str) -> List[str]:
        """
        Extract common log patterns from text content.
        
        Args:
            text_content: Log file content
            
        Returns:
            List of detected log patterns
        """
        patterns = []
        
        # Common error patterns
        error_patterns = [
            r'ERROR\s*:.*',
            r'Exception\s+.*',
            r'Traceback.*',
            r'FATAL\s*:.*',
            r'CRITICAL\s*:.*'
        ]
        
        for pattern in error_patterns:
            matches = re.findall(pattern, text_content, re.MULTILINE | re.IGNORECASE)
            patterns.extend(matches[:10])  # Limit to first 10 matches per pattern
        
        return patterns
    
    def process_attachment(
        self,
        file_data: bytes,
        filename: str,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process attachment based on file type.
        
        Args:
            file_data: File content as bytes
            filename: Original filename
            mime_type: MIME type if known
            
        Returns:
            Dictionary with processed attachment information
        """
        file_type = self.get_file_type(filename, mime_type)
        file_hash = self.calculate_file_hash(file_data)
        
        # Base result
        result = {
            'filename': filename,
            'size': len(file_data),
            'type': file_type,
            'hash': file_hash,
            'mime_type': mime_type
        }
        
        # Process based on type
        if file_type == 'image':
            result.update(self.process_image(file_data, filename))
        elif file_type == 'document':
            if filename.lower().endswith('.pdf'):
                result.update(self.process_pdf(file_data, filename))
            elif filename.lower().endswith('.docx'):
                result.update(self.process_docx(file_data, filename))
            else:
                result['error'] = f'Unsupported document format: {filename}'
        elif file_type == 'spreadsheet':
            result.update(self.process_excel(file_data, filename))
        elif file_type == 'text':
            result.update(self.process_text_file(file_data, filename))
        else:
            result['error'] = f'Unsupported file type: {file_type}'
        
        return result
    
    def is_supported_type(self, filename: str, mime_type: Optional[str] = None) -> bool:
        """
        Check if file type is supported for processing.
        
        Args:
            filename: Filename to check
            mime_type: MIME type if known
            
        Returns:
            True if supported, False otherwise
        """
        file_type = self.get_file_type(filename, mime_type)
        
        supported_types = {
            'image': PIL_AVAILABLE,
            'document': PDF_AVAILABLE or DOCX_AVAILABLE,
            'spreadsheet': EXCEL_AVAILABLE,
            'text': True
        }
        
        return supported_types.get(file_type, False)


# Import io for image processing
import io
import re
