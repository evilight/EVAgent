import axios, { AxiosResponse } from 'axios';
import { LoginResponse, ChatRequest, ChatResponse, SearchRequest, SearchResponse } from '../types/api';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

class APIService {
  private token: string | null = null;
  
  constructor() {
    this.token = localStorage.getItem('token');
  }
  
  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    return headers;
  }
  
  async login(username: string, password: string): Promise<LoginResponse> {
    try {
      const response = await axios.post<LoginResponse>(
        `${API_BASE_URL}/auth/login`,
        {},
        {
          headers: {
            'Authorization': `Basic ${btoa(`${username}:${password}`)}`
          }
        }
      );
      
      if (response.data.access_token) {
        this.token = response.data.access_token;
        localStorage.setItem('token', this.token);
      }
      
      return response.data;
    } catch (error: any) {
      console.error('Login error:', error);
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  }
  
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await axios.post<ChatResponse>(
        `${API_BASE_URL}/chat/`,
        request,
        {
          headers: this.getHeaders()
        }
      );
      
      if (response.status === 401) {
        this.logout();
        throw new Error('Authentication required');
      }
      
      return response.data;
    } catch (error: any) {
      console.error('Send message error:', error);
      if (error.response?.status === 401) {
        this.logout();
        throw new Error('Authentication required');
      }
      throw new Error(error.response?.data?.detail || 'Failed to send message');
    }
  }
  
  async search(request: SearchRequest): Promise<SearchResponse> {
    try {
      const response = await axios.post<SearchResponse>(
        `${API_BASE_URL}/search/`,
        request,
        {
          headers: this.getHeaders()
        }
      );
      
      if (response.status === 401) {
        this.logout();
        throw new Error('Authentication required');
      }
      
      return response.data;
    } catch (error: any) {
      console.error('Search error:', error);
      if (error.response?.status === 401) {
        this.logout();
        throw new Error('Authentication required');
      }
      throw new Error(error.response?.data?.detail || 'Search failed');
    }
  }
  
  async getSystemStats(): Promise<any> {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/system/stats`,
        {
          headers: this.getHeaders()
        }
      );
      
      return response.data;
    } catch (error: any) {
      console.error('Get system stats error:', error);
      throw new Error(error.response?.data?.detail || 'Failed to get stats');
    }
  }
  
  async getHealth(): Promise<any> {
    try {
      const response = await axios.get(`${API_BASE_URL}/system/health`);
      return response.data;
    } catch (error: any) {
      console.error('Health check error:', error);
      throw new Error('Health check failed');
    }
  }
  
  logout(): void {
    this.token = null;
    localStorage.removeItem('token');
    window.location.href = '/login';
  }
  
  isAuthenticated(): boolean {
    return !!this.token;
  }
  
  getToken(): string | null {
    return this.token;
  }
}

export default new APIService();
