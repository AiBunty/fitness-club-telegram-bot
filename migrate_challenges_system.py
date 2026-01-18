"""
Migration script for Challenges System + Enhanced Check-in
Creates: challenges, challenge_participants, motivational_messages tables
Modifies: points_transactions (adds challenge_id column)
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from src.config import DATABASE_CONFIG
import sys

def run_migration():
    """Execute the challenges system migration"""
    conn = None
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(**DATABASE_CONFIG, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        print("✅ Connected successfully!")
        print("\n" + "="*60)
        
        # 1. Create challenges table
        print("\n📋 Creating 'challenges' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                challenge_id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                challenge_type VARCHAR(50) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                price DECIMAL(10, 2) DEFAULT 0,
                is_free BOOLEAN DEFAULT TRUE,
                status VARCHAR(20) DEFAULT 'scheduled',
                created_by INTEGER REFERENCES users(user_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                broadcast_sent BOOLEAN DEFAULT FALSE,
                
                CONSTRAINT chk_dates CHECK (end_date > start_date),
                CONSTRAINT chk_price CHECK (price >= 0),
                CONSTRAINT chk_status CHECK (status IN ('scheduled', 'active', 'completed', 'cancelled'))
            );
        """)
        
        # Create indexes for challenges
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_challenges_status 
            ON challenges(status);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_challenges_dates 
            ON challenges(start_date, end_date);
        """)
        print("✅ 'challenges' table created with indexes")
        
        # 2. Create challenge_participants table
        print("\n👥 Creating 'challenge_participants' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS challenge_participants (
                participation_id SERIAL PRIMARY KEY,
                challenge_id INTEGER REFERENCES challenges(challenge_id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approval_status VARCHAR(20) DEFAULT 'pending',
                payment_status VARCHAR(20) DEFAULT 'unpaid',
                receivable_id INTEGER REFERENCES accounts_receivable(receivable_id),
                total_points INTEGER DEFAULT 0,
                daily_progress JSONB DEFAULT '{}',
                status VARCHAR(20) DEFAULT 'active',
                
                CONSTRAINT chk_approval CHECK (approval_status IN ('pending', 'approved', 'rejected')),
                CONSTRAINT chk_payment CHECK (payment_status IN ('unpaid', 'partial', 'paid', 'na')),
                CONSTRAINT chk_participant_status CHECK (status IN ('active', 'withdrawn', 'completed')),
                UNIQUE(challenge_id, user_id)
            );
        """)
        
        # Create indexes for challenge_participants
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_participants_challenge 
            ON challenge_participants(challenge_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_participants_user 
            ON challenge_participants(user_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_participants_approval 
            ON challenge_participants(approval_status);
        """)
        print("✅ 'challenge_participants' table created with indexes")
        
        # 3. Create motivational_messages table
        print("\n💬 Creating 'motivational_messages' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS motivational_messages (
                id SERIAL PRIMARY KEY,
                message_text TEXT NOT NULL,
                category VARCHAR(50) DEFAULT 'checkin',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_count INTEGER DEFAULT 0
            );
        """)
        
        # Create index for fast random selection
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_motivational_active 
            ON motivational_messages(is_active) 
            WHERE is_active = TRUE;
        """)
        print("✅ 'motivational_messages' table created")
        
        # 4. Populate motivational messages with 15 defaults
        print("\n💬 Populating motivational messages...")
        
        # Check if messages already exist
        cursor.execute("SELECT COUNT(*) as count FROM motivational_messages")
        result = cursor.fetchone()
        
        if result['count'] == 0:
            messages = [
                "🔥 Great job! You showed up today!",
                "💪 Another step towards your goals!",
                "⭐ Consistency is key - you're doing it!",
                "🚀 Keep this momentum going!",
                "🎯 You're building great habits!",
                "✨ Your dedication is inspiring!",
                "👏 Way to prioritize your health!",
                "🏆 Champions show up even when it's tough!",
                "💯 You're on fire this week!",
                "🌟 Every workout counts - nice work!",
                "⚡ You're stronger than you think!",
                "🎉 Crushing it! Keep going!",
                "💪 That's the spirit! Well done!",
                "🔥 You're unstoppable today!",
                "✅ One more day closer to your best self!"
            ]
            
            for message in messages:
                cursor.execute("""
                    INSERT INTO motivational_messages (message_text, category)
                    VALUES (%s, 'checkin')
                """, (message,))
            
            print(f"✅ Inserted {len(messages)} motivational messages")
        else:
            print(f"ℹ️  Motivational messages already exist ({result['count']} messages)")
        
        # 5. Add challenge_id column to points_transactions
        print("\n🎯 Modifying 'points_transactions' table...")
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'points_transactions' 
            AND column_name = 'challenge_id'
        """)
        
        if cursor.fetchone() is None:
            cursor.execute("""
                ALTER TABLE points_transactions 
                ADD COLUMN challenge_id INTEGER REFERENCES challenges(challenge_id);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_points_challenge 
                ON points_transactions(challenge_id);
            """)
            print("✅ Added 'challenge_id' column with index to points_transactions")
        else:
            print("ℹ️  'challenge_id' column already exists in points_transactions")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "="*60)
        print("\n✅ Challenges System migration completed successfully!")
        print("\n📊 Summary:")
        print("   • challenges table created")
        print("   • challenge_participants table created")
        print("   • motivational_messages table created (15 messages)")
        print("   • points_transactions.challenge_id column added")
        print("   • All indexes created")
        
        # Verify table creation
        print("\n🔍 Verifying tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name IN ('challenges', 'challenge_participants', 'motivational_messages')
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        print(f"\n✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"   ✓ {table['table_name']}")
        
        # Count motivational messages
        cursor.execute("SELECT COUNT(*) as count FROM motivational_messages WHERE is_active = TRUE")
        msg_count = cursor.fetchone()
        print(f"\n💬 Active motivational messages: {msg_count['count']}")
        
        cursor.close()
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
        
    finally:
        if conn:
            conn.close()
            print("\n🔌 Database connection closed")

if __name__ == "__main__":
    print("="*60)
    print("CHALLENGES SYSTEM MIGRATION")
    print("="*60)
    
    response = input("\n⚠️  This will create new tables and modify existing ones.\nContinue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        run_migration()
    else:
        print("\n❌ Migration cancelled")
        sys.exit(0)
