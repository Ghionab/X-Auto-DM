#!/usr/bin/env python3

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from services.campaign_analytics_service import CampaignAnalyticsService
    print("✓ Import successful")
    
    # Test instantiation
    service = CampaignAnalyticsService()
    print("✓ Service instantiation successful")
    
    # Test that all methods exist
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
            
except ImportError as e:
    print(f"✗ Import failed: {e}")
except Exception as e:
    print(f"✗ Error: {e}")