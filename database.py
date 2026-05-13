"""
Database models for Tender Dashboard
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Tender(Base):
    __tablename__ = 'tenders'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ocid = Column(String(128), index=True)
    external_id = Column(String(128), index=True)
    title = Column(Text)
    description = Column(Text)
    buyer_name = Column(String(512), index=True)
    buyer_id = Column(String(128))
    status = Column(String(64), index=True)
    tender_stage = Column(String(64))
    procurement_method = Column(String(128))
    value_amount = Column(Float)
    value_currency = Column(String(16))
    published_date = Column(DateTime, index=True)
    closing_date = Column(DateTime, index=True)
    source_url = Column(Text)
    source_name = Column(String(128), index=True)
    province = Column(String(128), index=True)
    category = Column(String(256), index=True)
    reference_number = Column(String(256))
    location = Column(String(256))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_tender_search', 'title', 'description'),
        Index('idx_source_unique', 'source_name', 'external_id', unique=True),
    )

DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'tenders.db'))
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database initialized.")

if __name__ == '__main__':
    init_db()
