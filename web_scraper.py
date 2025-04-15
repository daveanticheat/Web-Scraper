import requests
from bs4 import BeautifulSoup
import csv
import json
import os
from urllib.parse import urljoin
import time
from dataclasses import dataclass
from typing import List, Optional
import argparse

# Constants
BASE_URL = "https://scrape-test-site.vercel.app"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
DELAY = 1  # seconds between requests to be polite
MAX_PAGES = 3  # safety limit for demo purposes

@dataclass
class Product:
    name: str
    price: float
    description: str
    rating: float
    url: str
    category: Optional[str] = None
    in_stock: bool = True

class WebScraper:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.scraped_data: List[Product] = []

    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage with error handling"""
        try:
            time.sleep(DELAY)  # Be polite to servers
            response = self.session.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def scrape_products(self, category: str = "all", max_pages: int = MAX_PAGES) -> None:
        """Main scraping function that handles pagination"""
        page = 1
        while page <= max_pages:
            url = f"{self.base_url}/products/{category}?page={page}" if category != "all" else f"{self.base_url}/products?page={page}"
            print(f"Scraping page {page}: {url}")
            
            soup = self.fetch_page(url)
            if not soup:
                break

            products = self._parse_product_listing(soup)
            if not products:
                print("No more products found")
                break

            self.scraped_data.extend(products)
            page += 1

    def _parse_product_listing(self, soup: BeautifulSoup) -> List[Product]:
        """Parse product cards from listing page"""
        products = []
        product_cards = soup.select('.product-card')
        
        for card in product_cards:
            try:
                name = card.select_one('.product-name').text.strip()
                price_str = card.select_one('.product-price').text.strip().replace('$', '')
                price = float(price_str)
                description = card.select_one('.product-description').text.strip()
                rating_str = card.select_one('.product-rating')['data-rating']
                rating = float(rating_str)
                relative_url = card.select_one('a')['href']
                full_url = urljoin(self.base_url, relative_url)
                
                # Get additional details from product page
                product_details = self._get_product_details(full_url)
                
                products.append(Product(
                    name=name,
                    price=price,
                    description=description,
                    rating=rating,
                    url=full_url,
                    category=product_details.get('category'),
                    in_stock=product_details.get('in_stock', True)
                ))
            except (AttributeError, ValueError) as e:
                print(f"Error parsing product: {e}")
                continue
        
        return products

    def _get_product_details(self, url: str) -> dict:
        """Get additional details from individual product page"""
        details = {}
        soup = self.fetch_page(url)
        if not soup:
            return details
        
        try:
            category = soup.select_one('.breadcrumb a:last-child').text.strip()
            stock_status = soup.select_one('.stock-status').text.strip().lower()
            details = {
                'category': category,
                'in_stock': 'in stock' in stock_status
            }
        except AttributeError:
            pass
            
        return details

    def export_to_csv(self, filename: str = "products.csv") -> None:
        """Export scraped data to CSV"""
        if not self.scraped_data:
            print("No data to export")
            return
            
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=vars(self.scraped_data[0]).keys())
                writer.writeheader()
                for product in self.scraped_data:
                    writer.writerow(vars(product))
            print(f"Successfully exported {len(self.scraped_data)} products to {filename}")
        except IOError as e:
            print(f"Error exporting to CSV: {e}")

    def export_to_json(self, filename: str = "products.json") -> None:
        """Export scraped data to JSON"""
        if not self.scraped_data:
            print("No data to export")
            return
            
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump([vars(p) for p in self.scraped_data], f, indent=2)
            print(f"Successfully exported {len(self.scraped_data)} products to {filename}")
        except IOError as e:
            print(f"Error exporting to JSON: {e}")

def main():
    parser = argparse.ArgumentParser(description="Web Scraper for E-commerce Products")
    parser.add_argument('--category', type=str, default="all", help="Product category to scrape")
    parser.add_argument('--pages', type=int, default=MAX_PAGES, help="Maximum pages to scrape")
    parser.add_argument('--csv', action='store_true', help="Export to CSV")
    parser.add_argument('--json', action='store_true', help="Export to JSON")
    args = parser.parse_args()

    scraper = WebScraper()
    
    print(f"Starting scraping for category: {args.category}")
    scraper.scrape_products(category=args.category, max_pages=args.pages)
    
    if args.csv:
        scraper.export_to_csv()
    if args.json:
        scraper.export_to_json()
    
    if not args.csv and not args.json:
        print("\nScraped Products Preview:")
        for i, product in enumerate(scraper.scraped_data[:3], 1):
            print(f"\nProduct {i}:")
            print(f"Name: {product.name}")
            print(f"Price: ${product.price:.2f}")
            print(f"Category: {product.category}")
            print(f"Rating: {product.rating}/5")
        
        print(f"\nTotal products scraped: {len(scraper.scraped_data)}")
        print("Use --csv or --json flags to export data")

if __name__ == "__main__":
    main()