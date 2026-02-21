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
    
    async def _test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Jira API.
        
        Returns:
            Dictionary with connection status and message
        """
        url = f"{self.base_url}/rest/api/{self.api_version}/myself"
        
        # Make a direct request without using _make_request to avoid circular dependency
        try:
            headers = self._get_default_headers()
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    self.logger.info("Jira connection test successful")
                    try:
                        user_data = await response.json()
                        return {
                            "status": "success",
                            "message": "Connected to Jira successfully",
                            "user": user_data
                        }
                    except Exception as json_error:
                        return {
                            "status": "success",
                            "message": "Connected to Jira successfully",
                            "user": None
                        }
                else:
                    error_text = await response.text()
                    raise Exception(f"Connection test failed with status {response.status}: {error_text}")
        except Exception as e:
            raise Exception(f"Jira connection test failed: {e}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Public method to test connection.
        
        Returns:
            Dictionary with connection status and message
        """
        try:
            return await self._test_connection()
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
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
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """
        Retrieve all projects from Jira.
        
        Returns:
            List of project dictionaries
        """
        try:
            await self.rate_limiter.wait_if_needed()
            
            url = f"{self.base_url.rstrip('/')}/rest/api/2/project"
            params = {
                'expand': 'description,lead,issueTypes'
            }
            
            response = await self.session.get(url, params=params)
            
            if response.status_code == 200:
                projects = response.json()
                self.logger.info(f"Retrieved {len(projects)} projects from Jira")
                
                return [{
                    'id': project.get('id'),
                    'key': project.get('key'),
                    'name': project.get('name'),
                    'description': project.get('description', ''),
                    'url': f"{self.base_url}/browse/{project.get('key')}",
                    'lead': project.get('lead', {}).get('name', ''),
                    'type': project.get('projectTypeKey', ''),
                    'category': project.get('projectCategory', {}).get('name', ''),
                    'components': self._extract_components(project.get('components', []))
                } for project in projects]
            else:
                self.logger.error(f"Failed to retrieve projects: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error retrieving projects: {e}")
            return []
    
    async def get_issues(self, project_key: str = None, limit: int = 50, 
                   jql: str = None, status: str = None, 
                   priority: str = None, assignee: str = None) -> List[Dict[str, Any]]:
        """
        Retrieve issues from Jira with advanced filtering options.
        
        Args:
            project_key: Filter by specific project (optional)
            limit: Maximum number of issues to retrieve
            jql: JQL query string for custom filtering (optional)
            status: Filter by issue status (optional)
            priority: Filter by priority (optional)
            assignee: Filter by assignee (optional)
        
        Returns:
            List of issue dictionaries
        """
        try:
            await self.rate_limiter.wait_if_needed()
            
            url = f"{self.base_url.rstrip('/')}/rest/api/2/search"
            
            # Build JQL query
            jql_parts = []
            
            if jql:
                jql_parts.append(jql)
            
            if project_key:
                jql_parts.append(f"project = {project_key}")
            
            if status:
                jql_parts.append(f"status = '{status}'")
            
            if priority:
                jql_parts.append(f"priority = {priority}")
            
            if assignee:
                jql_parts.append(f"assignee = '{assignee}'")
            
            query = " AND ".join(jql_parts) if jql_parts else ""
            
            params = {
                'jql': query,
                'fields': 'summary,description,status,created,updated,priority,issuetype,reporter,assignee,labels,fixVersions',
                'expand': 'renderedFields,transitions,comments,worklog,attachment',
                'maxResults': limit
            }
            
            response = await self.session.get(url, params=params)
            
            if response.status_code == 200:
                issues_data = response.json()
                issues = issues_data.get('issues', [])
                
                self.logger.info(f"Retrieved {len(issues)} issues from Jira")
                
                return [{
                    'id': issue.get('id'),
                    'key': issue.get('key'),
                    'summary': issue.get('fields', {}).get('summary', ''),
                    'description': issue.get('fields', {}).get('description', ''),
                    'status': issue.get('fields', {}).get('status', {}).get('name', ''),
                    'priority': issue.get('fields', {}).get('priority', {}).get('name', ''),
                    'created': issue.get('fields', {}).get('created', ''),
                    'updated': issue.get('fields', {}).get('updated', ''),
                    'reporter': issue.get('fields', {}).get('reporter', {}).get('displayName', ''),
                    'assignee': issue.get('fields', {}).get('assignee', {}).get('displayName', ''),
                    'labels': [label.get('displayName', '') for label in issue.get('fields', {}).get('labels', [])],
                    'issue_type': issue.get('fields', {}).get('issuetype', {}).get('name', ''),
                    'components': self._extract_components(issue.get('fields', {}).get('components', [])),
                    'attachments': self._extract_attachments(issue.get('fields', {}).get('attachment', [])),
                    'comments': await self._extract_comments_async(issue.get('fields', {}).get('comment', {})),
                    'worklog': await self._extract_worklog_async(issue.get('fields', {}).get('worklog', {})),
                    'url': f"{self.base_url}/browse/{issue.get('key')}",
                    'project': issue.get('fields', {}).get('project', {}).get('key', '')
                } for issue in issues]
            else:
                self.logger.error(f"Failed to retrieve issues: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error retrieving issues: {e}")
            return []
    
    async def get_issue_details(self, issue_key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve detailed information for a specific issue.
        
        Args:
            issue_key: Jira issue key (e.g., PROJ-123)
        
        Returns:
            Issue details dictionary or None if not found
        """
        try:
            await self.rate_limiter.wait_if_needed()
            
            url = f"{self.base_url.rstrip('/')}/rest/api/2/issue/{issue_key}"
            params = {
                'expand': 'renderedFields,comments,worklog,transitions,attachment'
            }
            
            response = await self.session.get(url, params=params)
            
            if response.status_code == 200:
                issue = response.json()
                self.logger.info(f"Retrieved details for issue {issue_key}")
                
                return {
                    'id': issue.get('id'),
                    'key': issue.get('key'),
                    'summary': issue.get('fields', {}).get('summary', ''),
                    'description': issue.get('fields', {}).get('description', ''),
                    'status': issue.get('fields', {}).get('status', {}).get('name', ''),
                    'priority': issue.get('fields', {}).get('priority', {}).get('name', ''),
                    'created': issue.get('fields', {}).get('created', ''),
                    'updated': issue.get('fields', {}).get('updated', ''),
                    'reporter': issue.get('fields', {}).get('reporter', {}).get('displayName', ''),
                    'assignee': issue.get('fields', {}).get('assignee', {}).get('displayName', ''),
                    'labels': [label.get('displayName', '') for label in issue.get('fields', {}).get('labels', [])],
                    'issue_type': issue.get('fields', {}).get('issuetype', {}).get('name', ''),
                    'components': self._extract_components(issue.get('fields', {}).get('components', [])),
                    'attachments': await self._extract_attachments_async(issue.get('fields', {}).get('attachment', [])),
                    'comments': await self._extract_comments_async(issue.get('fields', {}).get('comment', {})),
                    'worklog': await self._extract_worklog_async(issue.get('fields', {}).get('worklog', {})),
                    'transitions': self._extract_transitions(issue.get('fields', {}).get('transitions', {})),
                    'url': f"{self.base_url}/browse/{issue_key}"
                }
            else:
                self.logger.error(f"Failed to retrieve issue {issue_key}: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving issue {issue_key}: {e}")
            return None
    
    def _extract_components(self, components_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract component information from Jira components data."""
        components = []
        
        if isinstance(components_data, list):
            for component in components_data:
                if isinstance(component, dict):
                    components.append({
                        'id': component.get('id'),
                        'name': component.get('name', ''),
                        'description': component.get('description', '')
                    })
        
        return components
    
    async def _extract_attachments_async(self, attachments_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract attachment information from Jira attachments data."""
        attachments = []
        
        if isinstance(attachments_data, list):
            for attachment in attachments_data:
                if isinstance(attachment, dict):
                    attachments.append({
                        'id': attachment.get('id'),
                        'filename': attachment.get('filename', ''),
                        'mimetype': attachment.get('mimeType', ''),
                        'size': attachment.get('size', 0),
                        'url': f"{self.base_url}/secure/attachment/{attachment.get('id')}/{attachment.get('token')}" if attachment.get('token') else f"{self.base_url}/browse/{attachment.get('id')}",
                        'created': attachment.get('created', '')
                    })
        
        return attachments
    
    async def _extract_comments_async(self, comments_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract comments from Jira comment data."""
        comments = []
        
        if isinstance(comments_data, dict) and 'comments' in comments_data:
            for comment in comments_data['comments']:
                if comment.get('author'):
                    comments.append({
                        'id': comment.get('id'),
                        'author': comment['author'].get('displayName', ''),
                        'body': comment.get('body', ''),
                        'created': comment.get('created', ''),
                        'updated': comment.get('updated', ''),
                        'visibility': comment.get('visibility', ''),
                        'renderedBody': comment.get('renderedBody', ''),
                        'updates': self._extract_comment_updates(comment.get('updateAuthor', []))
                    })
        
        return comments
    
    def _extract_worklog_async(self, worklog_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract work log entries from Jira worklog data."""
        worklogs = []
        
        if isinstance(worklog_data, dict) and 'worklogs' in worklog_data:
            for worklog in worklog_data['worklogs']:
                if worklog.get('author'):
                    worklogs.append({
                        'id': worklog.get('id'),
                        'author': worklog['author'].get('displayName', ''),
                        'timeSpent': worklog.get('timeSpent', ''),
                        'timeSpentSeconds': worklog.get('timeSpentSeconds', 0),
                        'started': worklog.get('started', ''),
                        'comment': worklog.get('comment', ''),
                        'created': worklog.get('created', '')
                    })
        
        return worklogs
    
    def _extract_transitions(self, transitions_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract workflow transitions from Jira transitions data."""
        transitions = []
        
        if isinstance(transitions_data, dict):
            for transition in transitions_data.get('transitions', []):
                transitions.append({
                    'id': transition.get('id'),
                    'name': transition.get('name', ''),
                    'to': transition.get('to', {}).get('name', ''),
                    'from': transition.get('from', {}).get('name', '')
                })
        
        return transitions
    
    def _extract_comment_updates(self, updates_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract comment update history."""
        updates = []
        
        if isinstance(updates_data, list):
            for update in updates_data:
                if isinstance(update, dict):
                    updates.append({
                        'author': update.get('author', {}).get('displayName', ''),
                        'updated': update.get('updated', ''),
                        'renderedBody': update.get('renderedBody', '')
                    })
        
        return updates
    
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
