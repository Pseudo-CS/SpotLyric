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
google_search(query)
