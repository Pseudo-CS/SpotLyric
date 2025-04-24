from main import search_lyrics_translations
from serpapi import GoogleSearch
import os
import time

def test_search():
    # Test cases
    test_cases = [
        ("chundari penne", "gopi sundar"),
    ]
    
    # Get SerpAPI key from environment variable
    api_key = '6b1c5ada495ea534107a4ac5807851e770c104235fa4e198d8d7f5beeaebeb31'
    if not api_key:
        print("Error: SERPAPI_KEY environment variable not set")
        print("Please set your SerpAPI key using: set SERPAPI_KEY=your_api_key")
        return
    
    for song, artist in test_cases:
        print(f"\nSearching for: {song} by {artist}")
        results = search_lyrics_translations(song, artist)
        
        if results:
            print(f"Found {len(results)} sources:")
            for result in results:
                print(f"- Source: {result['source']}")
                print(f"  Title: {result['title']}")
                print(f"  URL: {result['url']}")
        else:
            print("No sources found")
            
        # Search using SerpAPI
        print("\nSerpAPI Results:")
        search_query = f"{song} {artist} lyrics translation"
        
        params = {
            "engine": "google",
            "q": search_query,
            "api_key": api_key,
            "num": 10,  # Number of results to return
            "gl": "in",  # Country to search from
            "hl": "en"   # Language of results
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "error" in results:
                print(f"Error from SerpAPI: {results['error']}")
                continue
                
            if "organic_results" in results:
                print(f"Found {len(results['organic_results'])} results")
                
                for i, result in enumerate(results['organic_results'][:5], 1):
                    print(f"\nResult {i}:")
                    print(f"Title: {result.get('title', 'No title')}")
                    print(f"Link: {result.get('link', 'No link')}")
                    print(f"Snippet: {result.get('snippet', 'No snippet')}")
                    
                    # Print additional information if available
                    if 'sitelinks' in result:
                        print("\nSitelinks:")
                        for sitelink in result['sitelinks']:
                            print(f"- {sitelink.get('title', 'No title')}: {sitelink.get('link', 'No link')}")
                    
            else:
                print("No organic results found")
                
        except Exception as e:
            print(f"Error occurred: {str(e)}")
        
        # Add delay between searches
        time.sleep(2)
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    test_search() 