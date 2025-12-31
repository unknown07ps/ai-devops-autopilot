"""
Database Setup Script
Run this to initialize the PostgreSQL database
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import init_db, engine
from models import Base, User, Subscription, SubscriptionStatus, SubscriptionPlan
from auth import hash_password, create_user
from subscription_service import create_trial_subscription
from sqlalchemy.orm import Session
import secrets

def create_superuser(db: Session):
    """Create initial superuser account"""
    email = os.getenv("ADMIN_EMAIL", "admin@deployr.com")
    password = os.getenv("ADMIN_PASSWORD", secrets.token_urlsafe(16))
    
    # Check if admin exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"⚠️  Admin user already exists: {email}")
        return existing
    
    # Create admin user
    user_id = f"usr_{secrets.token_urlsafe(16)}"
    
    admin = User(
        user_id=user_id,
        email=email,
        hashed_password=hash_password(password),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
        email_verified=True
    )
    
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    # Create pro subscription for admin
    sub_id = f"sub_{secrets.token_urlsafe(16)}"
    from datetime import datetime, timedelta, timezone
    
    subscription = Subscription(
        subscription_id=sub_id,
        user_id=admin.user_id,
        plan=SubscriptionPlan.PRO,
        status=SubscriptionStatus.ACTIVE,
        subscription_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=365),
        feature_limits={
            "max_services": -1,
            "data_retention_days": 90,
            "max_actions_per_day": -1,
            "ai_analysis": True,
            "auto_remediation": True,
            "autonomous_mode": True,
            "slack_alerts": True,
        }
    )
    
    db.add(subscription)
    db.commit()
    
    print(f"✅ Admin user created:")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"   ⚠️  SAVE THIS PASSWORD - it won't be shown again!")
    
    return admin

def main():
    print("🚀 Setting up Deployr Database\n")
    
    # Check database connection
    print("1️⃣ Testing database connection...")
    try:
        with engine.connect() as conn:
            print("   ✅ Connected to database")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        print("\n   Make sure PostgreSQL is running:")
        print("   docker-compose up -d postgres")
        return
    
    # Create tables
    print("\n2️⃣ Creating database tables...")
    try:
        init_db()
        print("   ✅ Tables created successfully")
    except Exception as e:
        print(f"   ❌ Table creation failed: {e}")
        return
    
    # Create superuser
    print("\n3️⃣ Creating admin user...")
    try:
        from database import SessionLocal
        db = SessionLocal()
        create_superuser(db)
        db.close()
    except Exception as e:
        print(f"   ❌ Admin creation failed: {e}")
        return
    
    print("\n✅ Database setup complete!")
    print("\n📚 Next steps:")
    print("   1. Update your .env file with:")
    print("      DATABASE_URL=postgresql://deployr:deployr_password@localhost:5432/deployr")
    print("      JWT_SECRET_KEY=<generate-a-secret-key>")
    print("   2. Update src/main.py to use PostgreSQL instead of Redis for auth")
    print("   3. Restart the application")
    print("\n🔐 Login with the admin credentials shown above")

if __name__ == "__main__":
    main()