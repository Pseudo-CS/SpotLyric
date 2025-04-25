import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse

def duckduckgo_search(query):
    url = f"https://html.duckduckgo.com/html/?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    results = []
    for result in soup.find_all('a', class_='result__url', limit=10):
        # Extract the actual URL from the redirect link
        redirect_url = result['href']
        if redirect_url.startswith('//duckduckgo.com/l/'):
            # Extract the actual URL from the redirect
            query_params = urlparse(redirect_url).query
            for param in query_params.split('&'):
                if param.startswith('uddg='):
                    actual_url = unquote(param[5:])
                    results.append(actual_url)
                    break
        else:
            results.append(redirect_url)

    for i, link in enumerate(results, 1):
        print(f"{i}. {link}")

# Example
duckduckgo_search("chundari penne translations lyrics")

