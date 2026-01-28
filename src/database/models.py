"""Database models for the Defense Capital Tracker."""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

# Import sqlalchemy_libsql to register the libsql dialect
try:
    import sqlalchemy_libsql
except ImportError:
    pass  # Not required for local SQLite

Base = declarative_base()

# Turso/LibSQL connection cache
_turso_engine = None


class RawItem(Base):
    """Raw RSS feed items."""
    __tablename__ = 'raw_items'

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    rss_summary = Column(Text)
    published_date = Column(DateTime)
    feed_source = Column(String)  # Which Google Alert feed
    date_found = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='new')  # new, scraped, failed, auto_rejected

    # Relevance scoring (added 2026-01-22)
    relevance_score = Column(Float)  # 0.0-1.0, based on keyword matching
    relevance_flags = Column(Text)   # Comma-separated list of matched keywords

    # Relationships
    article = relationship("ArticleContent", back_populates="raw_item", uselist=False)
    extraction = relationship("AIExtraction", back_populates="raw_item", uselist=False)
    master = relationship("MasterItem", back_populates="raw_item", uselist=False)

    def __repr__(self):
        return f"<RawItem(id={self.id}, title='{self.title[:50]}...')>"


class ArticleContent(Base):
    """Scraped full article content."""
    __tablename__ = 'article_content'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('raw_items.id'), unique=True, nullable=False)
    html = Column(Text)
    clean_text = Column(Text)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    scrape_success = Column(Boolean, default=True)
    error_message = Column(Text)

    # Relationships
    raw_item = relationship("RawItem", back_populates="article")

    def __repr__(self):
        return f"<ArticleContent(item_id={self.item_id}, success={self.scrape_success})>"


class AIExtraction(Base):
    """AI-extracted structured data for defense investment deals."""
    __tablename__ = 'ai_extractions'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('raw_items.id'), unique=True, nullable=False)

    # Core deal information
    company = Column(String)  # Company name
    company_description = Column(Text)  # What the company does (1 sentence)
    deal_type = Column(String)  # VC, M&A, IPO, etc. (legacy)
    deal_amount = Column(String)  # e.g., "$300M", "$4.7B"
    investors = Column(Text)  # Key investors/acquirers

    # New enhanced category fields
    transaction_type = Column(String)  # Single-select: Equity Funding Round, Acquisition, etc.
    capital_sources = Column(Text)  # Multi-select comma-separated: "Venture Capital,Corporate Venture"
    sectors = Column(Text)  # Multi-select comma-separated: "AI/ML,Autonomous Systems/Drones"

    # Analysis fields
    strategic_significance = Column(Text)  # Why this matters (2-3 sentences)
    market_implications = Column(Text)  # What this signals (1-2 sentences)

    # Legacy/additional fields (kept for backward compatibility)
    capital_type = Column(String)  # VC, PE, corporate, public-private
    location = Column(String)
    sector = Column(String)  # Single sector (legacy)
    project_type = Column(String)  # factory, lab, test range, acquisition
    ai_summary = Column(Text)  # General summary field

    # Metadata
    confidence_score = Column(Float)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    model_used = Column(String)  # e.g., "claude-sonnet-4-20250514"
    summary_complete = Column(Boolean, default=False)  # Was AI extraction successful?

    # Relationships
    raw_item = relationship("RawItem", back_populates="extraction")

    def __repr__(self):
        return f"<AIExtraction(item_id={self.item_id}, company='{self.company}')>"


class MasterItem(Base):
    """Human-curated master list for publication."""
    __tablename__ = 'master_list'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('raw_items.id'), unique=True, nullable=False)

    # Human-verified fields (can override AI extractions)
    company = Column(String)
    investors = Column(String)
    investment_amount = Column(String)

    # Legacy single-select fields (kept for backward compatibility)
    deal_type = Column(String)
    capital_type = Column(String)
    project_type = Column(String)
    sector = Column(String)

    # New multi-select fields (JSON-encoded comma-separated lists)
    transaction_type = Column(String)  # Single-select
    capital_sources = Column(Text)  # Multi-select: "Venture Capital,Corporate Venture"
    sectors = Column(Text)  # Multi-select: "AI/ML,Space,Aerospace"

    location = Column(String)
    summary = Column(Text)

    # Curation metadata
    human_notes = Column(Text)
    curated_by = Column(String)  # Future: user authentication
    curated_at = Column(DateTime, default=datetime.utcnow)

    # Publishing
    published = Column(Boolean, default=False)
    published_at = Column(DateTime)

    # Relationships
    raw_item = relationship("RawItem", back_populates="master")

    def __repr__(self):
        return f"<MasterItem(id={self.id}, company='{self.company}')>"


class RejectedItem(Base):
    """Items that have been reviewed and rejected."""
    __tablename__ = 'rejected_items'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('raw_items.id'), unique=True, nullable=False)
    rejected_at = Column(DateTime, default=datetime.utcnow)
    rejection_reason = Column(Text)  # Optional notes on why rejected

    def __repr__(self):
        return f"<RejectedItem(item_id={self.item_id})>"


# Database setup
def get_engine(db_path='databases/tracker.db'):
    """Create and return database engine.

    Supports both local SQLite and cloud Turso database.
    Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN env vars for cloud mode.
    """
    global _turso_engine

    turso_url = os.environ.get('TURSO_DATABASE_URL')
    turso_token = os.environ.get('TURSO_AUTH_TOKEN')

    if turso_url and turso_token:
        # Use Turso cloud database
        if _turso_engine is not None:
            return _turso_engine

        import libsql_experimental as libsql

        # Convert libsql:// to https:// for HTTP-based connection (more compatible)
        if turso_url.startswith('libsql://'):
            http_url = turso_url.replace('libsql://', 'https://')
        else:
            http_url = turso_url

        # Create connection factory for SQLAlchemy
        def get_libsql_connection():
            return libsql.connect(
                'defense-tracker',
                sync_url=http_url,
                auth_token=turso_token
            )

        _turso_engine = create_engine(
            'sqlite+libsql://',
            creator=get_libsql_connection,
            echo=False
        )
        Base.metadata.create_all(_turso_engine)
        return _turso_engine
    else:
        # Fall back to local SQLite
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(engine)
        return engine


def get_session(db_path='databases/tracker.db'):
    """Create and return database session."""
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()
