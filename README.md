# ABC Pharmaceuticals Sales Assistant

Sales recommendation system combining Long Chau pharmacy data, purchase history, and promotions.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Google Gemini API key

### Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Go to https://aistudio.google.com/app/api-keys to get GEMINI_API_KEY
3. Create `.env` file with: `GEMINI_API_KEY=your_api_key_here`

### Run Pipeline (Optional)
```bash
# 1. Crawl product data (~10-15 min)
python longchau_crawler.py

# 2. Process promotions & purchase history
python process.py

# 3. AI product extraction (~5-10 min)
python gemini_product_extraction.py

# 4. Standardize data (~2-3 min)
python standardize_data.py
```
### Run Application
```bash
streamlit run app.py
```


Access at: `http://localhost:8501`

## 📁 Key Files
- `app.py` - Main Streamlit application
- `longchau_crawler.py` - Product data crawler
- `process.py` - Promotions & purchase history processor
- `gemini_product_extraction.py` - AI product matching
- `standardize_data.py` - Data standardization

## 🎯 Features
- Product search and recommendations
- Promotional offer detection
- Cross-sell opportunities
- Order analytics and insights

## 📊 Output
- `standardized_data_output/standardized_data.csv` - Complete product database
- `standardized_data_output/high_value_products.csv` - Products with promotions
- `standardized_data_output/ai_matched_products.csv` - AI-matched products

## 🚨 Troubleshooting
- **Module errors**: `pip install -r requirements.txt`
- **API errors**: Check `.env` file and API quota
- **File errors**: Ensure input files are in `info/` folder
- **Encoding errors**: Set `PYTHONIOENCODING=utf-8` (Windows)
