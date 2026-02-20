"""
Jira connector for fetching issues, comments, and attachments.
"""

import os
import sys
import asyncio
import base64
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from urllib.parse import urljoin

# Add EVAgent src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base_connector import BaseConnector
from utils.rate_limiter import JiraRateLimiter


class JiraConnector(BaseConnector):
    """
    Connector for Jira API to fetch issues, comments, and attachments.
    
    Supports Jira Cloud and Jira Server with proper authentication and rate limiting.
    """
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """
        Initialize Jira connector.
        
        Args:
            config: Jira configuration dictionary
            logger: Logger instance (optional)
        """
        super().__init__(config, logger)
        self.base_url = config['url'].rstrip('/')
        self.username = config['username']
        self.api_token = config['api_token']
        self.api_version = config.get('api', {}).get('version', '3')
        
        # Use specialized Jira rate limiter
        self.rate_limiter = JiraRateLimiter()
        
        # Authentication header
        auth_string = f"{self.username}:{self.api_token}"
        self.auth_header = base64.b64encode(auth_string.encode()).decode()
    
    def _get_default_headers(self) -> Dict[str, str]:
        """
        Get default HTTP headers for Jira API requests.
        
        Returns:
            Dictionary of default headers
        """
        return {
            'Authorization': f'Basic {self.auth_header}',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'EVAgent-RAG/1.0'
        }
    
    async def _test_connection(self) -> None:
        """
        Test connection to Jira API.
        
        Raises:
            Exception: If connection test fails
        """
        url = f"{self.base_url}/rest/api/{self.api_version}/myself"
        
        # Make a direct request without using _make_request to avoid circular dependency
        try:
            headers = self._get_default_headers()
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    self.logger.info("Jira connection test successful")
                else:
                    error_text = await response.text()
                    raise Exception(f"Connection test failed with status {response.status}: {error_text}")
        except Exception as e:
            raise Exception(f"Jira connection test failed: {e}")
    
    async def search_issues(
        self,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
        fields: Optional[List[str]] = None,
        expand: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search issues using JQL (Jira Query Language).
        
        Args:
            jql: JQL query string
            start_at: Starting index for pagination
            max_results: Maximum number of results to return
            fields: List of fields to include in response
            expand: List of fields to expand
            
        Returns:
            Dictionary containing search results
        """
        # Use the new JQL search endpoint
        url = f"{self.base_url}/rest/api/{self.api_version}/search/jql"
        
        # Build minimal payload for the new API (it doesn't accept all parameters)
        payload = {'jql': jql}
        
        # Only add maxResults if specified (API might not support other params)
        if max_results != 50:  # Only add if not default
            payload['maxResults'] = max_results
        
        self.logger.info(f"Searching issues with JQL: {jql}")
        return await self._make_request('POST', url, data=payload)
    
    async def get_issue_details(self, issue_key: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific issue.
        
        Args:
            issue_key: Issue key (e.g., 'PROJ-123')
            fields: List of fields to include
            
        Returns:
            Issue details dictionary
        """
        url = f"{self.base_url}/rest/api/{self.api_version}/issue/{issue_key}"
        
        params = {}
        if fields:
            params['fields'] = ','.join(fields)
        
        self.logger.debug(f"Getting issue details for {issue_key}")
        return await self._make_request('GET', url, params=params)
    
    async def get_issue_comments(self, issue_key: str) -> List[Dict[str, Any]]:
        """
        Get all comments for an issue.
        
        Args:
            issue_key: Issue key
            
        Returns:
            List of comment dictionaries
        """
        url = f"{self.base_url}/rest/api/{self.api_version}/issue/{issue_key}/comment"
        
        params = {
            'orderBy': 'created',
            'expand': 'renderedBody'
        }
        
        self.logger.debug(f"Getting comments for {issue_key}")
        response = await self._make_request('GET', url, params=params)
        return response.get('comments', [])
    
    async def get_attachment_metadata(self, attachment_id: str) -> Dict[str, Any]:
        """
        Get metadata for an attachment.
        
        Args:
            attachment_id: Attachment ID
            
        Returns:
            Attachment metadata dictionary
        """
        url = f"{self.base_url}/rest/api/{self.api_version}/attachment/{attachment_id}"
        
        self.logger.debug(f"Getting attachment metadata for {attachment_id}")
        return await self._make_request('GET', url)
    
    async def download_attachment(self, attachment_url: str) -> bytes:
        """
        Download attachment content.
        
        Args:
            attachment_url: URL to the attachment
            
        Returns:
            Attachment content as bytes
        """
        # Use a separate session without JSON content type for binary downloads
        headers = {
            'Authorization': f'Basic {self.auth_header}',
            'User-Agent': 'EVAgent-RAG/1.0'
        }
        
        await self.rate_limiter.acquire('jira')
        
        async with self.session.get(attachment_url, headers=headers) as response:
            if response.status == 200:
                return await response.read()
            else:
                raise Exception(f"Failed to download attachment: {response.status}")
    
    async def get_updated_issues(
        self,
        since: datetime,
        projects: Optional[List[str]] = None,
        issue_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get issues updated since a specific timestamp.
        
        Args:
            since: DateTime to fetch updates since
            projects: List of project keys to filter by
            issue_types: List of issue types to filter by
            
        Returns:
            List of updated issues
        """
        # Build JQL query
        jql_parts = [f"updated >= '{since.strftime('%Y-%m-%d %H:%M')}'"]
        
        if projects:
            project_filter = " OR ".join([f"project = {p}" for p in projects])
            jql_parts.append(f"({project_filter})")
        
        if issue_types:
            type_filter = " OR ".join([f'issuetype = "{t}"' for t in issue_types])
            jql_parts.append(f"({type_filter})")
        
        jql = " AND ".join(jql_parts)
        
        # Fetch all updated issues (handle pagination)
        all_issues = []
        start_at = 0
        batch_size = self.config.get('sync', {}).get('batch_size', 50)
        
        while True:
            response = await self.search_issues(
                jql=jql,
                start_at=start_at,
                max_results=batch_size,
                fields=['*all']
            )
            
            issues = response.get('issues', [])
            all_issues.extend(issues)
            
            # Check if we have all issues
            total = response.get('total', 0)
            if start_at + len(issues) >= total:
                break
            
            start_at += len(issues)
        
        self.logger.info(f"Found {len(all_issues)} issues updated since {since}")
        return all_issues
    
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch data from Jira based on configuration.
        
        Args:
            **kwargs: Additional parameters (projects, jql_filters, etc.)
            
        Returns:
            List of issues with comments and attachments
        """
        projects = kwargs.get('projects', self.config.get('projects', []))
        jql_filters = kwargs.get('jql_filters', self.config.get('jql_filters', []))
        
        all_issues = []
        
        for jql in jql_filters:
            # Add project filter if specified
            if projects:
                project_filter = " OR ".join([f"project = {p}" for p in projects])
                jql = f"({project_filter}) AND {jql}"
            
            # Fetch issues
            response = await self.search_issues(jql=jql, max_results=100)
            issues = response.get('issues', [])
            
            # Enrich issues with comments and attachments
            for issue in issues:
                issue_key = issue['key']
                
                # Add comments
                try:
                    comments = await self.get_issue_comments(issue_key)
                    issue['comments'] = comments
                except Exception as e:
                    self.logger.warning(f"Failed to get comments for {issue_key}: {e}")
                    issue['comments'] = []
                
                # Add attachment metadata
                attachments = issue.get('fields', {}).get('attachment', [])
                enriched_attachments = []
                
                for attachment in attachments:
                    try:
                        metadata = await self.get_attachment_metadata(attachment['id'])
                        enriched_attachments.append(metadata)
                    except Exception as e:
                        self.logger.warning(f"Failed to get attachment metadata for {attachment['id']}: {e}")
                        enriched_attachments.append(attachment)
                
                issue['attachments'] = enriched_attachments
            
            all_issues.extend(issues)
        
        self.logger.info(f"Fetched {len(all_issues)} issues from Jira")
        return all_issues
    
    def extract_issue_metadata(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured metadata from an issue.
        
        Args:
            issue: Issue dictionary from Jira API
            
        Returns:
            Structured metadata dictionary
        """
        fields = issue.get('fields', {})
        
        return {
            'source': 'jira',
            'source_id': issue['key'],
            'title': fields.get('summary', ''),
            'description': fields.get('description', ''),
            'type': fields.get('issuetype', {}).get('name', ''),
            'status': fields.get('status', {}).get('name', ''),
            'priority': fields.get('priority', {}).get('name', ''),
            'project': fields.get('project', {}).get('key', ''),
            'project_name': fields.get('project', {}).get('name', ''),
            'assignee': fields.get('assignee', {}).get('displayName', ''),
            'reporter': fields.get('reporter', {}).get('displayName', ''),
            'created_date': fields.get('created', ''),
            'updated_date': fields.get('updated', ''),
            'resolution_date': fields.get('resolutiondate', ''),
            'labels': fields.get('labels', []),
            'components': [c.get('name', '') for c in fields.get('components', [])],
            'fix_versions': [v.get('name', '') for v in fields.get('fixVersions', [])],
            'attachments': [att.get('filename', '') for att in issue.get('attachments', [])],
            'comment_count': len(issue.get('comments', [])),
            'url': f"{self.base_url}/browse/{issue['key']}"
        }
