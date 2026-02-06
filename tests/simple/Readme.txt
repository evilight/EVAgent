Simple Test Scripts for EVAgent Integration
===========================================

This directory contains simple test scripts to debug and verify Jira and Confluence integration.

Prerequisites:
--------------
1. Set environment variables for Jira:
   - JIRA_USERNAME="evilight@gmail.com"
   - JIRA_API_TOKEN="your_api_token_here"

2. Set environment variables for Confluence (same as Jira):
   - CONFLUENCE_USERNAME="evilight@gmail.com"
   - CONFLUENCE_API_TOKEN="your_api_token_here"

3. Install dependencies:
   pip install -r requirements.txt

Test Scripts:
-------------

JIRA TESTS:

1. test_config_simple.py
   Purpose: Test configuration loading and environment variable substitution
   Run: python test_config_simple.py
   
   Steps:
   - Tests manual YAML environment variable substitution
   - Tests ConfigLoader class functionality
   - Verifies configuration file parsing

2. test_auth.py
   Purpose: Test Jira authentication and basic connection
   Run: python test_auth.py
   
   Steps:
   - Tests environment variable loading
   - Tests Basic Auth encoding
   - Tests Jira connection and user info retrieval

3. test_projects.py
   Purpose: Discover available Jira projects and test API endpoints
   Run: python test_projects.py
   
   Steps:
   - Lists all available projects in Jira instance
   - Tests old vs new search API endpoints
   - Tests different payload formats for new API

4. test_api_formats.py
   Purpose: Test different API request formats for Jira search
   Run: python test_api_formats.py
   
   Steps:
   - Tests various payload formats for /rest/api/3/search/jql
   - Compares old GET vs new POST API approaches
   - Identifies working request format

5. test_story_fields.py
   Purpose: List all fields of Jira stories/issues
   Run: python test_story_fields.py
   
   Steps:
   - Connects to Jira and searches for issues
   - Fetches detailed information for each issue
   - Displays all fields (top-level and nested)
   - Categorizes fields by type (basic, complex, empty)
   - Saves full details to story_fields_output.json

CONFLUENCE TESTS:

6. test_confluence_auth.py
   Purpose: Test Confluence authentication and connection
   Run: python test_confluence_auth.py
   
   Steps:
   - Tests Confluence configuration loading
   - Tests connection to Confluence API
   - Retrieves current user information
   Note: Requires Confluence to be enabled on your Atlassian account

7. test_confluence_pages.py
   Purpose: Fetch first 3 pages from Confluence
   Run: python test_confluence_pages.py
   
   Steps:
   - Lists available spaces
   - Fetches pages from the first space
   - Displays page details (ID, title, status, author)
   - Saves full details to confluence_pages_output.json
   Note: Requires Confluence to be enabled on your Atlassian account

8. test_confluence_discover.py
   Purpose: Discover available Confluence API endpoints
   Run: python test_confluence_discover.py
   
   Steps:
   - Tests multiple API endpoints
   - Identifies working endpoints
   - Helps troubleshoot connection issues

Running Tests:
--------------
From project root directory:

# Jira tests
cd tests/simple
set JIRA_USERNAME=evilight@gmail.com
set JIRA_API_TOKEN=your_api_token_here
python test_config_simple.py
python test_auth.py
python test_projects.py
python test_api_formats.py
python test_story_fields.py

# Confluence tests (same credentials as Jira)
set CONFLUENCE_USERNAME=evilight@gmail.com
set CONFLUENCE_API_TOKEN=your_api_token_here
python test_confluence_auth.py
python test_confluence_pages.py

Or run all tests at once:
cd tests/simple
set JIRA_USERNAME=evilight@gmail.com
set JIRA_API_TOKEN=your_api_token_here
set CONFLUENCE_USERNAME=evilight@gmail.com
set CONFLUENCE_API_TOKEN=your_api_token_here
for %f in (test_*.py) do python %f

Troubleshooting:
---------------
- If you get Unicode errors, the scripts use plain text output
- If authentication fails, verify your API token is valid
- If projects don't load, check Jira permissions
- If API calls fail, verify network connectivity
- For Confluence: Check CONFLUENCE_TEST_RESULTS.txt if tests fail

Expected Results:
----------------
- test_config_simple.py: Should show successful config loading
- test_auth.py: Should show successful user authentication
- test_projects.py: Should list 1 project: SCRUM (EVAgent)
- test_api_formats.py: Should identify working API format
- test_story_fields.py: Should list all fields of first 5 issues
- test_confluence_auth.py: Should connect and show user info (if Confluence enabled)
- test_confluence_pages.py: Should list 3 pages (if Confluence enabled)

Notes:
------
- CONFLUENCE_USERNAME and CONFLUENCE_API_TOKEN can be the same as JIRA credentials
- Confluence must be enabled on your Atlassian account for Confluence tests to work
- See CONFLUENCE_TEST_RESULTS.txt for details on Confluence availability

These scripts were used during development to debug the Jira and Confluence integration
and are kept for future troubleshooting and testing.
