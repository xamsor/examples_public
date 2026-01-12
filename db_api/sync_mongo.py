#!/usr/bin/env python3
"""
Sync MongoDB user/subscription data to local DuckDB warehouse.

Optimized version using config-driven approach and batch inserts.

Usage:
    python3 db_api/sync_mongo_v2.py
"""

import os
import sys
import argparse
from datetime import datetime

import duckdb
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

try:
    from pymongo import MongoClient
except ImportError:
    print("ERROR: Required packages not installed. Run:")
    print("  pip3 install pymongo")
    sys.exit(1)

# Configuration
MONGO_URI = os.getenv('MONGO_URI')
WAREHOUSE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'warehouse.duckdb')

# Collection definitions: (mongo_field, duckdb_column, type, is_object_id, is_unix_timestamp)
# is_object_id: convert ObjectId to string
# is_unix_timestamp: convert Unix timestamp to datetime
COLLECTIONS = [
    {
        'name': 'users',
        'table': 'mongo_users',
        'fields': [
            ('_id', 'id', 'VARCHAR PRIMARY KEY', True, False),
            ('email', 'email', 'VARCHAR', False, False),
            ('role', 'role', 'INTEGER', False, False),
            ('status', 'status', 'INTEGER', False, False),
            ('companyId', 'company_id', 'VARCHAR', True, False),
            ('customerId', 'customer_id', 'VARCHAR', False, False),
            ('isPublisher', 'is_publisher', 'BOOLEAN', False, False),
            ('balance', 'balance', 'DOUBLE', False, False),
            ('createdAt', 'created_at', 'TIMESTAMP', False, False),
            ('updatedAt', 'updated_at', 'TIMESTAMP', False, False),
        ]
    },
    {
        'name': 'subscriptions',
        'table': 'mongo_subscriptions',
        'fields': [
            ('_id', 'id', 'VARCHAR PRIMARY KEY', True, False),
            ('subscriptionId', 'subscription_id', 'VARCHAR', False, False),
            ('userId', 'user_id', 'VARCHAR', True, False),
            ('companyId', 'company_id', 'VARCHAR', True, False),
            ('type', 'type', 'VARCHAR', False, False),
            ('amount', 'amount', 'INTEGER', False, False),
            ('currency', 'currency', 'VARCHAR', False, False),
            ('interval', 'interval', 'VARCHAR', False, False),
            ('stripeStatus', 'stripe_status', 'VARCHAR', False, False),
            ('priceId', 'price_id', 'VARCHAR', False, False),
            ('startDate', 'start_date', 'TIMESTAMP', False, True),
            ('currentPeriodStart', 'current_period_start', 'TIMESTAMP', False, True),
            ('currentPeriodEnd', 'current_period_end', 'TIMESTAMP', False, True),
            ('cancelAtPeriodEnd', 'cancel_at_period_end', 'BOOLEAN', False, False),
            ('canceledAt', 'canceled_at', 'TIMESTAMP', False, True),
            ('endedAt', 'ended_at', 'TIMESTAMP', False, True),
            ('createdAt', 'created_at', 'TIMESTAMP', False, False),
            ('updatedAt', 'updated_at', 'TIMESTAMP', False, False),
        ]
    },
    {
        'name': 'stripePayments',
        'table': 'mongo_payments',
        'fields': [
            ('_id', 'id', 'VARCHAR PRIMARY KEY', True, False),
            ('paymentIntentId', 'payment_intent_id', 'VARCHAR', False, False),
            ('userId', 'user_id', 'VARCHAR', True, False),
            ('companyId', 'company_id', 'VARCHAR', True, False),
            ('email', 'email', 'VARCHAR', False, False),
            ('amount', 'amount', 'INTEGER', False, False),
            ('currency', 'currency', 'VARCHAR', False, False),
            ('method', 'method', 'VARCHAR', False, False),
            ('paymentStatus', 'payment_status', 'VARCHAR', False, False),
            ('stripeStatus', 'stripe_status', 'VARCHAR', False, False),
            ('last4', 'last4', 'VARCHAR', False, False),
            ('description', 'description', 'VARCHAR', False, False),
            ('receiptUrl', 'receipt_url', 'VARCHAR', False, False),
            ('createdAt', 'created_at', 'TIMESTAMP', False, False),
            ('updatedAt', 'updated_at', 'TIMESTAMP', False, False),
        ]
    },
    {
        'name': 'companies',
        'table': 'mongo_companies',
        'fields': [
            ('_id', 'id', 'VARCHAR PRIMARY KEY', True, False),
            ('name', 'name', 'VARCHAR', False, False),
            ('ownerId', 'owner_id', 'VARCHAR', True, False),
            ('subscriptionType', 'subscription_type', 'VARCHAR', False, False),
            ('createdAt', 'created_at', 'TIMESTAMP', False, False),
            ('updatedAt', 'updated_at', 'TIMESTAMP', False, False),
        ]
    },
    {
        'name': 'orders',
        'table': 'mongo_orders',
        'fields': [
            ('_id', 'id', 'VARCHAR PRIMARY KEY', True, False),
            ('orderId', 'order_id', 'INTEGER', False, False),
            ('userId', 'user_id', 'VARCHAR', True, False),
            ('companyId', 'company_id', 'VARCHAR', True, False),
            ('link', 'domain', 'VARCHAR', False, False),  # MongoDB field is 'link'
            ('price', 'price', 'DOUBLE', False, False),
            ('status', 'status', 'VARCHAR', False, False),
            ('paymentStatus', 'payment_status', 'VARCHAR', False, False),
            ('buyerEmail', 'buyer_email', 'VARCHAR', False, False),
            ('sellerEmail', 'seller_email', 'VARCHAR', False, False),
            ('stripePaymentId', 'stripe_payment_id', 'VARCHAR', True, False),
            ('docUrl', 'doc_url', 'VARCHAR', False, False),
            ('createdAt', 'created_at', 'TIMESTAMP', False, False),
            ('updatedAt', 'updated_at', 'TIMESTAMP', False, False),
        ]
    },
    {
        'name': 'userUnlocks',
        'table': 'mongo_user_unlocks',
        'fields': [
            ('_id', 'id', 'VARCHAR PRIMARY KEY', True, False),
            ('userId', 'user_id', 'VARCHAR', True, False),
            ('companyId', 'company_id', 'VARCHAR', True, False),
            ('domainId', 'domain_id', 'VARCHAR', True, False),
            ('domain', 'domain', 'VARCHAR', False, False),
            ('createdAt', 'created_at', 'TIMESTAMP', False, False),
        ]
    },
    {
        'name': 'internalPayments',
        'table': 'mongo_internal_payments',
        'fields': [
            ('_id', 'id', 'VARCHAR PRIMARY KEY', True, False),
            ('userId', 'user_id', 'VARCHAR', True, False),
            ('companyId', 'company_id', 'VARCHAR', True, False),
            ('amount', 'amount', 'INTEGER', False, False),
            ('actionType', 'action_type', 'VARCHAR', False, False),
            ('status', 'status', 'VARCHAR', False, False),
            ('createdAt', 'created_at', 'TIMESTAMP', False, False),
            ('updatedAt', 'updated_at', 'TIMESTAMP', False, False),
        ]
    },
    {
        'name': 'projects',
        'table': 'mongo_projects',
        'fields': [
            ('_id', 'id', 'VARCHAR PRIMARY KEY', True, False),
            ('userId', 'user_id', 'VARCHAR', True, False),
            ('companyId', 'company_id', 'VARCHAR', True, False),
            ('name', 'name', 'VARCHAR', False, False),
            ('domain', 'domain', 'VARCHAR', False, False),
            ('createdAt', 'created_at', 'TIMESTAMP', False, False),
            ('updatedAt', 'updated_at', 'TIMESTAMP', False, False),
        ]
    },
    {
        'name': 'projectProspects',
        'table': 'mongo_project_prospects',
        'fields': [
            ('_id', 'id', 'VARCHAR PRIMARY KEY', True, False),
            ('projectId', 'project_id', 'VARCHAR', True, False),
            ('userId', 'user_id', 'VARCHAR', True, False),
            ('companyId', 'company_id', 'VARCHAR', True, False),
            ('domain', 'domain', 'VARCHAR', False, False),
            ('status', 'status', 'VARCHAR', False, False),
            ('liveLink', 'live_link', 'VARCHAR', False, False),
            ('orderPrice', 'order_price', 'DOUBLE', False, False),
            ('placedVia', 'placed_via', 'VARCHAR', False, False),
            ('createdAt', 'created_at', 'TIMESTAMP', False, False),
            ('updatedAt', 'updated_at', 'TIMESTAMP', False, False),
        ]
    },
    {
        'name': 'projectCompletedOrders',
        'table': 'mongo_project_completed_orders',
        'fields': [
            ('_id', 'id', 'VARCHAR PRIMARY KEY', True, False),
            ('projectId', 'project_id', 'VARCHAR', True, False),
            ('userId', 'user_id', 'VARCHAR', True, False),
            ('domain', 'domain', 'VARCHAR', False, False),
            ('liveLink', 'live_link', 'VARCHAR', False, False),
            ('placedVia', 'placed_via', 'VARCHAR', False, False),
            ('createdAt', 'created_at', 'TIMESTAMP', False, False),
            ('updatedAt', 'updated_at', 'TIMESTAMP', False, False),
        ]
    },
]


def log(msg):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_mongo_client():
    """Initialize MongoDB client."""
    if not MONGO_URI:
        raise ValueError("MONGO_URI not set in .env")
    return MongoClient(MONGO_URI)


def extract_value(doc, mongo_field, is_object_id, is_unix_timestamp):
    """Extract and convert a value from a MongoDB document."""
    value = doc.get(mongo_field)

    if value is None:
        return None

    if is_object_id:
        return str(value) if value else None

    if is_unix_timestamp:
        return datetime.fromtimestamp(value) if value else None

    return value


def build_create_table_sql(config):
    """Generate CREATE TABLE statement from config."""
    table = config['table']
    columns = [f"{col} {dtype}" for _, col, dtype, _, _ in config['fields']]
    columns.append("synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    return f"CREATE OR REPLACE TABLE {table} (\n    {','.join(columns)}\n)"


def build_insert_sql(config):
    """Generate INSERT statement from config."""
    table = config['table']
    columns = [col for _, col, _, _, _ in config['fields']]
    placeholders = ', '.join(['?' for _ in columns])
    return f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"


def extract_row(doc, config):
    """Extract a row tuple from a MongoDB document based on config."""
    return tuple(
        extract_value(doc, mongo_field, is_oid, is_unix)
        for mongo_field, _, _, is_oid, is_unix in config['fields']
    )


def sync_collection(db, conn, config):
    """Sync a single MongoDB collection to DuckDB."""
    collection_name = config['name']
    table_name = config['table']

    log(f"Fetching {collection_name}...")
    docs = list(db[collection_name].find())
    log(f"  Got {len(docs)} documents")

    if not docs:
        return 0

    # Create table
    conn.execute(build_create_table_sql(config))

    # Batch insert
    rows = [extract_row(doc, config) for doc in docs]
    conn.executemany(build_insert_sql(config), rows)

    log(f"  Saved {len(docs)} rows to {table_name}")
    return len(docs)


def main():
    parser = argparse.ArgumentParser(description='Sync MongoDB data to DuckDB (v2)')
    parser.add_argument('--incremental', action='store_true',
                        help='Only sync new records (not implemented yet)')
    args = parser.parse_args()

    print("=" * 60)
    print("MongoDB -> DuckDB Sync (v2)")
    print("=" * 60)
    log(f"Warehouse: {WAREHOUSE_PATH}")
    print("-" * 60)

    try:
        # Connect to MongoDB
        log("Connecting to MongoDB...")
        client = get_mongo_client()
        db = client['getlinks_pro_prod']
        log("  Connected")

        # Connect to DuckDB
        log("Opening warehouse...")
        conn = duckdb.connect(WAREHOUSE_PATH)
        log("  Connected")

        print("-" * 60)

        # Sync each collection
        total_rows = 0
        for config in COLLECTIONS:
            total_rows += sync_collection(db, conn, config)

        conn.close()
        client.close()

        print("-" * 60)
        log(f"DONE! Synced {total_rows:,} total rows")
        print("=" * 60)

        # Show summary
        print("\nTo query the data:")
        print("  python3 -c \"import duckdb; print(duckdb.connect('warehouse.duckdb').sql('SELECT * FROM mongo_users LIMIT 10'))\"")

    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
