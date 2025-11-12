#!/usr/bin/env python3
"""Script to check subscriptions in RDS database."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.subscription_service import subscription_service
from app.services.customer_service import customer_service
from app.utils.logging import setup_logging
import asyncio

setup_logging()


async def check_subscriptions():
    """Check subscriptions for all customers."""
    print("🔍 Checking subscriptions in RDS database...\n")
    
    # List all customers
    customers = customer_service.list_customers()
    
    if not customers:
        print("❌ No customers found in database")
        return
    
    print(f"📋 Found {len(customers)} customer(s):\n")
    
    total_subscriptions = 0
    for customer in customers:
        print(f"  Customer: {customer.customer_id}")
        print(f"    Name: {customer.name or 'N/A'}")
        print(f"    Email: {customer.email or 'N/A'}")
        print(f"    API Key: {customer.api_key[:20]}...")
        
        # Get subscriptions for this customer
        subscriptions = await subscription_service.get_subscriptions(customer.customer_id)
        
        if subscriptions:
            print(f"    ✅ Found {len(subscriptions)} subscription(s):")
            for sub in subscriptions:
                print(f"      - Workflow ID: {sub.workflow_id}")
                print(f"        Event Selector: {sub.event_selector}")
                print(f"        Webhook URL: {sub.webhook_url[:50]}...")
                print(f"        Status: {sub.status}")
            total_subscriptions += len(subscriptions)
        else:
            print(f"    ⚠️  No subscriptions found")
        print()
    
    print(f"📊 Summary: {len(customers)} customer(s), {total_subscriptions} subscription(s) total")
    
    if total_subscriptions == 0:
        print("\n💡 Tip: Create a subscription to route events to workflows.")
        print("   Use subscription_service.create_subscription() or insert directly into RDS.")


if __name__ == "__main__":
    asyncio.run(check_subscriptions())

