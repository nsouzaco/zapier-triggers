#!/usr/bin/env python3
"""Script to manage API keys and customers."""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.customer_service import customer_service
from app.utils.logging import setup_logging
from app.config import get_settings

setup_logging()

def ensure_rds_connection():
    """Ensure we're connecting to RDS, not local database."""
    settings = get_settings()
    
    # Check if we have RDS configuration
    if not (settings.rds_endpoint and settings.rds_username and settings.rds_password):
        print("⚠️  Warning: RDS configuration not found in environment.")
        print("   The script will use local database if available.")
        print("   To use RDS, set: RDS_ENDPOINT, RDS_USERNAME, RDS_PASSWORD")
        response = input("\n   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    else:
        # Force use of RDS by unsetting DATABASE_URL if it exists
        if 'DATABASE_URL' in os.environ:
            print("⚠️  DATABASE_URL is set, which may override RDS connection.")
            print(f"   Current DATABASE_URL: {os.environ['DATABASE_URL'][:50]}...")
            response = input("   Unset DATABASE_URL to use RDS? (y/n): ")
            if response.lower() == 'y':
                del os.environ['DATABASE_URL']
                # Clear settings cache to reload
                from app.config import get_settings
                get_settings.cache_clear()
                print("✅ DATABASE_URL unset, will use RDS")
        
        db_url = settings.postgresql_url
        safe_url = db_url.split('@')[1] if '@' in db_url else db_url
        print(f"✅ Connecting to RDS: {safe_url}")


def create_customer(
    name: Optional[str] = None,
    email: Optional[str] = None,
    api_key: Optional[str] = None,
    rate_limit: int = 1000,
):
    """Create a new customer with API key."""
    try:
        customer = customer_service.create_customer(
            name=name,
            email=email,
            api_key=api_key,
            rate_limit_per_second=rate_limit,
        )
        print(f"\n✅ Customer created successfully!")
        print(f"   Customer ID: {customer.customer_id}")
        print(f"   API Key: {customer.api_key}")
        print(f"   Name: {customer.name or 'N/A'}")
        print(f"   Email: {customer.email or 'N/A'}")
        print(f"   Rate Limit: {customer.rate_limit_per_second}/second")
        print(f"   Status: {customer.status}")
        print(f"\n📋 Use this API key in requests:")
        print(f"   curl -H 'Authorization: Bearer {customer.api_key}' \\")
        print(f"        -H 'Content-Type: application/json' \\")
        print(f"        -d '{{\"event_type\":\"test.event\",\"payload\":{{\"test\":\"data\"}}}}' \\")
        print(f"        http://localhost:8000/api/v1/events")
        return customer
    except Exception as e:
        print(f"❌ Error creating customer: {e}", file=sys.stderr)
        sys.exit(1)


def list_customers():
    """List all customers."""
    try:
        customers = customer_service.list_customers()
        if not customers:
            print("No customers found.")
            return

        print(f"\n📋 Found {len(customers)} customer(s):\n")
        for customer in customers:
            print(f"   Customer ID: {customer.customer_id}")
            print(f"   API Key: {customer.api_key}")
            print(f"   Name: {customer.name or 'N/A'}")
            print(f"   Email: {customer.email or 'N/A'}")
            print(f"   Status: {customer.status}")
            print(f"   Rate Limit: {customer.rate_limit_per_second}/second")
            print(f"   Created: {customer.created_at}")
            print()
    except Exception as e:
        print(f"❌ Error listing customers: {e}", file=sys.stderr)
        sys.exit(1)


def show_customer(customer_id: str):
    """Show details for a specific customer."""
    try:
        customer = customer_service.get_customer_by_id(customer_id)
        if not customer:
            print(f"❌ Customer not found: {customer_id}", file=sys.stderr)
            sys.exit(1)

        print(f"\n📋 Customer Details:")
        print(f"   Customer ID: {customer.customer_id}")
        print(f"   API Key: {customer.api_key}")
        print(f"   Name: {customer.name or 'N/A'}")
        print(f"   Email: {customer.email or 'N/A'}")
        print(f"   Status: {customer.status}")
        print(f"   Rate Limit: {customer.rate_limit_per_second}/second")
        print(f"   Created: {customer.created_at}")
        print(f"   Updated: {customer.updated_at}")
    except Exception as e:
        print(f"❌ Error showing customer: {e}", file=sys.stderr)
        sys.exit(1)


def disable_customer(customer_id: str):
    """Disable a customer."""
    try:
        if customer_service.update_customer_status(customer_id, "disabled"):
            print(f"✅ Customer {customer_id} disabled successfully")
        else:
            print(f"❌ Failed to disable customer: {customer_id}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error disabling customer: {e}", file=sys.stderr)
        sys.exit(1)


def enable_customer(customer_id: str):
    """Enable a customer."""
    try:
        if customer_service.update_customer_status(customer_id, "active"):
            print(f"✅ Customer {customer_id} enabled successfully")
        else:
            print(f"❌ Failed to enable customer: {customer_id}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error enabling customer: {e}", file=sys.stderr)
        sys.exit(1)


def delete_customer(customer_id: str):
    """Delete a customer."""
    try:
        if customer_service.delete_customer(customer_id):
            print(f"✅ Customer {customer_id} deleted successfully")
        else:
            print(f"❌ Failed to delete customer: {customer_id}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error deleting customer: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Manage API keys and customers")
    parser.add_argument("--use-rds", action="store_true", 
                       help="Force use of RDS (unset DATABASE_URL if present)")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new customer with API key")
    create_parser.add_argument("--name", help="Customer name")
    create_parser.add_argument("--email", help="Customer email")
    create_parser.add_argument("--api-key", help="Custom API key (generated if not provided)")
    create_parser.add_argument("--rate-limit", type=int, default=1000, help="Rate limit per second")

    # List command
    subparsers.add_parser("list", help="List all customers")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show customer details")
    show_parser.add_argument("customer_id", help="Customer ID")

    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable a customer")
    disable_parser.add_argument("customer_id", help="Customer ID")

    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable a customer")
    enable_parser.add_argument("customer_id", help="Customer ID")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a customer")
    delete_parser.add_argument("customer_id", help="Customer ID")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Ensure RDS connection if requested
    if args.use_rds:
        ensure_rds_connection()

    if args.command == "create":
        create_customer(
            name=args.name,
            email=args.email,
            api_key=args.api_key,
            rate_limit=args.rate_limit,
        )
    elif args.command == "list":
        list_customers()
    elif args.command == "show":
        show_customer(args.customer_id)
    elif args.command == "disable":
        disable_customer(args.customer_id)
    elif args.command == "enable":
        enable_customer(args.customer_id)
    elif args.command == "delete":
        delete_customer(args.customer_id)


if __name__ == "__main__":
    main()

