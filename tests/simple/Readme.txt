Simple Test Scripts for EVAgent Jira Integration
===============================================

This directory contains simple test scripts to debug and verify Jira integration.

Prerequisites:
--------------
1. Set environment variables:
   - JIRA_USERNAME="evilight@gmail.com"
   - JIRA_API_TOKEN="your_api_token_here"

2. Install dependencies:
   pip install -r requirements.txt

Test Scripts:
-------------

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

Running Tests:
--------------
From project root directory:
cd tests/simple
set JIRA_USERNAME=evilight@gmail.com
set JIRA_API_TOKEN=your_api_token_here
python test_config_simple.py
python test_auth.py
python test_projects.py
python test_api_formats.py

Or run all at once:
cd tests/simple
set JIRA_USERNAME=evilight@gmail.com
set JIRA_API_TOKEN=your_api_token_here
for %f in (test_*.py) do python %f

Troubleshooting:
---------------
- If you get Unicode errors, the scripts use plain text output
- If authentication fails, verify your API token is valid
- If projects don't load, check Jira permissions
- If API calls fail, verify network connectivity

Expected Results:
----------------
- test_config_simple.py: Should show successful config loading
- test_auth.py: Should show successful user authentication
- test_projects.py: Should list 1 project: SCRUM (EVAgent)
- test_api_formats.py: Should identify working API format

These scripts were used during development to debug the Jira integration
and are kept for future troubleshooting and testing.
