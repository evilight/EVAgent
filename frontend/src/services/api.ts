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
      console.log('🔍 Login attempt:', { username, password: '***' });
      console.log('🔍 API URL:', `${API_BASE_URL}/auth/login`);
      
      const response = await axios.post<LoginResponse>(
        `${API_BASE_URL}/auth/login`,
        {
          username: username,
          password: password
        },
        {
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );
      
      console.log('🔍 Raw response:', response);
      console.log('🔍 Response status:', response.status);
      console.log('🔍 Response data:', response.data);
      console.log('🔍 Response headers:', response.headers);
      
      if (response.data && response.data.access_token) {
        this.token = response.data.access_token;
        localStorage.setItem('token', this.token);
        console.log('🔍 Token saved:', this.token.substring(0, 20) + '...');
        return response.data;
      } else {
        console.error('❌ Invalid response format:', response);
        throw new Error('Login failed - invalid response format');
      }
    } catch (error: any) {
      console.error('❌ Login error:', error);
      console.error('❌ Error response:', error.response);
      console.error('❌ Error status:', error.response?.status);
      console.error('❌ Error message:', error.message);
      throw new Error(error.response?.data?.detail || error.message || 'Login failed');
    }
  }
  
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    try {
      console.log('🔍 Chat request:', request);
      console.log('🔍 Request headers:', this.getHeaders());
      
      const response = await axios.post<ChatResponse>(
        `${API_BASE_URL}/chat/`,
        request,
        {
          headers: this.getHeaders()
        }
      );
      
      console.log('🔍 Chat response status:', response.status);
      console.log('🔍 Chat response headers:', response.headers);
      console.log('🔍 Chat response data:', response.data);
      
      if (response.status === 401) {
        this.logout();
        throw new Error('Authentication required');
      }
      
      return response.data;
    } catch (error: any) {
      console.error('❌ Chat error:', error);
      console.error('❌ Error response:', error.response);
      console.error('❌ Error status:', error.response?.status);
      console.error('❌ Error message:', error.message);
      console.error('❌ Error config:', error.config);
      
      if (error.response?.status === 401) {
        this.logout();
        throw new Error('Authentication required');
      }
      throw new Error(error.response?.data?.detail || error.message || 'Failed to send message');
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
