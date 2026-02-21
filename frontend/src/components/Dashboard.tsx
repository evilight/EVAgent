import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import ChatComponent from './ChatComponent';
import SearchComponent from './SearchComponent';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'chat' | 'search' | 'stats'>('chat');
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    if (activeTab === 'stats') {
      fetchStats();
    }
  }, [activeTab]);

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/v1/system/stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          EVAgent RAG System
        </h1>
        <div className="flex items-center gap-4">
          <span className="text-gray-600">Welcome, {user || 'User'}</span>
          <button
            onClick={logout}
            className="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600"
          >
            Logout
          </button>
        </div>
      </div>

      <div className="mb-6">
        <nav className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === 'chat'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            💬 Chat
          </button>
          <button
            onClick={() => setActiveTab('search')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === 'search'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            🔍 Search
          </button>
          <button
            onClick={() => setActiveTab('stats')}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              activeTab === 'stats'
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            📊 Stats
          </button>
        </nav>
      </div>

      <div className="space-y-6">
        {activeTab === 'chat' && <ChatComponent />}
        {activeTab === 'search' && <SearchComponent />}
        {activeTab === 'stats' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">System Statistics</h2>
            {stats ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-blue-900 mb-2">Documents</h3>
                  <p className="text-2xl font-bold text-blue-600">{stats.total_documents || 0}</p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-green-900 mb-2">Conversations</h3>
                  <p className="text-2xl font-bold text-green-600">{stats.total_conversations || 0}</p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-purple-900 mb-2">Total Searches</h3>
                  <p className="text-2xl font-bold text-purple-600">{stats.total_searches || 0}</p>
                </div>
                <div className="bg-yellow-50 p-4 rounded-lg">
                  <h3 className="font-semibold text-yellow-900 mb-2">Models</h3>
                  <div className="text-sm text-yellow-800">
                    <p><strong>Embedding:</strong> {stats.model_info?.embedding_model || 'Unknown'}</p>
                    <p><strong>LLM:</strong> {stats.model_info?.llm_model || 'Unknown'}</p>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-gray-500">Loading statistics...</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
