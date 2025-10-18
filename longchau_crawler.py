import requests
import json
import csv
import time
import sys
import os
import logging
from typing import List, Dict, Optional

# Set up encoding for Windows
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        os.system('chcp 65001 > nul')
    except:
        pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = "longchau_data"
OUTPUT_FILE = "longchau_products.csv"
CATEGORIES = [
    "thuc-pham-chuc-nang",
    "duoc-my-pham",     
    "thuoc",
    "cham-soc-ca-nhan",
    "trang-thiet-bi-y-te",
]
MAX_RESULT_COUNT = 100
SKIP_COUNT = 0

class APIClient:
    """Handles API communication with the Long Chau API"""
    
    def __init__(self):
        self.base_url = "https://api.nhathuoclongchau.com.vn/lccus/search-product-service/api/products/ecom/product/search/cate"
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
            "access-control-allow-origin": "*",
            "content-type": "application/json",
            "order-channel": "1",
            "origin": "https://nhathuoclongchau.com.vn",
            "priority": "u=1, i",
            "referer": "https://nhathuoclongchau.com.vn/",
            "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            "x-channel": "EStore"
        }
    
    def make_request(self, category: str, skip_count: int = 0, max_result_count: int = MAX_RESULT_COUNT) -> Optional[Dict]:
        """Make API request to get products for a specific category with advanced filtering"""
        payload = {
            "skipCount": skip_count,
            "maxResultCount": max_result_count,
            "codes": [
                "productTypes",
                "objectUse", 
                "priceRanges",
                "prescription",
                "skin",
                "flavor",
                "manufactor",
                "indications",
                "brand",
                "brandOrigin"
            ],
            "sortType": 4,
            "category": [category]
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for category {category}, skip {skip_count}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response for category {category}, skip {skip_count}: {e}")
            return None

class ProductProcessor:
    """Handles product data extraction and processing"""
    
    @staticmethod
    def extract_product_data(product: Dict, count: int = 0) -> Dict:
        """Extract relevant product data from API response"""
        try:
            price_info = product.get('price', {})
            prices_list = product.get('prices', [])
            
            primary_price = price_info.get('price', 'N/A')
            price_unit = price_info.get('measureUnitName', 'N/A')
            currency_symbol = price_info.get('currencySymbol', 'đ')
            
            categories = product.get('category', [])
            category_names = []
            category_slugs = []
            for cat in categories:
                if isinstance(cat, dict):
                    category_names.append(cat.get('name', ''))
                    category_slugs.append(cat.get('slug', ''))
            
            product_data = {
                'count': count,
                'sku': product.get('sku', 'N/A'),
                'name': product.get('name', 'N/A'),
                'web_name': product.get('webName', 'N/A'),
                'slug': product.get('slug', 'N/A'),
                'price': primary_price,
                'price_unit': price_unit,
                'currency_symbol': currency_symbol,
                'image_url': product.get('image', 'N/A'),
                'ingredients': product.get('ingredients', 'N/A'),
                'dosage_form': product.get('dosageForm', 'N/A'),
                'brand': product.get('brand', 'N/A'),
                'specification': product.get('specification', 'N/A'),
                'category_names': ' | '.join(category_names) if category_names else 'N/A',
                'category_slugs': ' | '.join(category_slugs) if category_slugs else 'N/A',
                'is_active': product.get('isActive', 'N/A'),
                'is_publish': product.get('isPublish', 'N/A'),
                'search_scoring': product.get('searchScoring', 'N/A'),
                'product_ranking': product.get('productRanking', 'N/A'),
                'link': f"https://nhathuoclongchau.com.vn/{product.get('slug', '')}" if product.get('slug') else 'N/A'
            }
            return product_data
            
        except Exception as e:
            logger.error(f"Error extracting product data: {e}")
            return None
    
    @staticmethod
    def remove_duplicates(products_data: List[Dict]) -> List[Dict]:
        """Remove duplicate products based on SKU"""
        if not products_data:
            return products_data
        
        seen_skus = set()
        unique_products = []
        
        for product in products_data:
            product_sku = product.get('sku')
            
            if product_sku and product_sku not in seen_skus:
                seen_skus.add(product_sku)
                unique_products.append(product)
            elif not product_sku:
                unique_products.append(product)
        
        duplicates_removed = len(products_data) - len(unique_products)
        
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate products")
        
        return unique_products

class DataExporter:
    """Handles data export to CSV files"""
    
    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = output_dir
        self.fieldnames = [
            'count', 'sku', 'name', 'web_name', 'slug', 'price', 'price_unit', 'currency_symbol',
            'image_url', 'ingredients', 'dosage_form', 'brand', 'specification',
            'category_names', 'category_slugs', 'is_active', 'is_publish',
            'search_scoring', 'product_ranking', 'link', 'category', 'skip_count'
        ]
        
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except Exception:
            pass
    
    def save_to_csv(self, products_data: List[Dict], filename: str = None):
        """Save products data to CSV file"""
        if not products_data:
            logger.warning("No products data to save")
            return
        
        output_filename = filename or os.path.join(self.output_dir, OUTPUT_FILE)
        
        try:
            with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(products_data)
            
            logger.info(f"Saved {len(products_data)} products to {output_filename}")
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
    
    def save_by_category(self, products_data: List[Dict]):
        """Save products data to separate CSV files by category"""
        if not products_data:
            logger.warning("No products data to save")
            return
        
        categories = {}
        for product in products_data:
            category = product.get('category', 'unknown')
            if category not in categories:
                categories[category] = []
            categories[category].append(product)
        
        for category, products in categories.items():
            filename = os.path.join(self.output_dir, f"{category}.csv")
            self.save_category_to_csv(products, filename)
            logger.info(f"Saved {len(products)} products for category '{category}' to {filename}")
    
    def save_category_to_csv(self, products: List[Dict], filename: str):
        """Save products for a specific category to CSV file"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(products)
            
        except Exception as e:
            logger.error(f"Error saving category CSV {filename}: {e}")

class CategoryCrawler:
    """Handles crawling for individual categories"""
    
    def __init__(self, api_client: APIClient, product_processor: ProductProcessor):
        self.api_client = api_client
        self.product_processor = product_processor
    
    def crawl_category(self, category: str) -> List[Dict]:
        """Crawl all products for a specific category"""
        logger.info(f"Starting to crawl category: {category}")
        skip_count = SKIP_COUNT
        max_result_count = MAX_RESULT_COUNT
        products_data = []
        count = 1
        
        while True:
            logger.info(f"  Requesting category {category}, skip {skip_count}...")
            
            response_data = self.api_client.make_request(category, skip_count, max_result_count)
            
            if not response_data:
                logger.warning(f"  No response for category {category}, skip {skip_count}")
                break
            
            products = response_data.get('products', [])
            
            if not products:
                logger.info(f"  No more products found for category {category} at skip {skip_count}")
                break
            
            for product in products:
                product_data = self.product_processor.extract_product_data(product, count)
                if product_data:
                    product_data['category'] = category
                    product_data['skip_count'] = skip_count
                    products_data.append(product_data)
                    count += 1
            
            logger.info(f"  Found {len(products)} products for category {category}, skip {skip_count}")
            
            if len(products) < max_result_count:
                logger.info(f"  Reached end of products for category {category}")
                break
            
            skip_count += max_result_count
            time.sleep(0.5)
        
        logger.info(f"Completed category {category}: {len(products_data)} products")
        return products_data

class AdvancedCrawler:
    """Main crawler class that orchestrates the crawling process"""
    
    def __init__(self, output_dir: str = OUTPUT_DIR):
        """Initialize the advanced crawler with all required components"""
        self.api_client = APIClient()
        self.product_processor = ProductProcessor()
        self.data_exporter = DataExporter(output_dir)
        self.category_crawler = CategoryCrawler(self.api_client, self.product_processor)
        self.products_data = []
        self.output_dir = output_dir
        self.categories = CATEGORIES
    
    def crawl_all_categories(self) -> int:
        """Crawl all categories and return total number of products found"""
        logger.info("Starting to crawl all categories...")
        total_products = 0
        
        for category in self.categories:
            try:
                category_products = self.category_crawler.crawl_category(category)
                self.products_data.extend(category_products)
                total_products += len(category_products)
                
                self.data_exporter.save_to_csv(self.products_data)
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error crawling category {category}: {e}")
                continue
        
        logger.info(f"Crawling completed. Total products found: {total_products}")
        return total_products
    
    def process_and_save_data(self):
        """Process the crawled data and save to files"""
        self.products_data = self.product_processor.remove_duplicates(self.products_data)
        self.data_exporter.save_to_csv(self.products_data)
        self.data_exporter.save_by_category(self.products_data)
    
    def run(self):
        """Main method to run the complete crawling process"""
        try:
            total_products = self.crawl_all_categories()
            self.process_and_save_data()
            
            logger.info("=== ADVANCED CRAWLING SUMMARY ===")
            logger.info(f"Total products found: {len(self.products_data)}")
            logger.info(f"Combined file: {os.path.join(self.output_dir, OUTPUT_FILE)}")
            logger.info(f"Category files saved in: {self.output_dir}/")
            
        except KeyboardInterrupt:
            logger.warning("Crawling interrupted by user")
            self.process_and_save_data()
        except Exception as e:
            logger.error(f"Error during crawling: {e}")
            self.process_and_save_data()

def main():
    """Main function to run the advanced crawler"""
    crawler = AdvancedCrawler()
    crawler.run()

if __name__ == "__main__":
    main()
