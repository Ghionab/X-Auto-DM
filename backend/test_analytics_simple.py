#!/usr/bin/env python3

"""
Simple test for Campaign Analytics Service
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_service_import():
    """Test that the service can be imported and instantiated"""
    try:
        from services.campaign_analytics_service import CampaignAnalyticsService
        print("✓ Service import successful")
        
        service = CampaignAnalyticsService()
        print("✓ Service instantiation successful")
        
        # Test that all required methods exist
        methods = [
            'calculate_campaign_metrics',
            'get_target_demographics',
            'compare_campaigns',
            'export_campaign_data',
            'generate_campaign_report'
        ]
        
        for method in methods:
            if hasattr(service, method):
                print(f"✓ Method {method} exists")
            else:
                print(f"✗ Method {method} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_error_handling():
    """Test error handling for invalid inputs"""
    try:
        from services.campaign_analytics_service import CampaignAnalyticsService
        service = CampaignAnalyticsService()
        
        # Test with non-existent campaign
        try:
            result = service.calculate_campaign_metrics(999999)
            print("✗ Should have raised an error for non-existent campaign")
            return False
        except Exception as e:
            print(f"✓ Correctly raised error for non-existent campaign: {type(e).__name__}")
        
        # Test compare_campaigns with empty list
        try:
            result = service.compare_campaigns([])
            print("✗ Should have raised an error for empty campaign list")
            return False
        except Exception as e:
            if "No campaign IDs provided" in str(e):
                print(f"✓ Correctly raised error for empty campaign list")
            else:
                print(f"✗ Unexpected error: {e}")
                return False
        
        # Test export with unsupported format
        try:
            result = service.export_campaign_data(1, 'json')
            print("✗ Should have raised an error for unsupported format")
            return False
        except Exception as e:
            if "Only CSV format is currently supported" in str(e):
                print(f"✓ Correctly raised error for unsupported format")
            else:
                print(f"✗ Unexpected error: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Unexpected error in error handling test: {e}")
        return False

if __name__ == '__main__':
    print("Testing Campaign Analytics Service...")
    
    success = True
    success &= test_service_import()
    success &= test_error_handling()
    
    if success:
        print("\n✓ All tests passed!")
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1)