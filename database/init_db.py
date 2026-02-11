"""
Database initialization script
Run this to create the database with the schema
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database(db_path: str = None, schema_path: str = None):
    """Initialize the database with schema."""
    
    if db_path is None:
        db_path = Path(__file__).parent / "loan_collateral.db"
    
    if schema_path is None:
        schema_path = Path(__file__).parent / "schema.sql"
    
    logger.info(f"Initializing database at: {db_path}")
    logger.info(f"Using schema from: {schema_path}")
    
    # Create database manager
    db_manager = DatabaseManager(str(db_path))
    
    # Initialize with schema
    db_manager.initialize_database(str(schema_path))
    
    # Verify tables were created
    stats = db_manager.get_database_stats()
    logger.info("Database statistics:")
    for table, count in stats.items():
        logger.info(f"  {table}: {count} rows")
    
    logger.info("Database initialized successfully!")
    
    db_manager.close()
    
    return str(db_path)


if __name__ == "__main__":
    init_database()
