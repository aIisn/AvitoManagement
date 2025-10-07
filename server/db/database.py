"""
Database connection and session management
"""
from sqlalchemy.orm import Session
from .config import SessionLocal, engine
from .models import User, AvitoAccount, AdCard


class DatabaseManager:
    """Database manager for handling connections and operations"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def close_session(self, session: Session):
        """Close database session"""
        session.close()
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
    
    def get_user_by_email(self, email: str) -> User:
        """Get user by email"""
        session = self.get_session()
        try:
            return session.query(User).filter(User.email == email).first()
        finally:
            self.close_session(session)
    
    def get_user_by_id(self, user_id: int) -> User:
        """Get user by ID"""
        session = self.get_session()
        try:
            return session.query(User).filter(User.id == user_id).first()
        finally:
            self.close_session(session)
    
    def get_avito_account_by_client_id(self, client_id: str) -> AvitoAccount:
        """Get Avito account by client ID"""
        session = self.get_session()
        try:
            return session.query(AvitoAccount).filter(AvitoAccount.client_id == client_id).first()
        finally:
            self.close_session(session)
    
    def get_ad_cards_by_account_id(self, account_id: int) -> list[AdCard]:
        """Get all ad cards for specific account"""
        session = self.get_session()
        try:
            return session.query(AdCard).filter(AdCard.account_id == account_id).all()
        finally:
            self.close_session(session)
    
    def get_ad_cards_by_user_id(self, user_id: int) -> list[AdCard]:
        """Get all ad cards created by specific user"""
        session = self.get_session()
        try:
            return session.query(AdCard).filter(AdCard.created_by_user_id == user_id).all()
        finally:
            self.close_session(session)
    
    def create_user(self, user_data: dict) -> User:
        """Create new user"""
        session = self.get_session()
        try:
            user = User(**user_data)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        finally:
            self.close_session(session)
    
    def create_avito_account(self, account_data: dict) -> AvitoAccount:
        """Create new Avito account"""
        session = self.get_session()
        try:
            account = AvitoAccount(**account_data)
            session.add(account)
            session.commit()
            session.refresh(account)
            return account
        finally:
            self.close_session(session)
    
    def create_ad_card(self, card_data: dict) -> AdCard:
        """Create new ad card"""
        session = self.get_session()
        try:
            card = AdCard(**card_data)
            session.add(card)
            session.commit()
            session.refresh(card)
            return card
        finally:
            self.close_session(session)


# Global database manager instance
db_manager = DatabaseManager()
