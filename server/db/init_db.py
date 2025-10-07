"""
Database initialization script
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add the server directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.config import Base, engine, DATABASE_URL
from db.models import User, AvitoAccount, AdCard


def create_database():
    """Database already exists in production"""
    print("Database 'avito_management' already configured")


def create_tables():
    """Create all tables"""
    try:
        Base.metadata.create_all(bind=engine)
        print("All tables created successfully")
    except Exception as e:
        print(f"Error creating tables: {e}")
        raise


def create_indexes():
    """Create additional indexes for better performance"""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
        "CREATE INDEX IF NOT EXISTS idx_avito_accounts_client_id ON avito_accounts(client_id);",
        "CREATE INDEX IF NOT EXISTS idx_ad_cards_account_id ON ad_cards(account_id);",
        "CREATE INDEX IF NOT EXISTS idx_ad_cards_created_by ON ad_cards(created_by_user_id);",
    ]
    
    with engine.connect() as conn:
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                print(f"Index created: {index_sql.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                print(f"Error creating index: {e}")


def init_database():
    """Initialize the database tables and indexes"""
    print("Initializing database tables...")
    
    # Create tables
    create_tables()
    
    # Create indexes
    create_indexes()
    
    print("Database initialization completed successfully!")


if __name__ == "__main__":
    init_database()
