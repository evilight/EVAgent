"""
Unit tests for Jira connector.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.connectors.jira_connector import JiraConnector


class TestJiraConnector:
    """Test cases for JiraConnector class."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return {
            'url': 'https://test.atlassian.net',
            'username': 'test@example.com',
            'api_token': 'test-token',
            'api': {'version': '3'},
            'timeout': 30
        }
    
    @pytest.fixture
    def jira_connector(self, config):
        """Create Jira connector instance."""
        return JiraConnector(config)
    
    @pytest.fixture
    def sample_issue_response(self):
        """Sample Jira issue response."""
        return {
            'id': '10001',
            'key': 'TEST-123',
            'fields': {
                'summary': 'Test issue summary',
                'description': 'Test issue description',
                'issuetype': {'name': 'Bug'},
                'status': {'name': 'Open'},
                'priority': {'name': 'High'},
                'project': {'key': 'TEST', 'name': 'Test Project'},
                'assignee': {'displayName': 'John Doe'},
                'reporter': {'displayName': 'Jane Smith'},
                'created': '2024-01-01T10:00:00.000Z',
                'updated': '2024-01-02T15:30:00.000Z',
                'labels': ['bug', 'urgent'],
                'components': [{'name': 'UI'}, {'name': 'API'}],
                'fixVersions': [{'name': 'v1.0'}],
                'attachment': [{'id': 'att001', 'filename': 'screenshot.png'}]
            }
        }
    
    @pytest.fixture
    def sample_search_response(self, sample_issue_response):
        """Sample Jira search response."""
        return {
            'startAt': 0,
            'maxResults': 50,
            'total': 1,
            'issues': [sample_issue_response]
        }
    
    def test_init(self, config):
        """Test connector initialization."""
        connector = JiraConnector(config)
        
        assert connector.base_url == 'https://test.atlassian.net'
        assert connector.username == 'test@example.com'
        assert connector.api_token == 'test-token'
        assert connector.api_version == '3'
        assert not connector._is_connected
    
    def test_get_default_headers(self, jira_connector):
        """Test default headers generation."""
        headers = jira_connector._get_default_headers()
        
        assert 'Authorization' in headers
        assert headers['Accept'] == 'application/json'
        assert headers['Content-Type'] == 'application/json'
        assert 'User-Agent' in headers
    
    @pytest.mark.asyncio
    async def test_connect(self, jira_connector):
        """Test connection establishment."""
        with patch.object(jira_connector, '_make_request') as mock_request:
            mock_request.return_value = {'displayName': 'Test User'}
            
            await jira_connector.connect()
            
            assert jira_connector._is_connected
            assert jira_connector.session is not None
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_issues(self, jira_connector, sample_search_response):
        """Test issue search functionality."""
        jira_connector._is_connected = True
        jira_connector.session = AsyncMock()
        
        with patch.object(jira_connector, '_make_request') as mock_request:
            mock_request.return_value = sample_search_response
            
            result = await jira_connector.search_issues(
                jql="project = TEST",
                start_at=0,
                max_results=50
            )
            
            assert result == sample_search_response
            mock_request.assert_called_once()
            
            # Check call arguments
            call_args = mock_request.call_args
            assert call_args[0][0] == 'GET'  # method
            assert 'search' in call_args[0][1]  # URL contains 'search'
            assert call_args[1]['params']['jql'] == "project = TEST"
            assert call_args[1]['params']['startAt'] == 0
            assert call_args[1]['params']['maxResults'] == 50
    
    @pytest.mark.asyncio
    async def test_get_issue_details(self, jira_connector, sample_issue_response):
        """Test getting issue details."""
        jira_connector._is_connected = True
        jira_connector.session = AsyncMock()
        
        with patch.object(jira_connector, '_make_request') as mock_request:
            mock_request.return_value = sample_issue_response
            
            result = await jira_connector.get_issue_details('TEST-123')
            
            assert result == sample_issue_response
            mock_request.assert_called_once()
            
            call_args = mock_request.call_args
            assert call_args[0][0] == 'GET'
            assert 'TEST-123' in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_get_issue_comments(self, jira_connector):
        """Test getting issue comments."""
        jira_connector._is_connected = True
        jira_connector.session = AsyncMock()
        
        sample_comments = {
            'comments': [
                {
                    'id': '10010',
                    'author': {'displayName': 'John Doe'},
                    'body': 'Test comment',
                    'created': '2024-01-01T11:00:00.000Z'
                }
            ]
        }
        
        with patch.object(jira_connector, '_make_request') as mock_request:
            mock_request.return_value = sample_comments
            
            result = await jira_connector.get_issue_comments('TEST-123')
            
            assert result == sample_comments['comments']
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_updated_issues(self, jira_connector):
        """Test getting updated issues."""
        jira_connector._is_connected = True
        jira_connector.session = AsyncMock()
        
        sample_search_response = {
            'startAt': 0,
            'maxResults': 50,
            'total': 1,
            'issues': [{'key': 'TEST-123', 'fields': {}}]
        }
        
        with patch.object(jira_connector, 'search_issues') as mock_search:
            mock_search.return_value = sample_search_response
            
            since = datetime(2024, 1, 1, tzinfo=timezone.utc)
            result = await jira_connector.get_updated_issues(
                since=since,
                projects=['TEST'],
                issue_types=['Bug']
            )
            
            assert len(result) == 1
            assert result[0]['key'] == 'TEST-123'
            mock_search.assert_called_once()
            
            # Check JQL construction
            call_args = mock_search.call_args
            jql = call_args[1]['jql']
            assert 'updated >= 2024-01-01 00:00' in jql
            assert 'project = TEST' in jql
            assert 'issuetype = "Bug"' in jql
    
    def test_extract_issue_metadata(self, jira_connector, sample_issue_response):
        """Test metadata extraction from issue."""
        metadata = jira_connector.extract_issue_metadata(sample_issue_response)
        
        assert metadata['source'] == 'jira'
        assert metadata['source_id'] == 'TEST-123'
        assert metadata['title'] == 'Test issue summary'
        assert metadata['type'] == 'Bug'
        assert metadata['status'] == 'Open'
        assert metadata['priority'] == 'High'
        assert metadata['project'] == 'TEST'
        assert metadata['project_name'] == 'Test Project'
        assert metadata['assignee'] == 'John Doe'
        assert metadata['reporter'] == 'Jane Smith'
        assert metadata['labels'] == ['bug', 'urgent']
        assert metadata['components'] == ['UI', 'API']
        assert metadata['fix_versions'] == ['v1.0']
        assert metadata['attachments'] == ['screenshot.png']
        assert metadata['comment_count'] == 0
        assert 'TEST-123' in metadata['url']
    
    @pytest.mark.asyncio
    async def test_download_attachment(self, jira_connector):
        """Test attachment download."""
        jira_connector._is_connected = True
        jira_connector.session = AsyncMock()
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = b'fake image data'
        
        jira_connector.session.get.return_value.__aenter__.return_value = mock_response
        
        with patch.object(jira_connector.rate_limiter, 'acquire') as mock_rate_limit:
            mock_rate_limit.return_value = None
            
            result = await jira_connector.download_attachment('https://test.com/attachment.png')
            
            assert result == b'fake image data'
            mock_rate_limit.assert_called_once_with('jira')
    
    @pytest.mark.asyncio
    async def test_fetch_data(self, jira_connector):
        """Test the main fetch_data method."""
        jira_connector._is_connected = True
        jira_connector.session = AsyncMock()
        
        sample_issue = {
            'key': 'TEST-123',
            'fields': {'attachment': []},
            'comments': [],
            'attachments': []
        }
        
        with patch.object(jira_connector, 'search_issues') as mock_search, \
             patch.object(jira_connector, 'get_issue_comments') as mock_comments, \
             patch.object(jira_connector, 'get_attachment_metadata') as mock_attachments:
            
            mock_search.return_value = {'issues': [sample_issue]}
            mock_comments.return_value = []
            mock_attachments.return_value = []
            
            result = await jira_connector.fetch_data(
                projects=['TEST'],
                jql_filters=['status = Open']
            )
            
            assert len(result) == 1
            assert result[0]['key'] == 'TEST-123'
            mock_search.assert_called_once()
            mock_comments.assert_called_once_with('TEST-123')
    
    @pytest.mark.asyncio
    async def test_context_manager(self, jira_connector):
        """Test async context manager functionality."""
        with patch.object(jira_connector, 'connect') as mock_connect, \
             patch.object(jira_connector, 'disconnect') as mock_disconnect:
            
            async with jira_connector:
                pass
            
            mock_connect.assert_called_once()
            mock_disconnect.assert_called_once()
