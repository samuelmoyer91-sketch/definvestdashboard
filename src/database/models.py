"""Database models for the Defense Capital Tracker."""

import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool
import os

logger = logging.getLogger(__name__)

# Import sqlalchemy_libsql to register the libsql dialect
try:
    import sqlalchemy_libsql
except ImportError:
    pass  # Not required for local SQLite

Base = declarative_base()

# Turso/LibSQL connection cache
_turso_engine = None
_session_factory = None
_libsql_conn = None


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
    status = Column(String, default='new')  # new, ai_screened_out, scraped, failed, auto_rejected

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

    # AI-generated title
    title = Column(String)  # Concise deal headline, e.g. "Shield AI Raises $300M Series E"

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
    title = Column(String)  # Editable title (overrides RawItem.title)
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

    # Source URL overrides
    source_url = Column(Text)             # Replaces raw_item.url as primary source link (optional)
    additional_source_url = Column(Text)  # Optional second source link shown alongside primary

    # Curation metadata
    human_notes = Column(Text)
    curated_by = Column(String)  # Future: user authentication
    curated_at = Column(DateTime, default=datetime.utcnow)

    # Publishing
    published = Column(Boolean, default=False)
    published_at = Column(DateTime)

    # Relationships
    raw_item = relationship("RawItem", back_populates="master")
    investor_links = relationship("DealInvestor", back_populates="master_item", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MasterItem(id={self.id}, company='{self.company}')>"


class Investor(Base):
    """Normalized investor entity."""
    __tablename__ = 'investors'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    deal_count = Column(Integer, default=0)  # Cached count
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # Relationships
    deal_links = relationship("DealInvestor", back_populates="investor")

    def __repr__(self):
        return f"<Investor(id={self.id}, name='{self.name}')>"


class DealInvestor(Base):
    """Join table linking deals to investors."""
    __tablename__ = 'deal_investors'

    id = Column(Integer, primary_key=True)
    master_item_id = Column(Integer, ForeignKey('master_list.id'), nullable=False)
    investor_id = Column(Integer, ForeignKey('investors.id'), nullable=False)
    is_lead = Column(Boolean, default=False)

    # Relationships
    master_item = relationship("MasterItem", back_populates="investor_links")
    investor = relationship("Investor", back_populates="deal_links")

    def __repr__(self):
        return f"<DealInvestor(master_item_id={self.master_item_id}, investor_id={self.investor_id})>"


class RejectedItem(Base):
    """Items that have been reviewed and rejected."""
    __tablename__ = 'rejected_items'

    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('raw_items.id'), unique=True, nullable=False)
    rejected_at = Column(DateTime, default=datetime.utcnow)
    rejection_reason = Column(Text)  # Optional notes on why rejected

    def __repr__(self):
        return f"<RejectedItem(item_id={self.item_id})>"


class ApiUsageLog(Base):
    """Per-run Claude API token usage for cost tracking."""
    __tablename__ = 'api_usage_log'

    id = Column(Integer, primary_key=True)
    logged_at = Column(DateTime, default=datetime.utcnow)
    run_type = Column(String)       # 'title_screen' or 'summarizer'
    model = Column(String)          # e.g. 'claude-haiku-4-5-20251001'
    items_processed = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    cost_usd = Column(Float)

    def __repr__(self):
        return f"<ApiUsageLog(run_type='{self.run_type}', cost=${self.cost_usd:.4f})>"


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
        # Use Turso cloud database via embedded replica
        if _turso_engine is not None:
            return _turso_engine

        import libsql

        turso_url = turso_url.strip()
        turso_token = turso_token.strip()

        try:
            logger.info(f"Attempting Turso connection to {turso_url[:30]}...")

            class LibsqlConnectionWrapper:
                """Wraps libsql connection to add DBAPI methods SQLAlchemy expects."""
                def __init__(self, conn):
                    self._conn = conn
                def create_function(self, *args, **kwargs):
                    pass  # SQLAlchemy calls this for REGEXP; not needed
                def __getattr__(self, name):
                    return getattr(self._conn, name)

            def get_libsql_connection():
                global _libsql_conn
                if _libsql_conn is None:
                    _libsql_conn = libsql.connect('turso_replica.db',
                        sync_url=turso_url,
                        auth_token=turso_token)
                    _libsql_conn.sync()  # Sync once on first connection
                    logger.info("Initial Turso sync complete")
                else:
                    # Verify the cached connection is still alive
                    try:
                        _libsql_conn.execute("SELECT 1")
                    except Exception:
                        logger.warning("Cached libsql connection stale, reconnecting...")
                        _libsql_conn = libsql.connect('turso_replica.db',
                            sync_url=turso_url,
                            auth_token=turso_token)
                        _libsql_conn.sync()
                return LibsqlConnectionWrapper(_libsql_conn)

            _turso_engine = create_engine(
                'sqlite+libsql://',
                creator=get_libsql_connection,
                poolclass=StaticPool,
                echo=False
            )
            # Test the connection
            with _turso_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(_turso_engine)
            logger.info("Turso connection established successfully")
            return _turso_engine
        except Exception as e:
            logger.error(f"Turso connection failed: {e}")
            _turso_engine = None
            raise
    else:
        # Fall back to local SQLite
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(engine)
        return engine


def sync_turso():
    """Sync the local Turso replica with the cloud after writes.

    Call this after committing data so subsequent reads see fresh data.
    No-op if not using Turso (local SQLite mode).
    On stream expiration errors (e.g. 'stream not found'), resets all
    cached connection state so the next get_session() call reconnects.
    """
    global _libsql_conn, _turso_engine, _session_factory
    if _libsql_conn is not None:
        try:
            _libsql_conn.sync()
        except Exception as e:
            logger.warning(f"Turso sync failed, resetting connection for reconnect: {e}")
            _libsql_conn = None
            _turso_engine = None
            _session_factory = None


def get_session(db_path='databases/tracker.db'):
    """Create and return database session."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine(db_path)
        _session_factory = sessionmaker(bind=engine)
    return _session_factory()
