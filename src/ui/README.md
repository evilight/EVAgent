# EVAgent RAG Chat UI

A web-based chat interface for querying the EVAgent RAG system.

## Features

- Real-time chat interface
- Source attribution for answers
- Conversation history
- Clean, responsive design
- Integration with existing RAG pipeline

## Setup

1. Install dependencies:
```bash
cd src/ui
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export OPENAI_API_KEY=your-api-key-here
```

3. Run the chat UI:
```bash
python chat_ui.py
```

4. Open browser to: http://localhost:5000

## Usage

- Type your questions about bugs, setup, or project issues
- The system will retrieve relevant documents and generate answers
- Sources are shown below each response
- Conversation history is maintained during the session

## Architecture

- **Flask**: Web server and API endpoints
- **RAGChain**: Core question-answering logic
- **ChromaDB**: Vector storage and retrieval
- **MockEmbeddingService**: For testing without model downloads

## API Endpoints

- `GET /`: Chat interface
- `POST /api/init`: Initialize RAG system
- `POST /api/chat`: Send message and get response
- `POST /api/clear`: Clear conversation history
- `GET /api/status`: Get system status
