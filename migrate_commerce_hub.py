"""
Migration: Add Commerce Hub tables for subscription plans, PT plans, events, store products, and audit log
"""

import psycopg2
from src.database.connection import DatabaseConnection, execute_query

def migrate():
    """Create commerce hub tables"""
    db = DatabaseConnection()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        # Create subscription_plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscription_plans (
                plan_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                duration_days INT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'active',
                ar_enabled BOOLEAN DEFAULT TRUE,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)
        print("✓ Created subscription_plans table")
        
        # Create pt_subscriptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pt_subscriptions (
                pt_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                duration_days INT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'active',
                ar_enabled BOOLEAN DEFAULT TRUE,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)
        print("✓ Created pt_subscriptions table")
        
        # Create one_day_events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS one_day_events (
                event_id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                event_date DATE NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                description TEXT,
                max_attendees INT,
                current_attendees INT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                ar_enabled BOOLEAN DEFAULT TRUE,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)
        print("✓ Created one_day_events table")
        
        # Create store_products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS store_products (
                product_id SERIAL PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                mrp DECIMAL(10, 2) NOT NULL,
                discount_percent DECIMAL(5, 2) DEFAULT 0,
                final_price DECIMAL(10, 2) NOT NULL,
                stock INT DEFAULT 0,
                status VARCHAR(20) DEFAULT 'active',
                ar_enabled BOOLEAN DEFAULT FALSE,
                created_by INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)
        print("✓ Created store_products table")
        
        # Create admin_audit_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit_log (
                log_id SERIAL PRIMARY KEY,
                admin_id INT NOT NULL,
                entity_type VARCHAR(50) NOT NULL,
                entity_id INT,
                action VARCHAR(50) NOT NULL,
                old_value TEXT,
                new_value TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        print("✓ Created admin_audit_log table")
        
        # Create user_product_orders table (for tracking user orders of store products)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_product_orders (
                order_id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                product_id INT NOT NULL,
                quantity INT DEFAULT 1,
                unit_price DECIMAL(10, 2) NOT NULL,
                total_amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES store_products(product_id) ON DELETE CASCADE
            )
        """)
        print("✓ Created user_product_orders table")
        
        # Create user_event_registrations table (for one-day events)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_event_registrations (
                registration_id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                event_id INT NOT NULL,
                status VARCHAR(20) DEFAULT 'registered',
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (event_id) REFERENCES one_day_events(event_id) ON DELETE CASCADE,
                UNIQUE(user_id, event_id)
            )
        """)
        print("✓ Created user_event_registrations table")
        
        conn.commit()
        print("\n✅ Commerce Hub migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
