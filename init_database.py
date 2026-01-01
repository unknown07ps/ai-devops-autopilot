"""
Database initialization script for AI DevOps Autopilot
Run this to create all necessary tables
"""
import sys
import os
from sqlalchemy import create_engine, text

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database import engine, DATABASE_URL
from models import Base

def init_database():
    """Initialize database with all tables"""
    print("=" * 70)
    print("AI DevOps Autopilot - Database Initialization")
    print("=" * 70)
    
    try:
        # Use existing engine
        print(f"\n[1/3] Connecting to database...")
        print(f"      Database URL: {DATABASE_URL}")
        
        # Test connection
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
        print("      ✓ Database connection successful")
        
        # Drop all tables (optional - uncomment if you want fresh start)
        # print("\n[2/3] Dropping existing tables...")
        # Base.metadata.drop_all(bind=engine)
        # print("      ✓ Tables dropped")
        
        # Create all tables
        print("\n[2/3] Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("      ✓ Tables created successfully")
        
        # Verify tables
        print("\n[3/3] Verifying tables...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """))
            tables = [row[0] for row in result]
            
            if tables:
                print(f"      ✓ Found {len(tables)} tables:")
                for table in tables:
                    print(f"        - {table}")
            else:
                print("      ⚠ No tables found!")
                return False
        
        print("\n" + "=" * 70)
        print("✓ Database initialization completed successfully!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n✗ Database initialization failed!")
        print(f"Error: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check if PostgreSQL is running")
        print("2. Verify database credentials in .env")
        print("3. Ensure database 'ai_devops_autopilot' exists")
        print("4. Check if user has CREATE TABLE permissions")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)