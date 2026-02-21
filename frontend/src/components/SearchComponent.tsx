import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface SearchResult {
  id: string;
  title: string;
  content: string;
  score: number;
}

const SearchComponent: React.FC = () => {
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch('/api/v1/search/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ query })
      });

      const data = await response.json();
      setResults(data.results || []);
    } catch (error) {
      console.error('Error searching:', error);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-xl font-semibold mb-4">Search Documents</h2>
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && search()}
          placeholder="Enter search query..."
          className="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={isLoading}
        />
        <button
          onClick={search}
          disabled={isLoading || !query.trim()}
          className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 disabled:bg-gray-300"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </div>
      
      {results.length === 0 && !isLoading && query && (
        <p className="text-gray-500 text-center py-4">No results found for "{query}"</p>
      )}
      
      {results.length === 0 && !query && (
        <p className="text-gray-500 text-center py-4">Enter a search query to find documents</p>
      )}
      
      {results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-gray-600">Found {results.length} results:</p>
          {results.map((result) => (
            <div key={result.id} className="border rounded-lg p-4 hover:bg-gray-50">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-lg">{result.title}</h3>
                <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  Score: {(result.score * 100).toFixed(1)}%
                </span>
              </div>
              <p className="text-gray-700">{result.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchComponent;
