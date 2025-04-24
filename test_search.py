import requests
from bs4 import BeautifulSoup

def duckduckgo_search(query):
    url = f"https://html.duckduckgo.com/html/?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    results = []
    for result in soup.find_all('a', class_='result__url', limit=10):
        results.append(result['href'])

    for i, link in enumerate(results, 1):
        print(f"{i}. {link}")

# Example
duckduckgo_search("OpenAI news")
