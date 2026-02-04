# EVAgent RAG System

A comprehensive RAG (Retrieval-Augmented Generation) system for bug fix solutions and debugging with Jira and Confluence integration.

## Features

- **Jira Integration**: Fetch issues, comments, and attachments from Jira
- **Confluence Integration**: Access documentation pages and technical specs
- **Multi-modal Processing**: Handle text, images, PDFs, Word docs, Excel files, and logs
- **Advanced Semantic Search**: Find similar bugs and solutions using vector embeddings
- **RAG Pipeline**: Complete retrieval-augmented generation system
- **REST API**: FastAPI-based search API with comprehensive endpoints
- **CLI Tools**: Command-line interface for easy system management
- **Rate Limiting**: Intelligent API rate limiting with backoff strategies
- **Incremental Sync**: Efficient data synchronization with timestamp tracking

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/evilight/EVAgent.git
cd EVAgent

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

1. **Jira Setup**:
   ```yaml
   # config/jira_config.yaml
   jira:
     url: "https://your-company.atlassian.net"
     username: "${JIRA_USERNAME}"
     api_token: "${JIRA_API_TOKEN}"
     projects: ["PROJ1", "PROJ2"]
   ```

2. **Environment Variables**:
   ```bash
   export JIRA_USERNAME=your-email@company.com
   export JIRA_API_TOKEN=your-api-token
   ```

### Usage

#### Command Line Interface

```bash
# Check system status
evagent status

# Sync data from Jira and Confluence
evagent sync --source all --limit 100

# Search for documents
evagent search "NullPointerException authentication" --limit 5

# Find similar bugs
evagent find-bugs "NullPointerException at AuthenticationService.java:42" --project AUTH

# Start the API server
evagent serve --host 0.0.0.0 --port 8000
```

#### Python API

```python
from src.connectors import JiraConnector, ConfluenceConnector
from src.utils import ConfigLoader
from src.api import RAGQueryInterface

# Load configuration
config_loader = ConfigLoader()
jira_config = config_loader.get_jira_config()

# Create connector
async with JiraConnector(jira_config) as jira:
    # Search issues
    issues = await jira.search_issues("project = AUTH AND type = Bug")
    
    # Get issue details with comments and attachments
    for issue in issues['issues']:
        details = await jira.get_issue_details(issue['key'])
        comments = await jira.get_issue_comments(issue['key'])
        # Process data...

# Semantic search
query_interface = RAGQueryInterface(...)
results = await query_interface.semantic_search(
    query="OAuth2 authentication error",
    limit=10
)
```

#### REST API

```bash
# Start the server
evagent serve

# Search documents
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "NullPointerException authentication", "limit": 5}'

# Find similar bugs
curl -X POST "http://localhost:8000/search/bugs" \
  -H "Content-Type: application/json" \
  -d '{"error_message": "NullPointerException", "stack_trace": "..."}'

# Get system stats
curl "http://localhost:8000/stats"
```

## Project Structure

```
EVAgent/
├── src/
│   ├── connectors/          # Data source connectors
│   │   ├── base_connector.py
│   │   ├── jira_connector.py
│   │   └── confluence_connector.py
│   ├── processors/          # Data processing modules
│   │   ├── text_processor.py
│   │   ├── attachment_processor.py
│   │   └── metadata_extractor.py
│   ├── embeddings/          # Vector embeddings
│   │   └── embedding_service.py
│   ├── database/           # Vector database management
│   │   ├── chroma_manager.py
│   │   └── schema.py
│   ├── utils/              # Utilities (config, logging, etc.)
│   │   ├── config_loader.py
│   │   ├── logger.py
│   │   └── rate_limiter.py
│   ├── api/                # API interfaces
│   │   ├── query_interface.py
│   │   └── search_api.py
│   └── cli.py              # Command-line interface
├── config/                 # Configuration files
│   ├── jira_config.yaml
│   ├── confluence_config.yaml
│   └── embedding_config.yaml
├── storage/               # Data storage
├── tests/                 # Test suite
├── example_usage.py       # Usage examples
└── requirements.txt       # Dependencies
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run with coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/
```

## API Reference

### JiraConnector

The main class for interacting with Jira API.

#### Methods

- `search_issues(jql, start_at=0, max_results=50)`: Search issues using JQL
- `get_issue_details(issue_key)`: Get detailed issue information
- `get_issue_comments(issue_key)`: Retrieve all comments for an issue
- `get_updated_issues(since, projects=None)`: Get issues updated since timestamp
- `download_attachment(attachment_url)`: Download attachment content

### Configuration

All configuration is managed through YAML files in the `config/` directory with environment variable substitution support.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support, please open an issue in the repository.
