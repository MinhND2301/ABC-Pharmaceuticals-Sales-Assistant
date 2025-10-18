import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from pathlib import Path
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# File paths
STANDARDIZED_DATA_PATH = "standardized_data_output/standardized_data.csv"
HIGH_VALUE_PRODUCTS_PATH = "standardized_data_output/high_value_products.csv"
MATCHED_PRODUCTS_PATH = "standardized_data_output/ai_matched_products.csv"

class SalesAssistant:
    """
    Sales Assistant for ABC Pharmaceuticals to help optimize pharmacy orders.
    """
    
    def __init__(self):
        """Initialize the Sales Assistant."""
        self.standardized_data: Optional[pd.DataFrame] = None
        self.high_value_products: Optional[pd.DataFrame] = None
        self.matched_products: Optional[pd.DataFrame] = None
        self.promotions_data: Dict[str, str] = {}
        self.cross_sell_rules: Dict[str, List[str]] = {}
        
    def load_data(self) -> bool:
        """
        Load all required data files.
        
        Returns:
            bool: True if all data loaded successfully, False otherwise
        """
        try:
            # Load standardized data
            if Path(STANDARDIZED_DATA_PATH).exists():
                self.standardized_data = pd.read_csv(STANDARDIZED_DATA_PATH)
                logger.info(f"Loaded {len(self.standardized_data)} standardized products")
            else:
                logger.error(f"Standardized data file not found: {STANDARDIZED_DATA_PATH}")
                return False
            
            # Load high value products
            if Path(HIGH_VALUE_PRODUCTS_PATH).exists():
                self.high_value_products = pd.read_csv(HIGH_VALUE_PRODUCTS_PATH)
                logger.info(f"Loaded {len(self.high_value_products)} high-value products")
            
            # Load matched products
            if Path(MATCHED_PRODUCTS_PATH).exists():
                self.matched_products = pd.read_csv(MATCHED_PRODUCTS_PATH)
                logger.info(f"Loaded {len(self.matched_products)} matched products")
            
            # Build promotions data
            self._build_promotions_data()
            
            # Build cross-sell rules
            self._build_cross_sell_rules()
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return False
    
    def _build_promotions_data(self) -> None:
        """Build promotions data from standardized data."""
        if self.standardized_data is None:
            return
        
        # Create promotions mapping from products with promotion data
        promo_products = self.standardized_data[
            (self.standardized_data['has_promotion_data'] == True) & 
            (self.standardized_data['promotion_programs'].notna()) &
            (self.standardized_data['promotion_programs'] != '')
        ]
        
        for _, row in promo_products.iterrows():
            product_name = row['product_name']
            promotion_programs = row['promotion_programs']
            promotion_categories = row['promotion_categories']
            
            # Create promotion description
            promo_desc = f"**{promotion_programs}**"
            if pd.notna(promotion_categories) and promotion_categories != '':
                promo_desc += f" (Category: {promotion_categories})"
            
            self.promotions_data[product_name] = promo_desc
        
        logger.info(f"Built promotions data for {len(self.promotions_data)} products")
    
    def _build_cross_sell_rules(self) -> None:
        """Build cross-sell rules based on product categories and purchase patterns."""
        if self.standardized_data is None:
            return
        
        # Define category-based cross-sell rules
        category_rules = {
            'Vitamin & Khoáng chất': ['Vitamin C', 'Vitamin D', 'Multivitamin', 'Omega-3'],
            'Thuốc giảm đau - hạ sốt': ['Paracetamol', 'Ibuprofen', 'Aspirin'],
            'Thuốc ho & cảm lạnh': ['Siro ho', 'Thuốc ho', 'Cảm lạnh'],
            'Thực phẩm chức năng': ['Collagen', 'Omega-3', 'Probiotics', 'Glucosamine'],
            'Thuốc tiêu hóa': ['Men tiêu hóa', 'Probiotics', 'Thuốc đau dạ dày'],
            'Thuốc tim mạch': ['Omega-3', 'Coenzyme Q10', 'Magnesium'],
            'Thuốc xương khớp': ['Glucosamine', 'Chondroitin', 'Calcium', 'Vitamin D']
        }
        
        # Build cross-sell rules for each product
        for _, row in self.standardized_data.iterrows():
            product_name = row['product_name']
            category = row['category']
            
            # Get category-based suggestions
            if category in category_rules:
                suggestions = []
                for suggestion in category_rules[category]:
                    # Find products matching the suggestion
                    matching_products = self.standardized_data[
                        self.standardized_data['product_name'].str.contains(suggestion, case=False, na=False)
                    ]['product_name'].tolist()
                    
                    # Add up to 3 matching products
                    suggestions.extend(matching_products[:3])
                
                # Remove the product itself and duplicates
                suggestions = list(set([s for s in suggestions if s != product_name]))
                self.cross_sell_rules[product_name] = suggestions[:5]  # Limit to 5 suggestions
        
        logger.info(f"Built cross-sell rules for {len(self.cross_sell_rules)} products")
    
    def identify_promotions(self, current_order: List[str]) -> Dict[str, str]:
        """
        Identify promotions for products in the current order.
        
        Args:
            current_order: List of product names in the shopping cart
            
        Returns:
            Dict mapping product names to their promotion details
        """
        promotions = {}
        
        for product in current_order:
            # Direct match
            if product in self.promotions_data:
                promotions[product] = self.promotions_data[product]
            else:
                # Fuzzy match - look for similar product names
                for promo_product, promo_desc in self.promotions_data.items():
                    if self._is_similar_product(product, promo_product):
                        promotions[product] = f"{promo_desc} (Similar to: {promo_product})"
                        break
        
        return promotions
    
    def identify_cross_sell_opportunities(self, current_order: List[str]) -> Dict[str, List[str]]:
        """
        Identify cross-sell opportunities for products in the current order.
        
        Args:
            current_order: List of product names in the shopping cart
            
        Returns:
            Dict mapping product names to list of suggested cross-sell products
        """
        cross_sell_opportunities = {}
        
        for product in current_order:
            suggestions = []
            
            # Direct rule match
            if product in self.cross_sell_rules:
                suggestions.extend(self.cross_sell_rules[product])
            
            # Fuzzy match for similar products
            for rule_product, rule_suggestions in self.cross_sell_rules.items():
                if self._is_similar_product(product, rule_product):
                    suggestions.extend(rule_suggestions)
            
            # Remove products already in the order and duplicates
            suggestions = list(set([s for s in suggestions if s not in current_order]))
            
            # Limit to top 5 suggestions
            cross_sell_opportunities[product] = suggestions[:5]
        
        return cross_sell_opportunities
    
    def _is_similar_product(self, product1: str, product2: str) -> bool:
        """
        Check if two products are similar based on name similarity.
        
        Args:
            product1: First product name
            product2: Second product name
            
        Returns:
            bool: True if products are similar
        """
        # Simple similarity check - can be enhanced with more sophisticated algorithms
        p1_lower = product1.lower()
        p2_lower = product2.lower()
        
        # Check if one product name contains the other
        if p1_lower in p2_lower or p2_lower in p1_lower:
            return True
        
        # Check for common keywords
        common_keywords = ['vitamin', 'paracetamol', 'ibuprofen', 'omega', 'collagen', 'probiotics']
        for keyword in common_keywords:
            if keyword in p1_lower and keyword in p2_lower:
                return True
        
        return False
    
    def generate_recommendations(self, current_order: List[str]) -> Dict:
        """
        Generate comprehensive recommendations for the current order.
        
        Args:
            current_order: List of product names in the shopping cart
            
        Returns:
            Dict containing all recommendations
        """
        if not current_order:
            return {
                'promotions': {},
                'cross_sell_opportunities': {},
                'summary': 'No products in current order.'
            }
        
        # Identify promotions
        promotions = self.identify_promotions(current_order)
        
        # Identify cross-sell opportunities
        cross_sell_opportunities = self.identify_cross_sell_opportunities(current_order)
        
        # Create summary
        total_promotions = len(promotions)
        total_cross_sell = sum(len(suggestions) for suggestions in cross_sell_opportunities.values())
        
        summary = f"Found {total_promotions} promotional offers and {total_cross_sell} cross-sell opportunities for {len(current_order)} products in your order."
        
        return {
            'promotions': promotions,
            'cross_sell_opportunities': cross_sell_opportunities,
            'summary': summary
        }

def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="ABC Pharmaceuticals - Sales Assistant",
        layout="wide"
    )
    
    st.title("ABC Pharmaceuticals - Sales Assistant")
    st.markdown("---")
    
    # Initialize the Sales Assistant
    if 'assistant' not in st.session_state:
        st.session_state.assistant = SalesAssistant()
        
        # Load data
        with st.spinner("Loading data..."):
            if not st.session_state.assistant.load_data():
                st.error("Failed to load data. Please check if the standardized data files exist.")
                st.stop()
    
    # Sidebar for current order
    st.sidebar.header("Current Order")
    
    # Product input
    st.sidebar.subheader("Add Products to Order")
    
    # Text input for adding products
    new_product = st.sidebar.text_input(
        "Enter product name:",
        placeholder="e.g., Vitamin C 500mg, Paracetamol 500mg",
        help="Type the product name and press Enter to add to order"
    )
    
    # Initialize selected_products in session state if not exists
    if 'selected_products' not in st.session_state:
        st.session_state.selected_products = []
    
    # Add product button
    if st.sidebar.button("Add Product") and new_product.strip():
        if new_product.strip() not in st.session_state.selected_products:
            st.session_state.selected_products.append(new_product.strip())
            st.sidebar.success(f"Added: {new_product.strip()}")
        else:
            st.sidebar.warning("Product already in order")
    
    # Clear all products button
    if st.sidebar.button("Clear All Products"):
        st.session_state.selected_products = []
        st.sidebar.info("Order cleared")
    
    # Display current order
    selected_products = st.session_state.selected_products
    if selected_products:
        st.sidebar.subheader("Current Order:")
        for i, product in enumerate(selected_products, 1):
            col1, col2 = st.sidebar.columns([4, 1])
            with col1:
                st.sidebar.write(f"{i}. {product}")
            with col2:
                if st.sidebar.button("Remove", key=f"remove_{i}"):
                    st.session_state.selected_products.remove(product)
                    st.rerun()
    else:
        st.sidebar.info("No products in order. Add products using the text input above.")
    
    # Main content area
    if selected_products:
        # Generate recommendations
        with st.spinner("Generating recommendations..."):
            recommendations = st.session_state.assistant.generate_recommendations(selected_products)
        
        # Display summary
        st.success(recommendations['summary'])
        
        # Create two columns for recommendations
        col1, col2 = st.columns(2)
        
        # Promotions section
        with col1:
            st.header("Promotional Offers")
            if recommendations['promotions']:
                for product, promotion in recommendations['promotions'].items():
                    with st.expander(f"{product}", expanded=True):
                        st.markdown(promotion)
            else:
                st.info("No promotional offers found for the current order.")
        
        # Cross-sell opportunities section
        with col2:
            st.header("Cross-Sell Opportunities")
            if recommendations['cross_sell_opportunities']:
                for product, suggestions in recommendations['cross_sell_opportunities'].items():
                    if suggestions:  # Only show if there are suggestions
                        with st.expander(f"Customers who buy {product} also buy:", expanded=True):
                            for suggestion in suggestions:
                                st.write(f"• {suggestion}")
            else:
                st.info("No cross-sell opportunities found for the current order.")
        
        # Additional insights
        st.header("Order Insights")
        
        # Calculate order value and insights
        if st.session_state.assistant.standardized_data is not None:
            order_data = st.session_state.assistant.standardized_data[
                st.session_state.assistant.standardized_data['product_name'].isin(selected_products)
            ]
            
            if not order_data.empty:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Products", len(selected_products))
                
                with col2:
                    total_price = order_data['price'].sum()
                    st.metric("Estimated Order Value", f"₫{total_price:,.0f}")
                
                with col3:
                    categories = order_data['category'].nunique()
                    st.metric("Product Categories", categories)
                
                with col4:
                    high_value_count = len(order_data[order_data['has_purchase_data'] == True])
                    st.metric("High-Value Products", high_value_count)
                
                # Product details table
                st.subheader("Order Details")
                display_columns = ['product_name', 'brand', 'category', 'price', 'has_purchase_data', 'has_promotion_data']
                st.dataframe(
                    order_data[display_columns].rename(columns={
                        'product_name': 'Product Name',
                        'brand': 'Brand',
                        'category': 'Category',
                        'price': 'Price (₫)',
                        'has_purchase_data': 'Has Purchase Data',
                        'has_promotion_data': 'Has Promotion Data'
                    }),
                    use_container_width=True
                )
    
    else:
        # Welcome message when no products are selected
        st.info("Welcome to ABC Pharmaceuticals Sales Assistant!")
        st.markdown("""
        ### How to use this tool:
        1. **Add Products**: Type product names in the sidebar text input and click "Add Product"
        2. **View Recommendations**: Get promotional offers and cross-sell opportunities
        3. **Optimize Orders**: Use insights to maximize sales and customer satisfaction
        
        ### Features:
        - **Promotional Offers**: Find current promotions for products in your order
        - **Cross-Sell Opportunities**: Discover products customers are likely to buy together
        - **Order Insights**: Analyze order value, categories, and product performance
        - **Data-Driven**: Based on real purchase history and promotion data
        
        ### Example Product Names:
        - Vitamin C 500mg sủi bọt ABC
        - Paracetamol 500mg ABC Pharma
        - Omega-3 Fish Oil
        - Collagen Plus
        - Probiotics
        """)
        
        # Show some statistics
        if st.session_state.assistant.standardized_data is not None:
            st.subheader("Available Data Overview")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Products", len(st.session_state.assistant.standardized_data))
            
            with col2:
                promo_count = len(st.session_state.assistant.promotions_data)
                st.metric("Products with Promotions", promo_count)
            
            with col3:
                cross_sell_count = len(st.session_state.assistant.cross_sell_rules)
                st.metric("Products with Cross-Sell Rules", cross_sell_count)

if __name__ == "__main__":
    main()
