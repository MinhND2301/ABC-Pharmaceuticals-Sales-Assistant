import os
import re
import time
import json
import pandas as pd
import google.generativeai as genai
from pathlib import Path
from typing import List, Dict, Tuple
from dotenv import load_dotenv
load_dotenv()

PURCHASE_OUTPUT_FILE = 'processed_data/purchase_history.csv' 

class GeminiProductExtractor:
    def __init__(self, api_key: str = None):
        """Initialize Gemini API client"""
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key is None:
                raise ValueError("Please set GEMINI_API_KEY environment variable or pass api_key parameter.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    # --- OLD single-call method (kept for fallback) ---
    def extract_product_name(self, full_product_name: str) -> str:
        """Extract simplified product name using Gemini API (single call)"""
        try:
            prompt = f"""
            Extract only the main active ingredient/product name from this Vietnamese pharmacy product name.
            Remove dosage, brand names, manufacturer names, and packaging information.
            Return only the core product name in English.

            Examples:
            - "Paracetamol 500mg ABC Pharma" → "Paracetamol"
            - "Vitamin C 500mg sủi bọt ABC" → "Vitamin C"
            - "Thuốc ho Bảo Thanh" → "Cough Medicine"
            - "Omega-3 Fish Oil 1000mg" → "Omega-3"
            - "Vitamin	D3	1000IU	Softgel" → "Vitamin D3"
            - "Magie B6" → "Magnesium B6"

            Product name to extract: "{full_product_name}"
            Return only the extracted product name, nothing else:
            """
            response = self.model.generate_content(prompt)
            extracted = response.text.strip()
            extracted = re.sub(r'^["\']|["\']$', '', extracted)
            return extracted.split("\n")[0].strip()
        except Exception as e:
            print(f"Error extracting '{full_product_name}': {e}")
            return full_product_name

    def extract_product_names_batch(self, product_names: List[str], batch_size: int = 20, delay: float = 1.0) -> List[str]:
        """
        Extract simplified product names using Gemini API in batches.

        Args:
            product_names: List of full product names
            batch_size: Number of names per API call
            delay: Delay between API calls

        Returns:
            List of simplified names in the same order
        """
        all_extracted = []
        total_batches = (len(product_names) - 1) // batch_size + 1

        print(f"Extracting {len(product_names)} product names in {total_batches} batch(es)...")

        for batch_idx in range(0, len(product_names), batch_size):
            batch = product_names[batch_idx: batch_idx + batch_size]
            prompt = f"""
            You are a pharmacy text normalization assistant.
            For each of the following Vietnamese product names, extract only the main active ingredient
            or core product name in English. Remove dosage, manufacturer, and brand info.

            Return strictly as a JSON list of strings in the same order.

            Example:
            Input: ["Paracetamol 500mg ABC", "Vitamin C 500mg sủi bọt"]
            Output: ["Paracetamol", "Vitamin C"]

            Now process this list:
            {json.dumps(batch, ensure_ascii=False)}
            """

            try:
                response = self.model.generate_content(prompt)
                text = response.text.strip()

                # Try to extract JSON list
                json_text = re.search(r'\[.*\]', text, re.S)
                if json_text:
                    extracted = json.loads(json_text.group())
                else:
                    raise ValueError("No valid JSON found in response")

            except Exception as e:
                print(f"Error processing batch {batch_idx//batch_size + 1}: {e}")
                extracted = batch  # fallback: keep original

            all_extracted.extend(extracted)
            print(f"Processed batch {batch_idx//batch_size + 1}/{total_batches}")

            if batch_idx + batch_size < len(product_names):
                time.sleep(delay)

        return all_extracted

def load_databases():
    """Load all required databases"""
    print("Loading databases...")

    try:
        lc_products = pd.read_csv("longchau_data/longchau_products.csv")
        purchase_history = pd.read_csv("info/Lich_su_mua_hang_nha_thuoc.csv")
        promotions = pd.read_csv("promotions/promotions_structured.csv")

        print(f"Loaded {len(lc_products)} Long Chau products")
        print(f"Loaded {len(purchase_history)} purchase records")
        print(f"Loaded {len(promotions)} promotion records")

        return lc_products, purchase_history, promotions

    except Exception as e:
        print(f"Error loading databases: {e}")
        return None, None, None


def process_purchase_history_with_gemini(purchase_history: pd.DataFrame, extractor: GeminiProductExtractor):
    """Process purchase history using Gemini batch extraction"""
    print("\nProcessing purchase history with Gemini API...")

    unique_products = purchase_history["Sản phẩm"].dropna().unique().tolist()
    print(f"Found {len(unique_products)} unique products")

    extracted_names = extractor.extract_product_names_batch(unique_products, batch_size=30, delay=1.0)
    mapping = dict(zip(unique_products, extracted_names))

    purchase_history["AI_extracted_product"] = purchase_history["Sản phẩm"].map(mapping)
    return purchase_history, mapping


def process_promotions_with_gemini(promotions: pd.DataFrame, extractor: GeminiProductExtractor):
    """Process promotions using Gemini batch extraction"""
    print("\nProcessing promotions with Gemini API...")

    unique_products = promotions["san_pham"].dropna().unique().tolist()
    print(f"Found {len(unique_products)} unique promotion products")

    extracted_names = extractor.extract_product_names_batch(unique_products, batch_size=30, delay=1.0)
    mapping = dict(zip(unique_products, extracted_names))

    promotions["AI_extracted_product"] = promotions["san_pham"].map(mapping)
    return promotions, mapping


def compare_with_longchau(extracted_names: List[str], lc_products: pd.DataFrame):
    """Compare extracted names with Long Chau database"""
    print("\nComparing extracted names with Long Chau database...")

    lc_names = lc_products["name"].str.lower().tolist()
    results = []

    for name in extracted_names:
        name_lower = name.lower()
        matches = [n for n in lc_names if name_lower in n or any(w in n for w in name_lower.split() if len(w) > 2)]

        results.append({
            "extracted_name": name,
            "matches_count": len(matches),
            "top_matches": matches[:3]
        })

    return results


def generate_comparison_report(purchase_history, promotions, lc_products, extractor):
    """Generate detailed comparison report"""
    print("\nGenerating comparison report...")

    all_extracted = set(
        purchase_history["AI_extracted_product"].dropna().tolist()
        + promotions["AI_extracted_product"].dropna().tolist()
    )

    comparison = compare_with_longchau(list(all_extracted), lc_products)
    report = []

    for r in comparison:
        extracted = r["extracted_name"]
        purchase_count = (purchase_history["AI_extracted_product"] == extracted).sum()
        promo_count = (promotions["AI_extracted_product"] == extracted).sum()

        report.append({
            "AI_extracted_product": extracted,
            "purchase_count": purchase_count,
            "promotion_count": promo_count,
            "longchau_matches": r["matches_count"],
            "top_longchau_matches": "; ".join(r["top_matches"])
        })

    return pd.DataFrame(report)


def save_results(purchase_history, promotions, report):
    """Save all outputs to disk"""
    print("\nSaving results...")
    output_dir = Path("gemini_output")
    output_dir.mkdir(exist_ok=True)

    purchase_history.to_csv(output_dir / "purchase_history_with_ai_extraction.csv", index=False, encoding="utf-8")
    promotions.to_csv(output_dir / "promotions_with_ai_extraction.csv", index=False, encoding="utf-8")
    report.to_csv(output_dir / "ai_extraction_comparison_report.csv", index=False, encoding="utf-8")

    print(f"Results saved to '{output_dir}/'")
    print("\nSummary:")
    print(f"  Purchase records: {len(purchase_history)}")
    print(f"  Promotion records: {len(promotions)}")
    print(f"  Unique extracted names: {len(report)}")
    print(f"  Products with Long Chau matches: {len(report[report['longchau_matches'] > 0])}")

def main():
    print("Gemini API Product Extraction and Comparison")
    print("=" * 60)

    try:
        extractor = GeminiProductExtractor()
        lc_products, purchase_history, promotions = load_databases()
        if lc_products is None:
            return

        purchase_history, _ = process_purchase_history_with_gemini(purchase_history, extractor)
        promotions, _ = process_promotions_with_gemini(promotions, extractor)

        report = generate_comparison_report(purchase_history, promotions, lc_products, extractor)
        save_results(purchase_history, promotions, report)

        print("\nGemini extraction and comparison completed successfully!")
        print("Check the 'gemini_output' folder for results")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()