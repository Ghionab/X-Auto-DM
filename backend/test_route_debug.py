#!/usr/bin/env python3
"""
Debug test to understand why the route isn't working as expected
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_route():
    """Debug the Twitter login route"""
    
    try:
        # Import and create app
        from app import create_app
        
        app = create_app('testing')
        
        # Print all routes to see what's registered
        print("Registered routes:")
        for rule in app.url_map.iter_rules():
            if 'twitter' in rule.rule:
                print(f"  {rule.rule} -> {rule.endpoint}")
        
        # Get the actual function
        with app.app_context():
            from flask import current_app
            
            # Find the twitter login endpoint
            for rule in current_app.url_map.iter_rules():
                if rule.rule == '/api/auth/twitter/login':
                    endpoint = rule.endpoint
                    view_func = current_app.view_functions[endpoint]
                    
                    print(f"\nFound endpoint: {endpoint}")
                    print(f"View function: {view_func}")
                    print(f"Function name: {view_func.__name__}")
                    print(f"Function doc: {view_func.__doc__}")
                    
                    # Try to get the source code
                    import inspect
                    try:
                        source = inspect.getsource(view_func)
                        print(f"Source preview (first 500 chars):")
                        print(source[:500])
                        
                        # Check if it contains our new error handling
                        if 'MISSING_REQUIRED_FIELDS' in source:
                            print("✅ Function contains new error handling")
                        else:
                            print("❌ Function does NOT contain new error handling")
                            
                    except Exception as e:
                        print(f"Could not get source: {e}")
                    
                    break
            else:
                print("❌ Twitter login route not found!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_route()