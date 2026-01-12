#!/usr/bin/env python3
"""
Sync MongoDB user/subscription data to local DuckDB warehouse.

Pulls data from GetLinks Pro Prod MongoDB and stores in warehouse.duckdb tables:
- mongo_users: User accounts with signup dates
- mongo_subscriptions: Subscription history with status changes
- mongo_payments: Stripe payment transactions
- mongo_companies: Company/team data
- mongo_projects: User projects (folders for organizing publishers)
- mongo_project_prospects: Publishers saved to projects
- mongo_project_completed_orders: Backlinks purchased via projects

Usage:
    python3 db_api/sync_mongo.py              # Full sync (replaces all data)
    python3 db_api/sync_mongo.py --incremental # Only sync new records
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
    from bson import ObjectId
except ImportError:
    print("ERROR: Required packages not installed. Run:")
    print("  pip3 install pymongo")
    sys.exit(1)

# Configuration
MONGO_URI = os.getenv('MONGO_URI')
WAREHOUSE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'warehouse.duckdb')


def log(msg):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_mongo_client():
    """Initialize MongoDB client."""
    if not MONGO_URI:
        raise ValueError("MONGO_URI not set in .env")
    return MongoClient(MONGO_URI)


def sync_users(db, conn):
    """Sync users collection."""
    log("Fetching users...")

    users = list(db['users'].find())
    log(f"  Got {len(users)} users")

    if not users:
        return 0

    # Create table
    conn.execute("""
        CREATE OR REPLACE TABLE mongo_users (
            id VARCHAR PRIMARY KEY,
            email VARCHAR,
            role INTEGER,
            status INTEGER,
            company_id VARCHAR,
            customer_id VARCHAR,
            is_publisher BOOLEAN,
            balance DOUBLE,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert data
    for user in users:
        conn.execute("""
            INSERT INTO mongo_users
            (id, email, role, status, company_id, customer_id, is_publisher, balance, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(user.get('_id', '')),
            user.get('email'),
            user.get('role'),
            user.get('status'),
            str(user.get('companyId', '')) if user.get('companyId') else None,
            user.get('customerId'),
            user.get('isPublisher', False),
            user.get('balance', 0),
            user.get('createdAt'),
            user.get('updatedAt')
        ])

    log(f"  Saved {len(users)} rows to mongo_users")
    return len(users)


def sync_subscriptions(db, conn):
    """Sync subscriptions collection."""
    log("Fetching subscriptions...")

    subs = list(db['subscriptions'].find())
    log(f"  Got {len(subs)} subscriptions")

    if not subs:
        return 0

    # Create table
    conn.execute("""
        CREATE OR REPLACE TABLE mongo_subscriptions (
            id VARCHAR PRIMARY KEY,
            subscription_id VARCHAR,
            user_id VARCHAR,
            company_id VARCHAR,
            type VARCHAR,
            amount INTEGER,
            currency VARCHAR DEFAULT 'usd',
            interval VARCHAR,
            stripe_status VARCHAR,
            price_id VARCHAR,
            start_date TIMESTAMP,
            current_period_start TIMESTAMP,
            current_period_end TIMESTAMP,
            cancel_at_period_end BOOLEAN,
            canceled_at TIMESTAMP,
            ended_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert data
    for sub in subs:
        # Convert Unix timestamps to datetime
        start_date = datetime.fromtimestamp(sub['startDate']) if sub.get('startDate') else None
        current_period_start = datetime.fromtimestamp(sub['currentPeriodStart']) if sub.get('currentPeriodStart') else None
        current_period_end = datetime.fromtimestamp(sub['currentPeriodEnd']) if sub.get('currentPeriodEnd') else None
        canceled_at = datetime.fromtimestamp(sub['canceledAt']) if sub.get('canceledAt') else None
        ended_at = datetime.fromtimestamp(sub['endedAt']) if sub.get('endedAt') else None

        conn.execute("""
            INSERT INTO mongo_subscriptions
            (id, subscription_id, user_id, company_id, type, amount, interval, stripe_status,
             price_id, start_date, current_period_start, current_period_end,
             cancel_at_period_end, canceled_at, ended_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(sub.get('_id', '')),
            sub.get('subscriptionId'),
            str(sub.get('userId', '')) if sub.get('userId') else None,
            str(sub.get('companyId', '')) if sub.get('companyId') else None,
            sub.get('type'),
            sub.get('amount', 0),
            sub.get('interval'),
            sub.get('stripeStatus'),
            sub.get('priceId'),
            start_date,
            current_period_start,
            current_period_end,
            sub.get('cancelAtPeriodEnd', False),
            canceled_at,
            ended_at,
            sub.get('createdAt'),
            sub.get('updatedAt')
        ])

    log(f"  Saved {len(subs)} rows to mongo_subscriptions")
    return len(subs)


def sync_payments(db, conn):
    """Sync stripePayments collection."""
    log("Fetching stripe payments...")

    payments = list(db['stripePayments'].find())
    log(f"  Got {len(payments)} payments")

    if not payments:
        return 0

    # Create table
    conn.execute("""
        CREATE OR REPLACE TABLE mongo_payments (
            id VARCHAR PRIMARY KEY,
            payment_intent_id VARCHAR,
            user_id VARCHAR,
            company_id VARCHAR,
            email VARCHAR,
            amount INTEGER,
            currency VARCHAR,
            method VARCHAR,
            payment_status VARCHAR,
            stripe_status VARCHAR,
            last4 VARCHAR,
            description VARCHAR,
            receipt_url VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert data
    for p in payments:
        conn.execute("""
            INSERT INTO mongo_payments
            (id, payment_intent_id, user_id, company_id, email, amount, currency, method,
             payment_status, stripe_status, last4, description, receipt_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(p.get('_id', '')),
            p.get('paymentIntentId'),
            str(p.get('userId', '')) if p.get('userId') else None,
            str(p.get('companyId', '')) if p.get('companyId') else None,
            p.get('email'),
            p.get('amount', 0),
            p.get('currency', 'usd'),
            p.get('method'),
            p.get('paymentStatus'),
            p.get('stripeStatus'),
            p.get('last4'),
            p.get('description'),
            p.get('receiptUrl'),
            p.get('createdAt'),
            p.get('updatedAt')
        ])

    log(f"  Saved {len(payments)} rows to mongo_payments")
    return len(payments)


def sync_companies(db, conn):
    """Sync companies collection."""
    log("Fetching companies...")

    companies = list(db['companies'].find())
    log(f"  Got {len(companies)} companies")

    if not companies:
        return 0

    # Create table
    conn.execute("""
        CREATE OR REPLACE TABLE mongo_companies (
            id VARCHAR PRIMARY KEY,
            name VARCHAR,
            owner_id VARCHAR,
            subscription_type VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert data
    for c in companies:
        conn.execute("""
            INSERT INTO mongo_companies
            (id, name, owner_id, subscription_type, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            str(c.get('_id', '')),
            c.get('name'),
            str(c.get('ownerId', '')) if c.get('ownerId') else None,
            c.get('subscriptionType'),
            c.get('createdAt'),
            c.get('updatedAt')
        ])

    log(f"  Saved {len(companies)} rows to mongo_companies")
    return len(companies)


def sync_orders(db, conn):
    """Sync orders collection (domain purchases via guest post/link insertion)."""
    log("Fetching orders...")

    orders = list(db['orders'].find())
    log(f"  Got {len(orders)} orders")

    if not orders:
        return 0

    # Create table
    conn.execute("""
        CREATE OR REPLACE TABLE mongo_orders (
            id VARCHAR PRIMARY KEY,
            order_id INTEGER,
            user_id VARCHAR,
            company_id VARCHAR,
            domain VARCHAR,
            price DOUBLE,
            status VARCHAR,
            payment_status VARCHAR,
            buyer_email VARCHAR,
            seller_email VARCHAR,
            stripe_payment_id VARCHAR,
            doc_url VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert data
    for o in orders:
        conn.execute("""
            INSERT INTO mongo_orders
            (id, order_id, user_id, company_id, domain, price, status, payment_status,
             buyer_email, seller_email, stripe_payment_id, doc_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(o.get('_id', '')),
            o.get('orderId'),
            str(o.get('userId', '')) if o.get('userId') else None,
            str(o.get('companyId', '')) if o.get('companyId') else None,
            o.get('link'),  # MongoDB field is 'link', not 'domain'
            o.get('price', 0),
            o.get('status'),
            o.get('paymentStatus'),
            o.get('buyerEmail'),
            o.get('sellerEmail'),
            str(o.get('stripePaymentId', '')) if o.get('stripePaymentId') else None,
            o.get('docUrl'),
            o.get('createdAt'),
            o.get('updatedAt')
        ])

    log(f"  Saved {len(orders)} rows to mongo_orders")
    return len(orders)


def sync_user_unlocks(db, conn):
    """Sync userUnlocks collection."""
    log("Fetching user unlocks...")

    unlocks = list(db['userUnlocks'].find())
    log(f"  Got {len(unlocks)} unlocks")

    if not unlocks:
        return 0

    # Create table
    conn.execute("""
        CREATE OR REPLACE TABLE mongo_user_unlocks (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR,
            company_id VARCHAR,
            domain_id VARCHAR,
            domain VARCHAR,
            created_at TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert data
    for u in unlocks:
        conn.execute("""
            INSERT INTO mongo_user_unlocks
            (id, user_id, company_id, domain_id, domain, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            str(u.get('_id', '')),
            str(u.get('userId', '')) if u.get('userId') else None,
            str(u.get('companyId', '')) if u.get('companyId') else None,
            str(u.get('domainId', '')) if u.get('domainId') else None,
            u.get('domain'),
            u.get('createdAt')
        ])

    log(f"  Saved {len(unlocks)} rows to mongo_user_unlocks")
    return len(unlocks)


def sync_internal_payments(db, conn):
    """Sync internalPayments collection (unit spending transactions)."""
    log("Fetching internal payments (unit transactions)...")

    payments = list(db['internalPayments'].find())
    log(f"  Got {len(payments)} transactions")

    if not payments:
        return 0

    # Create table
    conn.execute("""
        CREATE OR REPLACE TABLE mongo_internal_payments (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR,
            company_id VARCHAR,
            amount INTEGER,
            action_type VARCHAR,
            status VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Insert data
    for p in payments:
        conn.execute("""
            INSERT INTO mongo_internal_payments
            (id, user_id, company_id, amount, action_type, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(p.get('_id', '')),
            str(p.get('userId', '')) if p.get('userId') else None,
            str(p.get('companyId', '')) if p.get('companyId') else None,
            p.get('amount', 0),
            p.get('actionType'),
            p.get('status'),
            p.get('createdAt'),
            p.get('updatedAt')
        ])

    log(f"  Saved {len(payments)} rows to mongo_internal_payments")
    return len(payments)


def sync_projects(db, conn):
    """Sync projects collection (user project folders)."""
    log("Fetching projects...")

    projects = list(db['projects'].find())
    log(f"  Got {len(projects)} projects")

    if not projects:
        return 0

    conn.execute("""
        CREATE OR REPLACE TABLE mongo_projects (
            id VARCHAR PRIMARY KEY,
            user_id VARCHAR,
            company_id VARCHAR,
            name VARCHAR,
            domain VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for p in projects:
        conn.execute("""
            INSERT INTO mongo_projects
            (id, user_id, company_id, name, domain, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            str(p.get('_id', '')),
            str(p.get('userId', '')) if p.get('userId') else None,
            str(p.get('companyId', '')) if p.get('companyId') else None,
            p.get('name'),
            p.get('domain'),
            p.get('createdAt'),
            p.get('updatedAt')
        ])

    log(f"  Saved {len(projects)} rows to mongo_projects")
    return len(projects)


def sync_project_prospects(db, conn):
    """Sync projectProspects collection (publishers saved to projects)."""
    log("Fetching project prospects...")

    prospects = list(db['projectProspects'].find())
    log(f"  Got {len(prospects)} prospects")

    if not prospects:
        return 0

    conn.execute("""
        CREATE OR REPLACE TABLE mongo_project_prospects (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR,
            user_id VARCHAR,
            company_id VARCHAR,
            domain VARCHAR,
            status VARCHAR,
            live_link VARCHAR,
            order_price DOUBLE,
            placed_via VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for p in prospects:
        conn.execute("""
            INSERT INTO mongo_project_prospects
            (id, project_id, user_id, company_id, domain, status, live_link, order_price, placed_via, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(p.get('_id', '')),
            str(p.get('projectId', '')) if p.get('projectId') else None,
            str(p.get('userId', '')) if p.get('userId') else None,
            str(p.get('companyId', '')) if p.get('companyId') else None,
            p.get('domain'),
            p.get('status'),
            p.get('liveLink'),
            p.get('orderPrice'),
            p.get('placedVia'),
            p.get('createdAt'),
            p.get('updatedAt')
        ])

    log(f"  Saved {len(prospects)} rows to mongo_project_prospects")
    return len(prospects)


def sync_project_completed_orders(db, conn):
    """Sync projectCompletedOrders collection (backlinks purchased via projects)."""
    log("Fetching project completed orders...")

    orders = list(db['projectCompletedOrders'].find())
    log(f"  Got {len(orders)} completed orders")

    if not orders:
        return 0

    conn.execute("""
        CREATE OR REPLACE TABLE mongo_project_completed_orders (
            id VARCHAR PRIMARY KEY,
            project_id VARCHAR,
            user_id VARCHAR,
            domain VARCHAR,
            live_link VARCHAR,
            placed_via VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    for o in orders:
        conn.execute("""
            INSERT INTO mongo_project_completed_orders
            (id, project_id, user_id, domain, live_link, placed_via, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            str(o.get('_id', '')),
            str(o.get('projectId', '')) if o.get('projectId') else None,
            str(o.get('userId', '')) if o.get('userId') else None,
            o.get('domain'),
            o.get('liveLink'),
            o.get('placedVia'),
            o.get('createdAt'),
            o.get('updatedAt')
        ])

    log(f"  Saved {len(orders)} rows to mongo_project_completed_orders")
    return len(orders)


def main():
    parser = argparse.ArgumentParser(description='Sync MongoDB data to DuckDB')
    parser.add_argument('--incremental', action='store_true',
                        help='Only sync new records (not implemented yet)')
    args = parser.parse_args()

    print("=" * 60)
    print("MongoDB → DuckDB Sync")
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

        total_rows += sync_users(db, conn)
        total_rows += sync_subscriptions(db, conn)
        total_rows += sync_payments(db, conn)
        total_rows += sync_companies(db, conn)
        total_rows += sync_orders(db, conn)
        total_rows += sync_user_unlocks(db, conn)
        total_rows += sync_internal_payments(db, conn)
        total_rows += sync_projects(db, conn)
        total_rows += sync_project_prospects(db, conn)
        total_rows += sync_project_completed_orders(db, conn)

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
