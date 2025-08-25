import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse

def debug_duckduckgo_search():
    search_query = "Shape of You Ed Sheeran translation lyrics"
    url = f"https://html.duckduckgo.com/html/?q={search_query}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        res = requests.get(url, headers=headers)
        print(f"Status code: {res.status_code}")
        print(f"Content length: {len(res.text)}")
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Check for different result classes
        print("\nLooking for different result classes...")
        print(f"result: {len(soup.find_all('div', class_='result'))}")
        print(f"result__body: {len(soup.find_all('div', class_='result__body'))}")
        print(f"web-result: {len(soup.find_all('div', class_='web-result'))}")
        print(f"links-result: {len(soup.find_all('div', class_='links-result'))}")
        print(f"result-snippet: {len(soup.find_all('div', class_='result-snippet'))}")
        
        # Look for any divs with "result" in class name
        print("\nAll divs with 'result' in class name:")
        result_divs = []
        for div in soup.find_all('div'):
            if div.get('class'):
                classes = div.get('class')
                if any('result' in cls.lower() for cls in classes):
                    result_divs.append(classes)
                    if len(result_divs) <= 5:  # Show first 5
                        print(f"  {classes}")
        
        print(f"\nTotal result divs found: {len(result_divs)}")
        
        # Try to find links
        print("\nLooking for links...")
        links = soup.find_all('a')
        print(f"Total links found: {len(links)}")
        
        # Look for specific patterns
        for link in links[:10]:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                print(f"  Link: {text[:50]}... -> {href[:80]}...")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_duckduckgo_search()