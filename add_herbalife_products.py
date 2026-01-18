"""
Add Herbalife Demo Products to Store
Inserts 20 sample Herbalife products for demonstration
"""

import psycopg2
from src.config import DATABASE_CONFIG

def add_herbalife_products():
    """Add 20 Herbalife demo products"""
    conn = None
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        cursor = conn.cursor()
        
        print("🛒 Adding 20 Herbalife Demo Products...")
        
        # Check if store_products table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'store_products'
            )
        """)
        
        if not cursor.fetchone()[0]:
            print("\n  Creating store_products table...")
            cursor.execute("""
                CREATE TABLE store_products (
                    product_id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    category VARCHAR(100) DEFAULT 'General',
                    mrp DECIMAL(10,2) NOT NULL,
                    discount_percent DECIMAL(5,2) DEFAULT 0,
                    final_price DECIMAL(10,2) NOT NULL,
                    stock INTEGER DEFAULT 0,
                    ar_enabled BOOLEAN DEFAULT TRUE,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("  ✅ store_products table created")
        
        # Clear existing products (for demo reset)
        cursor.execute("DELETE FROM store_products")
        print("  🗑️  Cleared existing products")
        
        # Herbalife Products Data
        products = [
            # Nutrition Shakes
            ("Formula 1 Nutritional Shake - Chocolate", "Healthy meal replacement shake with protein, fiber, and essential nutrients", "Nutrition Shakes", 2400, 15, 2040, 50),
            ("Formula 1 Nutritional Shake - Vanilla", "Delicious vanilla flavor meal replacement with vitamins and minerals", "Nutrition Shakes", 2400, 15, 2040, 45),
            ("Formula 1 Nutritional Shake - Strawberry", "Berry blast meal replacement for weight management", "Nutrition Shakes", 2400, 15, 2040, 40),
            ("Formula 1 Nutritional Shake - Cookies & Cream", "Indulgent cookies and cream flavor with balanced nutrition", "Nutrition Shakes", 2400, 15, 2040, 35),
            
            # Protein Products
            ("Personalized Protein Powder", "Soy and whey protein blend for muscle support", "Protein", 2200, 10, 1980, 30),
            ("Protein Drink Mix - Vanilla", "High-quality protein drink for post-workout recovery", "Protein", 2500, 10, 2250, 25),
            ("Protein Bars - Chocolate Peanut", "Convenient protein bar with 10g protein per serving", "Protein", 1500, 20, 1200, 60),
            ("Protein Bars - Vanilla Almond", "Nutritious protein bar for on-the-go", "Protein", 1500, 20, 1200, 55),
            
            # Herbal Tea & Aloe
            ("Herbal Tea Concentrate - Original", "Refreshing herbal tea with caffeine and antioxidants", "Beverages", 1800, 10, 1620, 40),
            ("Herbal Tea Concentrate - Lemon", "Zesty lemon flavor energizing tea", "Beverages", 1800, 10, 1620, 38),
            ("Herbal Tea Concentrate - Peach", "Fruity peach flavor herbal tea", "Beverages", 1800, 10, 1620, 35),
            ("Herbal Aloe Concentrate - Mango", "Soothing aloe vera drink for digestive health", "Beverages", 1600, 15, 1360, 30),
            ("Herbal Aloe Concentrate - Mandarin", "Citrus-flavored aloe for digestive support", "Beverages", 1600, 15, 1360, 28),
            
            # Supplements
            ("Cell-U-Loss", "Advanced wellness supplement for healthy fluid balance", "Supplements", 1400, 10, 1260, 20),
            ("Total Control", "Dietary supplement with caffeine and green tea", "Supplements", 1800, 10, 1620, 18),
            ("Multivitamin Complex - Men", "Comprehensive multivitamin for men's health", "Supplements", 1200, 15, 1020, 25),
            ("Multivitamin Complex - Women", "Complete multivitamin for women's wellness", "Supplements", 1200, 15, 1020, 23),
            
            # Snacks & Nutrition
            ("Roasted Soy Nuts - Salted", "High-protein crunchy snack", "Snacks", 450, 10, 405, 40),
            ("Protein Bites - Chocolate Mint", "Delicious protein-rich snack bites", "Snacks", 550, 10, 495, 35),
            ("Niteworks", "L-arginine supplement for cardiovascular support", "Supplements", 3200, 10, 2880, 15),
        ]
        
        # Insert products
        inserted = 0
        for name, desc, category, mrp, discount, final_price, stock in products:
            cursor.execute("""
                INSERT INTO store_products 
                (name, description, category, mrp, discount_percent, final_price, stock, ar_enabled, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, 'active')
            """, (name, desc, category, mrp, discount, final_price, stock))
            inserted += 1
        
        conn.commit()
        
        print(f"\n✅ Successfully added {inserted} Herbalife products!\n")
        
        # Show summary by category
        cursor.execute("""
            SELECT category, COUNT(*), SUM(stock), 
                   MIN(final_price), MAX(final_price)
            FROM store_products
            WHERE status = 'active'
            GROUP BY category
            ORDER BY category
        """)
        
        print("📊 Product Summary:")
        print("-" * 70)
        for row in cursor.fetchall():
            category, count, total_stock, min_price, max_price = row
            print(f"{category:20s} | {count:2d} products | Stock: {total_stock:3d} | Rs {min_price:,.0f} - Rs {max_price:,.0f}")
        print("-" * 70)
        
        # Show total
        cursor.execute("""
            SELECT COUNT(*), SUM(stock), SUM(final_price * stock)
            FROM store_products WHERE status = 'active'
        """)
        total_products, total_stock, total_value = cursor.fetchone()
        print(f"\nTotal: {total_products} products | {total_stock} items | Inventory Value: Rs {total_value:,.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    add_herbalife_products()
