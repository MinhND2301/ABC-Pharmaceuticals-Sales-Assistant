import fitz  # PyMuPDF
import pandas as pd
import re
import os
import logging
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('process_promotions.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

PROMOTIONS_FILE_PATH = "info/Thong_bao_chuong_trinh_ban_hang_09_2025.pdf"
PURCHASE_HISTORY_FILE_PATH = "info/Lich_su_mua_hang_nha_thuoc.xlsx"

OUTPUT_DIR = "promotions_and_purchase_history"
PROMOTIONS_OUTPUT_FILE = "promotions.csv"
PURCHASE_HISTORY_OUTPUT_FILE = "purchase_history.csv"

class PromotionProcessor:
    """
    Class to process and manage promotion data from multiple sources.
    """
    HARDCODED_PROMOTIONS = [
        {
            "nhom_san_pham": "Vitamin & Khoáng chất",
            "san_pham": "Vitamin C 500mg sủi bọt ABC",
            "chuong_trinh": "Giảm 15% giá bán lẻ cho mỗi hộp trong tháng 09/2025"
        },
        {
            "nhom_san_pham": "Vitamin & Khoáng chất",
            "san_pham": "Vitamin D3 1000IU Softgel",
            "chuong_trinh": "Mua 10 tặng 1, áp dụng cho đơn hàng từ 3 triệu trở lên"
        },
        {
            "nhom_san_pham": "Thuốc giảm đau - hạ sốt",
            "san_pham": "Paracetamol 500mg, Efferalgan",
            "chuong_trinh": "Mua 10 tặng 1 hộp, áp dụng cho đơn hàng từ 2 triệu trở lên"
        },
        {
            "nhom_san_pham": "Thuốc ho & cảm lạnh",
            "san_pham": "Siro ho Prospan, Thuốc ho Bảo Thanh",
            "chuong_trinh": "Chiết khấu thêm 5% cho đơn hàng từ 100 hộp trở lên"
        },
        {
            "nhom_san_pham": "Thực phẩm chức năng",
            "san_pham": "Omega-3 Fish Oil, Collagen Plus",
            "chuong_trinh": "Mua 5 tặng 1 + tặng kèm lịch 2026 cho đơn từ 3 triệu"
        }
    ]
    
    def __init__(self):
        """Initialize the PromotionProcessor."""
        self.pdf_promotions: Optional[pd.DataFrame] = None
        self.hardcoded_promotions: pd.DataFrame = pd.DataFrame(self.HARDCODED_PROMOTIONS)
        self.combined_promotions: Optional[pd.DataFrame] = None
        self.purchase_history: Optional[pd.DataFrame] = None
    
    def extract_promotions_from_pdf(self, pdf_path: str) -> Optional[pd.DataFrame]:
        """
        Read PDF promotion notification file and extract information into table format.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            Optional[pd.DataFrame]: DataFrame containing promotion data or None if error
        """
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"Error opening PDF file: {e}")
            logger.error("Please ensure the PDF file exists and is readable.")
            return None

        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        promotions = self._parse_pdf_text(full_text)
        
        if not promotions:
            logger.warning("Could not extract automatically. Please check the PDF file structure.")
            return None

        self.pdf_promotions = pd.DataFrame(promotions)
        return self.pdf_promotions
    
    def _parse_pdf_text(self, text: str) -> List[Dict[str, str]]:
        """
        Parse text from PDF to extract promotion information.
        
        Args:
            text (str): Text read from PDF
            
        Returns:
            List[Dict[str, str]]: List of dictionaries containing promotion information
        """
        promotions = []
        
        pattern = re.compile(r"^\d+\s+(.+?)\s{2,}(.+)$", re.MULTILINE)
        matches = pattern.findall(text)

        for match in matches:
            product_name = match[0].replace('\n', ' ').strip()
            description = match[1].replace('\n', ' ').strip()
            
            promotions.append({
                "nhom_san_pham": "Khác",  
                "san_pham": product_name,
                "chuong_trinh": description
            })
        
        return promotions
    
    def convert_excel_to_csv(self, excel_path: str = PURCHASE_HISTORY_FILE_PATH, 
                           output_dir: str = OUTPUT_DIR, 
                           output_file: str = PURCHASE_HISTORY_OUTPUT_FILE) -> bool:
        """
        Convert Excel file to CSV format.
        
        Args:
            excel_path (str): Path to the Excel file
            output_dir (str): Output directory for CSV file
            output_file (str): Output CSV file name
            
        Returns:
            bool: True if conversion successful, False if error
        """
        try:
            # Check if Excel file exists
            if not os.path.exists(excel_path):
                logger.error(f"Excel file not found: {excel_path}")
                return False
            
            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                logger.info(f"Creating directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            # Construct full CSV path
            csv_path = os.path.join(output_dir, output_file)
            
            # Read Excel file
            logger.info(f"Reading Excel file: {excel_path}")
            df = pd.read_excel(excel_path)
            
            # Save as CSV
            logger.info(f"Converting to CSV: {csv_path}")
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            # Store the data for later use
            self.purchase_history = df
            
            logger.info(f"Conversion successful! CSV file saved at: {csv_path}")
            logger.info(f"Number of rows: {len(df)}")
            logger.info(f"Columns: {list(df.columns)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error converting Excel to CSV: {e}")
            return False
    
    def get_purchase_history(self) -> Optional[pd.DataFrame]:
        """
        Get purchase history data.
        
        Returns:
            Optional[pd.DataFrame]: DataFrame containing purchase history or None if not loaded
        """
        return self.purchase_history.copy() if self.purchase_history is not None else None
    
    def get_hardcoded_promotions(self) -> pd.DataFrame:
        """
        Get hard-coded promotion data.
        
        Returns:
            pd.DataFrame: DataFrame containing hard-coded promotion data
        """
        return self.hardcoded_promotions.copy()
    
    def combine_promotions(self) -> pd.DataFrame:
        """
        Combine promotion data from PDF and hard-coded data.
        
        Returns:
            pd.DataFrame: DataFrame containing all promotion data
        """
        all_promotions = []
        if self.pdf_promotions is not None:
            all_promotions.extend(self.pdf_promotions.to_dict('records'))
        all_promotions.extend(self.HARDCODED_PROMOTIONS)
        
        self.combined_promotions = pd.DataFrame(all_promotions)
        return self.combined_promotions
    
    def save_promotions_to_csv(self, output_dir: str = OUTPUT_DIR, 
                              output_file: str = PROMOTIONS_OUTPUT_FILE) -> bool:
        """
        Save promotion data to CSV file.
        
        Args:
            output_dir (str): Output directory
            output_file (str): Output file name
            
        Returns:
            bool: True if save successful, False if error
        """
        if self.combined_promotions is None:
            logger.warning("No data to save. Please call combine_promotions() first.")
            return False
        
        try:
            # Create output directory if it doesn't exist
            if not os.path.exists(output_dir):
                logger.info(f"Creating directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            # Construct full path
            output_path = os.path.join(output_dir, output_file)
            
            self.combined_promotions.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"Promotions data saved to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving promotions file: {e}")
            return False
    
    def get_summary(self) -> Dict[str, int]:
        """
        Get summary statistics about promotion data.
        
        Returns:
            Dict[str, int]: Dictionary containing statistics
        """
        summary = {
            "pdf_promotions": len(self.pdf_promotions) if self.pdf_promotions is not None else 0,
            "hardcoded_promotions": len(self.HARDCODED_PROMOTIONS),
            "total_promotions": len(self.combined_promotions) if self.combined_promotions is not None else 0,
            "purchase_history_rows": len(self.purchase_history) if self.purchase_history is not None else 0
        }
        return summary
    
    def print_preview(self, n_rows: int = 5) -> None:
        """
        Print preview of promotion data.
        
        Args:
            n_rows (int): Number of rows to display
        """
        if self.combined_promotions is None:
            logger.warning("No data to display.")
            return
        
        logger.info(f"Preview of first {n_rows} promotions:")
        logger.info(f"\n{self.combined_promotions.head(n_rows).to_string()}")
        
        if self.purchase_history is not None:
            logger.info(f"Preview of first {n_rows} purchase history records:")
            logger.info(f"\n{self.purchase_history.head(n_rows).to_string()}")


def main():
    """Main function to execute the program."""
    
    logger.info("Starting promotion processing...")
    processor = PromotionProcessor()

    # Convert Excel to CSV first
    logger.info("Converting Excel to CSV...")
    excel_conversion_success = processor.convert_excel_to_csv()
    
    if excel_conversion_success:
        logger.info("SUCCESS: Excel to CSV conversion completed!")
    else:
        logger.error("ERROR: Failed to convert Excel to CSV.")
    
    # Process promotion data
    logger.info("Processing promotion data...")
    pdf_data = processor.extract_promotions_from_pdf(PROMOTIONS_FILE_PATH)
    
    if pdf_data is not None:
        logger.info(f"Successfully extracted {len(pdf_data)} promotions from PDF.")
    else:
        logger.warning("Could not extract data from PDF.")
    
    # Add hardcoded promotions
    hardcoded_data = processor.get_hardcoded_promotions()
    logger.info(f"Added {len(hardcoded_data)} hard-coded promotions.")
    
    # Combine all promotion data
    logger.info("Combining all promotion data...")
    combined_data = processor.combine_promotions()
    
    # Get and display summary
    summary = processor.get_summary()
    logger.info("SUMMARY:")
    logger.info(f"- PDF promotions: {summary['pdf_promotions']}")
    logger.info(f"- Hard-coded promotions: {summary['hardcoded_promotions']}")
    logger.info(f"- Total promotions: {summary['total_promotions']}")
    logger.info(f"- Purchase history records: {summary['purchase_history_rows']}")

    # Save promotions to CSV
    if processor.save_promotions_to_csv():
        logger.info("Processing completed successfully!")
        processor.print_preview()
    else:
        logger.error("ERROR: Failed to save promotions data.")


if __name__ == "__main__":
    main()