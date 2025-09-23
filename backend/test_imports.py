#!/usr/bin/env python3
"""
Test imports for manual account service
"""

import sys
import os

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required imports work"""
    
    print("🧪 Testing Imports for Manual Account Service")
    print("=" * 50)
    
    try:
        print("1. Testing Flask app imports...")
        from app import create_app
        print("✅ Flask app imports successful")
        
        print("2. Testing manual account service imports...")
        from services.manual_account_service import ManualAccountService
        print("✅ Manual account service imports successful")
        
        print("3. Testing cookie encryption imports...")
        from services.cookie_encryption import CookieManager
        print("✅ Cookie encryption imports successful")
        
        print("4. Testing models imports...")
        from models import db, User, TwitterAccount
        print("✅ Models imports successful")
        
        print("5. Creating Flask app instance...")
        app = create_app('development')
        print("✅ Flask app creation successful")
        
        print("6. Testing manual account service instantiation...")
        with app.app_context():
            manual_service = ManualAccountService()
            print("✅ Manual account service instantiation successful")
        
        print("\n" + "=" * 50)
        print("🎉 All imports and instantiations successful!")
        
    except Exception as e:
        print(f"❌ Import/instantiation failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_imports()