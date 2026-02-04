"""
End-to-end integration tests for EVAgent RAG System.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.connectors import JiraConnector, ConfluenceConnector
from src.processors import TextProcessor, AttachmentProcessor, MetadataExtractor
from src.embeddings import EmbeddingService
from src.database import ChromaManager
from src.api import RAGQueryInterface


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_config(self, temp_dir):
        """Test configuration with temporary directories."""
        return {
            'jira_config': {
                'url': 'https://test.atlassian.net',
                'username': 'test@example.com',
                'api_token': 'test-token',
                'api': {'version': '3'},
                'timeout': 30,
                'projects': ['TEST'],
                'jql_filters': ['type = Bug'],
                'sync': {'batch_size': 10}
            },
            'confluence_config': {
                'url': 'https://test.atlassian.net/wiki',
                'username': 'test@example.com',
                'api_token': 'test-token',
                'api': {'version': '2'},
                'spaces': ['TEST'],
                'page_filters': ['status = current']
            },
            'embedding_config': {
                'text_model': 'sentence-transformers/all-MiniLM-L6-v2',
                'embedding_dim': 384,
                'enable_image_embeddings': False,  # Disable for tests
                'batch_size': 4
            },
            'db_config': {
                'persist_directory': str(Path(temp_dir) / 'chroma_db'),
                'collection_name': 'test_documents'
            }
        }
    
    @pytest.fixture
    def sample_jira_issue(self):
        """Sample Jira issue for testing."""
        return {
            'id': '10001',
            'key': 'TEST-123',
            'fields': {
                'summary': 'NullPointerException in authentication service',
                'description': 'Users experiencing NullPointerException during OAuth2 authentication',
                'issuetype': {'name': 'Bug'},
                'status': {'name': 'Open'},
                'priority': {'name': 'High'},
                'project': {'key': 'TEST', 'name': 'Test Project'},
                'assignee': {'displayName': 'John Doe'},
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2024-01-15T10:30:00.000+0000',
                'updated': '2024-01-16T14:45:00.000+0000',
                'labels': ['bug', 'authentication', 'urgent'],
                'components': [{'name': 'Auth'}],
                'attachment': []
            }
        }
    
    @pytest.fixture
    def sample_confluence_page(self):
        """Sample Confluence page for testing."""
        return {
            'id': '12345',
            'title': 'Authentication Service Documentation',
            'space': {'key': 'TEST', 'name': 'Test Space'},
            'status': 'current',
            'body': {
                'storage': {
                    'value': '<h1>Authentication Service</h1><p>This service handles OAuth2 authentication.</p>'
                }
            },
            'history': {
                'createdDate': '2024-01-10T09:00:00.000+0000',
                'lastUpdated': {'when': '2024-01-15T11:30:00.000+0000'},
                'createdBy': {'displayName': 'John Doe'}
            },
            'version': {'number': 3},
            'metadata': {'labels': [{'name': 'documentation'}, {'name': 'auth'}]},
            'attachments': []
        }
    
    @pytest.mark.asyncio
    async def test_jira_to_search_pipeline(self, test_config, sample_jira_issue):
        """Test complete pipeline from Jira to search."""
        
        # Mock Jira connector
        with patch('src.connectors.jira_connector.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value.json.return_value = {
                'issues': [sample_jira_issue]
            }
            
            # Initialize components
            jira_connector = JiraConnector(test_config['jira_config'])
            text_processor = TextProcessor()
            metadata_extractor = MetadataExtractor()
            
            # Mock embedding service to avoid model loading
            with patch('src.embeddings.embedding_service.SentenceTransformer') as mock_model:
                mock_model_instance = MagicMock()
                mock_model_instance.get_sentence_embedding_dimension.return_value = 384
                mock_model_instance.encode.return_value = [[0.1] * 384]  # Dummy embedding
                mock_model.return_value = mock_model_instance
                
                embedding_service = EmbeddingService(test_config['embedding_config'])
                chroma_manager = ChromaManager(test_config['db_config'])
                query_interface = RAGQueryInterface(
                    embedding_service=embedding_service,
                    chroma_manager=chroma_manager,
                    config=test_config['embedding_config']
                )
                
                # Step 1: Fetch data from Jira
                async with jira_connector:
                    issues = await jira_connector.fetch_data()
                    assert len(issues) == 1
                    assert issues[0]['key'] == 'TEST-123'
                
                # Step 2: Process and store data
                for issue in issues:
                    # Extract metadata
                    metadata = metadata_extractor.extract_jira_metadata(issue)
                    assert metadata['source'] == 'jira'
                    assert metadata['source_id'] == 'TEST-123'
                    
                    # Process content
                    description = metadata.get('description', '')
                    cleaned_text = text_processor.clean_html(description)
                    assert len(cleaned_text) > 0
                    
                    # Generate embedding
                    embedding = await embedding_service.embed_text(cleaned_text)
                    assert embedding.shape == (384,)
                    
                    # Store in database
                    doc_id = chroma_manager.add_document(
                        content=cleaned_text,
                        embedding=embedding,
                        metadata=metadata
                    )
                    assert doc_id is not None
                
                # Step 3: Search for similar content
                search_results = await query_interface.semantic_search(
                    query="NullPointerException authentication",
                    limit=5
                )
                
                assert len(search_results['results']) >= 1
                result = search_results['results'][0]
                assert result['metadata']['source_id'] == 'TEST-123'
                assert result['similarity'] > 0
    
    @pytest.mark.asyncio
    async def test_confluence_to_search_pipeline(self, test_config, sample_confluence_page):
        """Test complete pipeline from Confluence to search."""
        
        # Mock Confluence connector
        with patch('src.connectors.confluence_connector.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value.status = 200
            mock_session.return_value.__aenter__.return_value.request.return_value.__aenter__.return_value.json.return_value = {
                'results': [sample_confluence_page]
            }
            
            # Initialize components
            confluence_connector = ConfluenceConnector(test_config['confluence_config'])
            text_processor = TextProcessor()
            
            # Mock embedding service
            with patch('src.embeddings.embedding_service.SentenceTransformer') as mock_model:
                mock_model_instance = MagicMock()
                mock_model_instance.get_sentence_embedding_dimension.return_value = 384
                mock_model_instance.encode.return_value = [[0.1] * 384]
                mock_model.return_value = mock_model_instance
                
                embedding_service = EmbeddingService(test_config['embedding_config'])
                chroma_manager = ChromaManager(test_config['db_config'])
                query_interface = RAGQueryInterface(
                    embedding_service=embedding_service,
                    chroma_manager=chroma_manager,
                    config=test_config['embedding_config']
                )
                
                # Step 1: Fetch data from Confluence
                async with confluence_connector:
                    pages = await confluence_connector.fetch_data()
                    assert len(pages) == 1
                    assert pages[0]['id'] == '12345'
                
                # Step 2: Process and store data
                for page in pages:
                    # Extract metadata
                    metadata = confluence_connector.extract_page_metadata(page)
                    assert metadata['source'] == 'confluence'
                    assert metadata['source_id'] == '12345'
                    
                    # Process content
                    content = metadata.get('content', '')
                    cleaned_text = text_processor.clean_html(content)
                    assert 'Authentication Service' in cleaned_text
                    
                    # Generate embedding
                    embedding = await embedding_service.embed_text(cleaned_text)
                    assert embedding.shape == (384,)
                    
                    # Store in database
                    doc_id = chroma_manager.add_document(
                        content=cleaned_text,
                        embedding=embedding,
                        metadata=metadata
                    )
                    assert doc_id is not None
                
                # Step 3: Search for similar content
                search_results = await query_interface.semantic_search(
                    query="OAuth2 authentication documentation",
                    limit=5
                )
                
                assert len(search_results['results']) >= 1
                result = search_results['results'][0]
                assert result['metadata']['source_id'] == '12345'
                assert result['similarity'] > 0
    
    @pytest.mark.asyncio
    async def test_bug_similarity_search(self, test_config, sample_jira_issue):
        """Test bug similarity search functionality."""
        
        # Mock embedding service
        with patch('src.embeddings.embedding_service.SentenceTransformer') as mock_model:
            mock_model_instance = MagicMock()
            mock_model_instance.get_sentence_embedding_dimension.return_value = 384
            mock_model_instance.encode.return_value = [[0.1] * 384]
            mock_model.return_value = mock_model_instance
            
            # Initialize components
            embedding_service = EmbeddingService(test_config['embedding_config'])
            chroma_manager = ChromaManager(test_config['db_config'])
            query_interface = RAGQueryInterface(
                embedding_service=embedding_service,
                chroma_manager=chroma_manager,
                config=test_config['embedding_config']
            )
            
            # Store sample bug data
            metadata_extractor = MetadataExtractor()
            metadata = metadata_extractor.extract_jira_metadata(sample_jira_issue)
            
            doc_id = chroma_manager.add_document(
                content="NullPointerException in authentication service during OAuth2 login",
                embedding=[[0.1] * 384],
                metadata=metadata
            )
            
            # Perform bug similarity search
            error_message = "NullPointerException at AuthenticationService.java:42"
            stack_trace = """
            at com.example.AuthenticationService.authenticate(AuthenticationService.java:42)
            at com.example.SecurityFilter.doFilter(SecurityFilter.java:89)
            """
            
            results = await query_interface.find_similar_bugs(
                error_message=error_message,
                stack_trace=stack_trace,
                context={'project': 'TEST'},
                limit=5
            )
            
            assert len(results['results']) >= 1
            result = results['results'][0]
            assert result['metadata']['source_id'] == 'TEST-123'
            assert 'bug_score' in result
            assert result['bug_score'] >= 0
    
    @pytest.mark.asyncio
    async def test_attachment_processing(self, test_config):
        """Test attachment processing pipeline."""
        
        # Initialize attachment processor
        attachment_processor = AttachmentProcessor()
        
        # Test text file processing
        text_content = b"This is a test log file\nERROR: NullPointerException at line 42"
        result = attachment_processor.process_attachment(text_content, "test.log", "text/plain")
        
        assert result['type'] == 'text'
        assert result['filename'] == 'test.log'
        assert result['extracted_text'] == "This is a test log file\nERROR: NullPointerException at line 42"
        assert 'log_patterns' in result
        assert any('NullPointerException' in pattern for pattern in result['log_patterns'])
        
        # Test unsupported file type
        binary_data = b'\x00\x01\x02\x03\x04'
        result = attachment_processor.process_attachment(binary_data, "test.bin", "application/octet-stream")
        
        assert result['type'] == 'binary'
        assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_text_processing_features(self, test_config):
        """Test advanced text processing features."""
        
        text_processor = TextProcessor()
        
        # Test HTML cleaning
        html_content = """
        <h1>Test Page</h1>
        <p>This is a <strong>test</strong> paragraph.</p>
        <pre><code>def hello():
    print("Hello, World!")</code></pre>
        """
        
        cleaned = text_processor.clean_html(html_content)
        assert 'Test Page' in cleaned
        assert 'test paragraph' in cleaned
        assert 'def hello():' in cleaned
        
        # Test code block extraction
        code_blocks = text_processor.extract_code_blocks(html_content)
        assert len(code_blocks) == 1
        assert code_blocks[0]['language'] == 'text'  # Default language
        assert 'def hello():' in code_blocks[0]['code']
        
        # Test content chunking
        long_text = " ".join(["word"] * 200)  # 200 words
        chunks = text_processor.chunk_content(long_text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1
        assert all(len(chunk) <= 100 + 20 for chunk in chunks)  # Allow for overlap
    
    @pytest.mark.asyncio
    async def test_database_operations(self, test_config):
        """Test ChromaDB operations."""
        
        chroma_manager = ChromaManager(test_config['db_config'])
        
        # Test adding documents
        metadata = {
            'source': 'test',
            'source_id': 'TEST-001',
            'title': 'Test Document',
            'type': 'test'
        }
        
        doc_id = chroma_manager.add_document(
            content="This is a test document for database operations.",
            embedding=[[0.1] * 384],
            metadata=metadata
        )
        
        assert doc_id is not None
        
        # Test retrieving document
        retrieved = chroma_manager.get_document_by_id(doc_id)
        assert retrieved is not None
        assert retrieved['id'] == doc_id
        assert retrieved['metadata']['source_id'] == 'TEST-001'
        
        # Test updating document
        updated = chroma_manager.update_document(
            doc_id,
            content="Updated test document content.",
            metadata={**metadata, 'status': 'updated'}
        )
        assert updated is True
        
        # Test search
        results = chroma_manager.search(
            query_embedding=[[0.1] * 384],
            n_results=5
        )
        assert len(results['ids']) >= 1
        assert doc_id in results['ids']
        
        # Test deletion
        deleted = chroma_manager.delete_document(doc_id)
        assert deleted is True
        
        # Verify deletion
        retrieved_after_delete = chroma_manager.get_document_by_id(doc_id)
        assert retrieved_after_delete is None
    
    @pytest.mark.asyncio
    async def test_system_stats(self, test_config):
        """Test system statistics functionality."""
        
        # Mock embedding service
        with patch('src.embeddings.embedding_service.SentenceTransformer') as mock_model:
            mock_model_instance = MagicMock()
            mock_model_instance.get_sentence_embedding_dimension.return_value = 384
            mock_model_instance.encode.return_value = [[0.1] * 384]
            mock_model.return_value = mock_model_instance
            
            # Initialize components
            embedding_service = EmbeddingService(test_config['embedding_config'])
            chroma_manager = ChromaManager(test_config['db_config'])
            query_interface = RAGQueryInterface(
                embedding_service=embedding_service,
                chroma_manager=chroma_manager,
                config=test_config['embedding_config']
            )
            
            # Add some test data
            chroma_manager.add_document(
                content="Test document 1",
                embedding=[[0.1] * 384],
                metadata={'source': 'test', 'source_id': 'TEST-001'}
            )
            chroma_manager.add_document(
                content="Test document 2",
                embedding=[[0.2] * 384],
                metadata={'source': 'test', 'source_id': 'TEST-002'}
            )
            
            # Get system stats
            stats = await query_interface.get_system_stats()
            
            assert 'database' in stats
            assert 'embeddings' in stats
            assert 'search_config' in stats
            assert stats['database']['document_count'] >= 2
            assert stats['embeddings']['text_model'] is not None
            assert stats['embeddings']['embedding_dim'] == 384
