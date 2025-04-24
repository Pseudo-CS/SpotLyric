from googlesearch import search

def google_search(query, num_results=10):
    try:
        results = search(query, num_results=num_results)
        print(f"\nTop {num_results} results for '{query}':\n")
        for i, url in enumerate(results, 1):
            print(f"{i}. {url}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
query = "latest advancements in AI"
#google_search(query)

def google_search_lyrics(song_name, artist_name, num_results=10):
    """Search for lyrics using Google search API"""

    search_query = f"{song_name} {artist_name} translation lyrics"
    
    try:
        results = list(search(search_query, num_results=num_results))
        matches = []
        
        for url in results:
            title = url.split('/')[-1].replace('-', ' ').title()
            matches.append({
                'url': url,
                'title': title
            })
        
        print(f"Found {len(matches)} results")
        # Cache the results
        return matches
        
    except Exception as e:
        print(f"Google search error: {str(e)}")
        return []
    
print(google_search_lyrics("chundari penne", "gopi sundar"))