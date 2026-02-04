"""
Data processing modules for the RAG system.

Provides text processing, attachment processing, and metadata extraction.
"""

from .text_processor import TextProcessor
from .attachment_processor import AttachmentProcessor
from .metadata_extractor import MetadataExtractor

__all__ = ["TextProcessor", "AttachmentProcessor", "MetadataExtractor"]
