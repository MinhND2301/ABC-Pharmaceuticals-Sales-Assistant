import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PURCHASE_HISTORY_FILE_PATH = "gemini_output/purchase_history_with_ai_extraction.csv"
PROMOTIONS_FILE_PATH = "gemini_output/promotions_with_ai_extraction.csv"
COMPARISON_REPORT_FILE_PATH = "gemini_output/ai_extraction_comparison_report.csv"
LONGCHAU_PRODUCTS_FILE_PATH = "longchau_data/longchau_products.csv"
OUTPUT_DIR = "standardized_data_output"


class DataStandardizer:
    """
    Class to standardize and combine data from multiple sources including
    Long Chau products, AI extraction results, purchase history, and promotions.
    """
    
    def __init__(self):
        """Initialize the DataStandardizer."""
        self.lc_products: Optional[pd.DataFrame] = None
        self.purchase_history: Optional[pd.DataFrame] = None
        self.promotions: Optional[pd.DataFrame] = None
        self.comparison_report: Optional[pd.DataFrame] = None
        self.product_mapping: Dict[str, List[str]] = {}
        self.purchase_agg: Optional[pd.DataFrame] = None
        self.promo_agg: Optional[pd.DataFrame] = None
        self.standardized_df: Optional[pd.DataFrame] = None
        self.summary_stats: Optional[Dict] = None
    
    def load_source_data(self) -> bool:
        """
        Load all source data files.
        
        Returns:
            bool: True if all data loaded successfully, False otherwise
        """
        logger.info("Loading source data...")
        
        try:
            # Load Long Chau products database
            self.lc_products = pd.read_csv(LONGCHAU_PRODUCTS_FILE_PATH)
            
            # Load AI extraction results
            self.purchase_history = pd.read_csv(PURCHASE_HISTORY_FILE_PATH)
            self.promotions = pd.read_csv(PROMOTIONS_FILE_PATH)
            self.comparison_report = pd.read_csv(COMPARISON_REPORT_FILE_PATH)
            
            logger.info(f"Loaded {len(self.lc_products)} Long Chau products")
            logger.info(f"Loaded {len(self.purchase_history)} purchase records with AI extraction")
            logger.info(f"Loaded {len(self.promotions)} promotion records with AI extraction")
            logger.info(f"Loaded {len(self.comparison_report)} AI extraction comparison results")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def create_product_mapping(self) -> Dict[str, List[str]]:
        """
        Create mapping from AI extracted products to Long Chau products.
        
        Returns:
            Dict[str, List[str]]: Product mapping dictionary
        """
        logger.info("Creating product mapping...")
        
        self.product_mapping = {}
        
        for _, row in self.comparison_report.iterrows():
            ai_product = row['AI_extracted_product']
            matches = row['top_longchau_matches']
            
            if pd.notna(matches) and matches != 'No matches':
                # Split matches and clean them
                match_list = [match.strip() for match in matches.split(';') if match.strip()]
                self.product_mapping[ai_product] = match_list
            else:
                self.product_mapping[ai_product] = []
        
        logger.info(f"Created mapping for {len(self.product_mapping)} AI extracted products")
        return self.product_mapping
    
    def aggregate_purchase_data(self) -> pd.DataFrame:
        """
        Aggregate purchase history data by AI extracted product.
        
        Returns:
            pd.DataFrame: Aggregated purchase data
        """
        logger.info("Aggregating purchase data...")
        
        # Group by AI extracted product and aggregate
        self.purchase_agg = self.purchase_history.groupby('AI_extracted_product').agg({
            'Số lượng': ['sum', 'count', 'mean'],
            'Đơn giá (VND)': ['mean', 'min', 'max'],
            'Nhà thuốc': lambda x: ', '.join(x.unique()),
            'Ngày mua': ['min', 'max']
        }).round(2)
        
        # Flatten column names
        self.purchase_agg.columns = [
            'total_quantity_purchased', 'purchase_frequency', 'avg_quantity_per_purchase',
            'avg_price', 'min_price', 'max_price', 'pharmacies', 'first_purchase_date', 'last_purchase_date'
        ]
        
        self.purchase_agg = self.purchase_agg.reset_index()
        logger.info(f"Aggregated data for {len(self.purchase_agg)} unique products")
        
        return self.purchase_agg
    
    def aggregate_promotion_data(self) -> pd.DataFrame:
        """
        Aggregate promotion data by AI extracted product.
        
        Returns:
            pd.DataFrame: Aggregated promotion data
        """
        logger.info("Aggregating promotion data...")
        
        # Group by AI extracted product and aggregate
        self.promo_agg = self.promotions.groupby('AI_extracted_product').agg({
            'chuong_trinh': lambda x: '; '.join(x.unique()),
            'nhom_san_pham': lambda x: ', '.join(x.unique()),
            'san_pham': 'count'
        })
        
        self.promo_agg.columns = ['promotion_programs', 'promotion_categories', 'promotion_count']
        self.promo_agg = self.promo_agg.reset_index()
        
        logger.info(f"Aggregated promotion data for {len(self.promo_agg)} unique products")
        return self.promo_agg
    
    def create_standardized_dataset(self) -> pd.DataFrame:
        """
        Create the standardized dataset combining all information.
        
        Returns:
            pd.DataFrame: Standardized dataset
        """
        logger.info("Creating standardized dataset...")
        
        standardized_records = []
        
        for _, lc_row in self.lc_products.iterrows():
            # Base record from Long Chau
            record = {
                'product_id': f"LC_{lc_row['sku']}" if pd.notna(lc_row['sku']) else f"LC_{lc_row.name}",
                'product_name': lc_row['name'],
                'product_name_original': lc_row['name'],
                'brand': lc_row['brand'] if pd.notna(lc_row['brand']) else 'Unknown',
                'category': lc_row['category_names'].split(' | ')[0] if pd.notna(lc_row['category_names']) else 'Unknown',
                'subcategory': lc_row['category_names'].split(' | ')[1] if pd.notna(lc_row['category_names']) and ' | ' in lc_row['category_names'] else '',
                'sku': lc_row['sku'] if pd.notna(lc_row['sku']) else '',
                'price': lc_row['price'] if pd.notna(lc_row['price']) else 0,
                'price_unit': lc_row['price_unit'] if pd.notna(lc_row['price_unit']) else 'Hộp',
                'dosage_form': lc_row['dosage_form'] if pd.notna(lc_row['dosage_form']) else '',
                'ingredients': lc_row['ingredients'] if pd.notna(lc_row['ingredients']) else '',
                'specification': lc_row['specification'] if pd.notna(lc_row['specification']) else '',
                'is_active': lc_row['is_active'] if pd.notna(lc_row['is_active']) else True,
                'source_database': 'Long Chau',
                
                # Initialize AI extraction fields
                'ai_extracted_product': '',
                'has_ai_match': False,
                'ai_match_confidence': 0,
                
                # Initialize purchase data
                'total_quantity_purchased': 0,
                'purchase_frequency': 0,
                'avg_quantity_per_purchase': 0,
                'avg_purchase_price': 0,
                'min_purchase_price': 0,
                'max_purchase_price': 0,
                'pharmacies': '',
                'first_purchase_date': '',
                'last_purchase_date': '',
                
                # Initialize promotion data
                'promotion_programs': '',
                'promotion_categories': '',
                'promotion_count': 0,
                
                # Summary fields
                'has_purchase_data': False,
                'has_promotion_data': False,
                'data_completeness_score': 0
            }
            
            # Check for AI extraction matches
            lc_name_lower = lc_row['name'].lower()
            matched_ai_product = None
            
            for ai_product, lc_matches in self.product_mapping.items():
                if any(ai_product.lower() in match.lower() or match.lower() in ai_product.lower() 
                       for match in lc_matches):
                    # Check if this Long Chau product matches
                    if any(lc_name_lower in match.lower() or match.lower() in lc_name_lower 
                           for match in lc_matches):
                        matched_ai_product = ai_product
                        break
            
            if matched_ai_product:
                record['ai_extracted_product'] = matched_ai_product
                record['has_ai_match'] = True
                record['ai_match_confidence'] = 1.0  # High confidence for direct matches
                
                # Add purchase data if available
                purchase_data = self.purchase_agg[self.purchase_agg['AI_extracted_product'] == matched_ai_product]
                if not purchase_data.empty:
                    purchase_row = purchase_data.iloc[0]
                    record.update({
                        'total_quantity_purchased': purchase_row['total_quantity_purchased'],
                        'purchase_frequency': purchase_row['purchase_frequency'],
                        'avg_quantity_per_purchase': purchase_row['avg_quantity_per_purchase'],
                        'avg_purchase_price': purchase_row['avg_price'],
                        'min_purchase_price': purchase_row['min_price'],
                        'max_purchase_price': purchase_row['max_price'],
                        'pharmacies': purchase_row['pharmacies'],
                        'first_purchase_date': purchase_row['first_purchase_date'],
                        'last_purchase_date': purchase_row['last_purchase_date'],
                        'has_purchase_data': True
                    })
                
                # Add promotion data if available
                promo_data = self.promo_agg[self.promo_agg['AI_extracted_product'] == matched_ai_product]
                if not promo_data.empty:
                    promo_row = promo_data.iloc[0]
                    record.update({
                        'promotion_programs': promo_row['promotion_programs'],
                        'promotion_categories': promo_row['promotion_categories'],
                        'promotion_count': promo_row['promotion_count'],
                        'has_promotion_data': True
                    })
            
            # Calculate data completeness score
            completeness_score = 0
            if record['has_ai_match']:
                completeness_score += 1
            if record['has_purchase_data']:
                completeness_score += 1
            if record['has_promotion_data']:
                completeness_score += 1
            if record['price'] > 0:
                completeness_score += 1
            if record['ingredients']:
                completeness_score += 1
            
            record['data_completeness_score'] = completeness_score / 5.0  # Normalize to 0-1
            
            standardized_records.append(record)
        
        self.standardized_df = pd.DataFrame(standardized_records)
        logger.info(f"Created standardized dataset with {len(self.standardized_df)} records")
        
        return self.standardized_df
    
    def save_standardized_data(self) -> Dict:
        """
        Save the standardized dataset and generate summary reports.
        
        Returns:
            Dict: Summary statistics
        """
        logger.info("Saving standardized data...")
        
        # Create output directory
        output_dir = Path('standardized_data_output')
        output_dir.mkdir(exist_ok=True)
        
        # Save main dataset
        output_file = output_dir / 'standardized_data.csv'
        self.standardized_df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"Saved standardized dataset: {output_file}")
        
        # Generate summary statistics
        self.summary_stats = {
            'total_products': len(self.standardized_df),
            'products_with_ai_matches': len(self.standardized_df[self.standardized_df['has_ai_match'] == True]),
            'products_with_purchase_data': len(self.standardized_df[self.standardized_df['has_purchase_data'] == True]),
            'products_with_promotion_data': len(self.standardized_df[self.standardized_df['has_promotion_data'] == True]),
            'products_with_complete_data': len(self.standardized_df[self.standardized_df['data_completeness_score'] >= 0.8]),
            'avg_completeness_score': self.standardized_df['data_completeness_score'].mean(),
            'total_purchase_quantity': self.standardized_df['total_quantity_purchased'].sum(),
            'total_purchase_frequency': self.standardized_df['purchase_frequency'].sum()
        }
        
        # Save summary
        summary_df = pd.DataFrame([self.summary_stats])
        summary_df.to_csv(output_dir / 'summary_statistics.csv', index=False, encoding='utf-8')
        
        # Create high-value products subset (products with both purchase and promotion data)
        high_value_products = self.standardized_df[
            (self.standardized_df['has_purchase_data'] == True) & 
            (self.standardized_df['has_promotion_data'] == True)
        ].copy()
        
        if not high_value_products.empty:
            high_value_products.to_csv(output_dir / 'high_value_products.csv', index=False, encoding='utf-8')
            logger.info(f"Saved {len(high_value_products)} high-value products")
        
        # Create products with AI matches subset
        ai_matched_products = self.standardized_df[self.standardized_df['has_ai_match'] == True].copy()
        if not ai_matched_products.empty:
            ai_matched_products.to_csv(output_dir / 'ai_matched_products.csv', index=False, encoding='utf-8')
            logger.info(f"Saved {len(ai_matched_products)} AI-matched products")
        
        return self.summary_stats
    
    def print_summary_report(self) -> None:
        """Print comprehensive summary report."""
        if self.summary_stats is None:
            logger.warning("No summary statistics available. Run save_standardized_data() first.")
            return
        
        logger.info("STANDARDIZED DATA SUMMARY REPORT")
        logger.info("=" * 60)
        
        logger.info("Dataset Overview:")
        logger.info(f"  Total products in standardized dataset: {self.summary_stats['total_products']:,}")
        logger.info(f"  Products with AI matches: {self.summary_stats['products_with_ai_matches']:,}")
        logger.info(f"  Products with purchase data: {self.summary_stats['products_with_purchase_data']:,}")
        logger.info(f"  Products with promotion data: {self.summary_stats['products_with_promotion_data']:,}")
        logger.info(f"  Products with complete data (≥80%): {self.summary_stats['products_with_complete_data']:,}")
        
        logger.info("Data Quality:")
        logger.info(f"  Average completeness score: {self.summary_stats['avg_completeness_score']:.2f}")
        logger.info(f"  AI match rate: {(self.summary_stats['products_with_ai_matches']/self.summary_stats['total_products'])*100:.1f}%")
        logger.info(f"  Purchase data coverage: {(self.summary_stats['products_with_purchase_data']/self.summary_stats['total_products'])*100:.1f}%")
        logger.info(f"  Promotion data coverage: {(self.summary_stats['products_with_promotion_data']/self.summary_stats['total_products'])*100:.1f}%")
        
        logger.info("Business Metrics:")
        logger.info(f"  Total quantity purchased: {self.summary_stats['total_purchase_quantity']:,}")
        logger.info(f"  Total purchase frequency: {self.summary_stats['total_purchase_frequency']:,}")
        
        logger.info("Files created in 'standardized_data_output/' folder:")
        logger.info("  - standardized_data.csv (main dataset)")
        logger.info("  - summary_statistics.csv (summary stats)")
        logger.info("  - high_value_products.csv (products with both purchase & promotion data)")
        logger.info("  - ai_matched_products.csv (products with AI matches)")
    
    def get_standardized_data(self) -> Optional[pd.DataFrame]:
        """
        Get the standardized dataset.
        
        Returns:
            Optional[pd.DataFrame]: Standardized dataset or None if not created
        """
        return self.standardized_df.copy() if self.standardized_df is not None else None
    
    def get_summary_stats(self) -> Optional[Dict]:
        """
        Get summary statistics.
        
        Returns:
            Optional[Dict]: Summary statistics or None if not calculated
        """
        return self.summary_stats.copy() if self.summary_stats is not None else None
    
    def process_all(self) -> bool:
        """
        Execute the complete standardization process.
        
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Starting data standardization process...")
        
        # Load source data
        if not self.load_source_data():
            logger.error("Failed to load source data")
            return False
        
        # Create product mapping
        self.create_product_mapping()
        
        # Aggregate data
        self.aggregate_purchase_data()
        self.aggregate_promotion_data()
        
        # Create standardized dataset
        self.create_standardized_dataset()
        
        # Save results
        self.save_standardized_data()
        
        # Print summary
        self.print_summary_report()
        
        logger.info("Standardization completed successfully!")
        return True


def main():
    """Main function to execute the standardization process."""
    standardizer = DataStandardizer()
    success = standardizer.process_all()
    
    if success:
        logger.info("Data standardization process completed successfully!")
    else:
        logger.error("Data standardization process failed!")


if __name__ == "__main__":
    main()