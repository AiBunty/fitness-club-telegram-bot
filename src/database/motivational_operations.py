"""
Motivational Messages Operations
Handles fetching and rotating motivational messages for check-in approvals
"""

from src.database.connection import DatabaseConnection

def get_random_motivational_message() -> str:
    """
    Get a random motivational message from the database
    Increments usage counter for tracking
    
    Returns:
        str: Motivational message text
    """
    try:
        db = DatabaseConnection()
        
        # Get random active message
        query = """
            SELECT id, message_text 
            FROM motivational_messages 
            WHERE is_active = TRUE 
            ORDER BY RANDOM() 
            LIMIT 1
        """
        
        result = db.execute_query(query)
        
        if result:
            message_id = result['id']
            message_text = result['message_text']
            
            # Increment usage counter
            update_query = """
                UPDATE motivational_messages 
                SET used_count = used_count + 1 
                WHERE id = %s
            """
            db.execute_update(update_query, (message_id,))
            
            return message_text
        else:
            # Fallback message if DB is empty
            return "🎉 Great job! Keep up the good work!"
            
    except Exception as e:
        print(f"❌ Error fetching motivational message: {e}")
        return "🎉 Great job! Keep up the good work!"

def get_all_motivational_messages() -> list:
    """
    Get all motivational messages (for admin management)
    
    Returns:
        list: All messages with metadata
    """
    try:
        db = DatabaseConnection()
        query = """
            SELECT 
                id,
                message_text,
                category,
                is_active,
                used_count,
                created_at
            FROM motivational_messages
            ORDER BY used_count DESC, id ASC
        """
        
        results = db.execute_query(query, fetch_all=True)
        return results if results else []
        
    except Exception as e:
        print(f"❌ Error fetching all messages: {e}")
        return []

def add_motivational_message(message_text: str, category: str = 'checkin') -> dict:
    """
    Add a new motivational message (admin function)
    
    Args:
        message_text: The motivational message
        category: Message category (default: 'checkin')
    
    Returns:
        dict: {'success': bool, 'message_id': int, 'message': str}
    """
    try:
        db = DatabaseConnection()
        query = """
            INSERT INTO motivational_messages (message_text, category)
            VALUES (%s, %s)
            RETURNING id
        """
        
        message_id = db.execute_insert(query, (message_text, category))
        
        if message_id:
            return {
                'success': True,
                'message_id': message_id,
                'message': 'Motivational message added successfully'
            }
        else:
            return {
                'success': False,
                'message': 'Failed to add message'
            }
            
    except Exception as e:
        print(f"❌ Error adding motivational message: {e}")
        return {
            'success': False,
            'message': str(e)
        }

def toggle_message_status(message_id: int, is_active: bool) -> dict:
    """
    Enable or disable a motivational message
    
    Args:
        message_id: Message ID
        is_active: True to enable, False to disable
    
    Returns:
        dict: {'success': bool, 'message': str}
    """
    try:
        db = DatabaseConnection()
        query = """
            UPDATE motivational_messages
            SET is_active = %s
            WHERE id = %s
        """
        
        db.execute_update(query, (is_active, message_id))
        
        status = "enabled" if is_active else "disabled"
        return {
            'success': True,
            'message': f'Message {status} successfully'
        }
        
    except Exception as e:
        print(f"❌ Error toggling message status: {e}")
        return {
            'success': False,
            'message': str(e)
        }

def get_message_statistics() -> dict:
    """
    Get statistics about motivational messages
    
    Returns:
        dict: Statistics including total, active, and usage counts
    """
    try:
        db = DatabaseConnection()
        query = """
            SELECT 
                COUNT(*) as total_messages,
                COUNT(*) FILTER (WHERE is_active = TRUE) as active_messages,
                SUM(used_count) as total_uses,
                AVG(used_count) as avg_uses_per_message
            FROM motivational_messages
        """
        
        result = db.execute_query(query)
        
        if result:
            return {
                'success': True,
                'total_messages': result['total_messages'],
                'active_messages': result['active_messages'],
                'total_uses': result['total_uses'] or 0,
                'avg_uses_per_message': float(result['avg_uses_per_message']) if result['avg_uses_per_message'] else 0
            }
        else:
            return {
                'success': False,
                'message': 'No statistics available'
            }
            
    except Exception as e:
        print(f"❌ Error fetching message statistics: {e}")
        return {
            'success': False,
            'message': str(e)
        }
