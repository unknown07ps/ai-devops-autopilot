"""
Check if all models are properly imported
"""
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_models():
    print("Checking model imports...")
    
    try:
        print("\n1. Importing Base...")
        from models import Base
        print("   ✓ Base imported")
        
        print("\n2. Checking registered models...")
        print(f"   Found {len(Base.metadata.tables)} tables:")
        
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
        
        if len(Base.metadata.tables) == 0:
            print("\n   ⚠ No tables registered!")
            print("   This means models aren't being imported properly.")
            print("\n   Check your app/models/__init__.py file")
            print("   It should import all model classes")
            return False
        
        print("\n✓ All models loaded successfully")
        return True
        
    except Exception as e:
        print(f"\n✗ Error loading models: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_models()
    sys.exit(0 if success else 1)