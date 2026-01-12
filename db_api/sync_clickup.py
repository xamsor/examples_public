#!/usr/bin/env python3
"""
Sync ClickUp Orders to DuckDB.

Usage:
    python3 db_api/sync_clickup.py          # Sync all orders
    python3 db_api/sync_clickup.py --init   # Re-create tables and sync
"""

import os
import sys
import re
import argparse
from datetime import datetime
from dotenv import load_dotenv
import requests
import duckdb

load_dotenv()

# ClickUp config
CLICKUP_API_KEY = os.getenv("CLICKUP_API_KEY")
ORDERS_LIST_ID = "901210524636"
BASE_URL = "https://api.clickup.com/api/v2"

# DuckDB config
DUCKDB_PATH = os.path.join(os.path.dirname(__file__), "..", "warehouse.duckdb")

HEADERS = {
    "Authorization": CLICKUP_API_KEY,
    "Content-Type": "application/json"
}


def get_connection():
    return duckdb.connect(DUCKDB_PATH)


def init_tables(conn):
    """Create or recreate tables."""
    conn.execute("DROP TABLE IF EXISTS clickup_order_comments")
    conn.execute("DROP TABLE IF EXISTS clickup_order_attachments")
    conn.execute("DROP TABLE IF EXISTS clickup_orders")

    conn.execute("""
        CREATE TABLE clickup_orders (
            task_id VARCHAR PRIMARY KEY,
            name VARCHAR,
            order_number INTEGER,
            order_type VARCHAR,
            domain VARCHAR,
            amount_usd DECIMAL(10,2),
            customer_email VARCHAR,
            status VARCHAR,
            status_type VARCHAR,
            date_created TIMESTAMP,
            date_updated TIMESTAMP,
            date_done TIMESTAMP,
            creator_id INTEGER,
            creator_name VARCHAR,
            creator_email VARCHAR,
            assignee_names VARCHAR,
            assignee_emails VARCHAR,
            description TEXT,
            url VARCHAR,
            attachment_count INTEGER,
            synced_at TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE clickup_order_comments (
            comment_id VARCHAR PRIMARY KEY,
            task_id VARCHAR,
            comment_text TEXT,
            user_id INTEGER,
            user_name VARCHAR,
            user_email VARCHAR,
            date_posted TIMESTAMP,
            synced_at TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE clickup_order_attachments (
            attachment_id VARCHAR PRIMARY KEY,
            task_id VARCHAR,
            title VARCHAR,
            extension VARCHAR,
            mimetype VARCHAR,
            size_bytes INTEGER,
            url VARCHAR,
            date_added TIMESTAMP,
            synced_at TIMESTAMP
        )
    """)

    print("Tables created.")


def ensure_tables(conn):
    """Create tables if they don't exist."""
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]

    if "clickup_orders" not in table_names:
        init_tables(conn)
        return True
    return False


def parse_task_name(name):
    """Parse order details from task name."""
    # Pattern: "ORDER_NUM, TYPE, DOMAIN, $AMOUNT, EMAIL"
    # Handle optional "ACTION REQUIRED!" prefix
    pattern = r'^(?:ACTION REQUIRED!\s*)?(\d+),\s*([^,]+),\s*([^,]+),\s*\$?([\d.]+),\s*(.+?)\"?$'
    match = re.match(pattern, name)

    if match:
        try:
            return {
                "order_number": int(match.group(1)),
                "order_type": match.group(2).strip(),
                "domain": match.group(3).strip(),
                "amount_usd": float(match.group(4)) if match.group(4) and match.group(4) != '.' else None,
                "customer_email": match.group(5).strip().rstrip('"')
            }
        except (ValueError, TypeError):
            pass

    # Try alternate patterns
    # Pattern: "ID XX, domain, $amount, email"
    pattern2 = r'^ID\s*(\d+),?\s*([^,\$]+),?\s*\$?([\d.]+),?\s*(.+?)\"?$'
    match = re.match(pattern2, name)
    if match:
        try:
            amount = match.group(3)
            return {
                "order_number": int(match.group(1)),
                "order_type": None,
                "domain": match.group(2).strip(),
                "amount_usd": float(amount) if amount and amount != '.' else None,
                "customer_email": match.group(4).strip().rstrip('"')
            }
        except (ValueError, TypeError):
            pass

    # Try to extract just order number
    order_match = re.match(r'^(?:ACTION REQUIRED!\s*)?(?:ID\s*)?(\d+)', name)
    order_num = int(order_match.group(1)) if order_match else None

    # Try to extract domain
    domain_match = re.search(r'([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)', name)
    domain = domain_match.group(1) if domain_match else None

    # Try to extract amount
    amount_match = re.search(r'\$?([\d]+\.?\d*)', name)
    amount = None
    if amount_match:
        try:
            amount = float(amount_match.group(1))
        except ValueError:
            pass

    # Try to extract email
    email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', name)
    email = email_match.group(1) if email_match else None

    return {
        "order_number": order_num,
        "order_type": None,
        "domain": domain,
        "amount_usd": amount,
        "customer_email": email
    }


def ts_to_datetime(ts):
    """Convert ClickUp timestamp (ms) to datetime."""
    if ts:
        return datetime.fromtimestamp(int(ts) / 1000)
    return None


def fetch_all_tasks():
    """Fetch all tasks from Orders list."""
    url = f"{BASE_URL}/list/{ORDERS_LIST_ID}/task"
    params = {"include_closed": "true", "subtasks": "true"}

    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json().get("tasks", [])


def fetch_task_comments(task_id):
    """Fetch comments for a task."""
    url = f"{BASE_URL}/task/{task_id}/comment"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("comments", [])
    return []


def fetch_task_attachments(task_id):
    """Fetch full task details to get attachments."""
    url = f"{BASE_URL}/task/{task_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("attachments", [])
    return []


def sync_orders(conn, full_sync=False):
    """Sync orders from ClickUp to DuckDB."""
    now = datetime.now()

    # Get existing task IDs and their update times
    existing = {}
    if not full_sync:
        try:
            rows = conn.execute(
                "SELECT task_id, date_updated FROM clickup_orders"
            ).fetchall()
            existing = {r[0]: r[1] for r in rows}
        except:
            pass

    # Fetch all tasks
    print("Fetching tasks from ClickUp...")
    tasks = fetch_all_tasks()
    print(f"Found {len(tasks)} tasks")

    new_count = 0
    updated_count = 0

    for task in tasks:
        task_id = task["id"]
        date_updated = ts_to_datetime(task.get("date_updated"))

        # Check if needs update
        if task_id in existing:
            if existing[task_id] and date_updated and existing[task_id] >= date_updated:
                continue  # No changes

        # Parse name
        parsed = parse_task_name(task["name"])

        # Assignees
        assignee_names = ", ".join([a["username"] for a in task.get("assignees", [])])
        assignee_emails = ", ".join([a["email"] for a in task.get("assignees", [])])

        # Upsert order
        conn.execute("""
            INSERT OR REPLACE INTO clickup_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            task_id,
            task["name"],
            parsed["order_number"],
            parsed["order_type"],
            parsed["domain"],
            parsed["amount_usd"],
            parsed["customer_email"],
            task["status"]["status"],
            task["status"].get("type"),
            ts_to_datetime(task.get("date_created")),
            date_updated,
            ts_to_datetime(task.get("date_done")),
            task["creator"]["id"],
            task["creator"]["username"],
            task["creator"]["email"],
            assignee_names,
            assignee_emails,
            task.get("text_content"),
            task.get("url"),
            len(task.get("attachments", [])) if "attachments" in task else 0,
            now
        ])

        if task_id in existing:
            updated_count += 1
        else:
            new_count += 1

        # Sync comments
        print(f"  Syncing comments for {task_id}...")
        comments = fetch_task_comments(task_id)
        for comment in comments:
            conn.execute("""
                INSERT OR REPLACE INTO clickup_order_comments VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                comment["id"],
                task_id,
                comment.get("comment_text"),
                comment["user"]["id"],
                comment["user"]["username"],
                comment["user"]["email"],
                ts_to_datetime(comment.get("date")),
                now
            ])

        # Sync attachments (need full task details)
        attachments = fetch_task_attachments(task_id)
        for att in attachments:
            conn.execute("""
                INSERT OR REPLACE INTO clickup_order_attachments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                att["id"],
                task_id,
                att.get("title"),
                att.get("extension"),
                att.get("mimetype"),
                att.get("size"),
                att.get("url"),
                ts_to_datetime(att.get("date")),
                now
            ])

    return new_count, updated_count, len(tasks)


def main():
    parser = argparse.ArgumentParser(description="Sync ClickUp Orders to DuckDB")
    parser.add_argument("--init", action="store_true", help="Re-create tables")
    args = parser.parse_args()

    conn = get_connection()

    if args.init:
        print("Initializing tables...")
        init_tables(conn)
        full_sync = True
    else:
        full_sync = ensure_tables(conn)

    print("Starting sync...")
    new_count, updated_count, total = sync_orders(conn, full_sync)

    print(f"\nSync complete:")
    print(f"  Total tasks: {total}")
    print(f"  New: {new_count}")
    print(f"  Updated: {updated_count}")
    print(f"  Unchanged: {total - new_count - updated_count}")

    # Show summary
    print("\n=== DuckDB Summary ===")
    orders = conn.execute("SELECT COUNT(*) FROM clickup_orders").fetchone()[0]
    comments = conn.execute("SELECT COUNT(*) FROM clickup_order_comments").fetchone()[0]
    attachments = conn.execute("SELECT COUNT(*) FROM clickup_order_attachments").fetchone()[0]
    print(f"  Orders: {orders}")
    print(f"  Comments: {comments}")
    print(f"  Attachments: {attachments}")

    conn.close()


if __name__ == "__main__":
    main()
