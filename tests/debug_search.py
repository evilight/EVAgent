"""Debug search functionality"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simple_api import search_documents

def debug_search():
    print("Debugging search functionality...")
    print("=" * 50)
    
    queries = [
        "EVAgent",
        "components", 
        "system",
        "architecture",
        "what are the components of EVAgent system"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        results = search_documents(query, limit=5)
        print(f"Results: {len(results)}")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result['title']} (score: {result['score']})")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    debug_search()
