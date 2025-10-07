# Database Module - Avito Management

Production-ready database module for the Avito Management system.

## Files

- `config.py` - Database configuration and connection settings
- `models.py` - SQLAlchemy models for all tables
- `database.py` - Database manager with CRUD operations
- `init_db.py` - Database initialization script
- `env_example.txt` - Environment variables template

## Database Schema

### Tables

1. **users** - System users
2. **avito_accounts** - Avito accounts  
3. **ad_cards** - Advertisement cards

## Usage

### Database Manager

```python
from db.database import db_manager

# Test connection
if db_manager.test_connection():
    print("Database connected")

# Get user by email
user = db_manager.get_user_by_email("user@example.com")

# Create new user
user_data = {
    "username": "new_user",
    "email": "new@example.com", 
    "password_hash": "hashed_password"
}
user = db_manager.create_user(user_data)
```

### Direct Model Usage

```python
from db.models import User, AvitoAccount, AdCard
from db.config import SessionLocal

session = SessionLocal()
# Your operations here
session.close()
```

## Environment Variables

Set `DATABASE_URL` environment variable:
```
DATABASE_URL=postgresql://avito_user:avito_password@localhost:5432/avito_management
```

## Initialization

```bash
python init_db.py
```
