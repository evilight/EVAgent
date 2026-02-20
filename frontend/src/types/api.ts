export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserInfo {
  username: string;
  roles: string[];
}

export interface AuthContextType {
  user: string | null;
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: SourceDocument[];
}

export interface SourceDocument {
  id: string;
  title: string;
  content: string;
  score: number;
  metadata: Record<string, any>;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  filters?: Record<string, any>;
}

export interface ChatResponse {
  answer: string;
  sources: SourceDocument[];
  conversation_id?: string;
  timestamp?: string;
  user_context?: Record<string, any>;
}

export interface SearchRequest {
  query: string;
  filters?: Record<string, any>;
  limit?: number;
  similarity_threshold?: number;
  include_content?: boolean;
}

export interface SearchResult {
  id: string;
  title: string;
  content: string;
  score: number;
  metadata: Record<string, any>;
  source: string;
  created_at?: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  username: string;
  timestamp?: string;
}

export interface SystemStats {
  total_documents: number;
  total_conversations: number;
  total_searches: number;
  uptime: number;
  memory_usage?: Record<string, any>;
  model_info: Record<string, any>;
}
