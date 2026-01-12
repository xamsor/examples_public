#!/usr/bin/env python3
"""
Simple MongoDB data export script
Usage: python3 mongo_export.py <collection_name> [format] [limit]

Databases available:
- publishers (MONGO_PUBLISHERS_URI): Publisher data from 116.203.48.70:27017
- getlinks_pro_prod (MONGO_URI): GetLinks Pro data from 5.161.52.116:27018
"""

import sys
import csv
import json
import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Database configurations
DATABASES = {
    'publishers': os.getenv('MONGO_PUBLISHERS_URI', 'mongodb://pub_w:StrongPassword123%40%40%26%261a@116.203.48.70:27017/publishers'),
    'getlinks': os.getenv('MONGO_URI', 'mongodb://read_user:Kd4VbFRvPu5u@5.161.52.116:27018/?authMechanism=DEFAULT&authSource=getlinks_pro_prod&directConnection=true'),
}

def export_collection(collection_name, db_name='publishers', format='csv', limit=None):
    connection_string = DATABASES.get(db_name, DATABASES['publishers'])

    try:
        print(f"Connecting to MongoDB ({db_name})...")
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)

        # Get database name from connection string or use default
        if db_name == 'publishers':
            db = client.publishers
        else:
            db = client.getlinks_pro_prod

        # Check if collection exists
        if collection_name not in db.list_collection_names():
            print(f"Collection '{collection_name}' not found!")
            print("Available collections:")
            for col in db.list_collection_names():
                print(f"  - {col}")
            return False

        collection = db[collection_name]
        total_docs = collection.count_documents({})

        print(f"Collection: {collection_name}")
        print(f"Total documents: {total_docs}")

        # Set limit
        if limit:
            limit = min(int(limit), total_docs)
            print(f"Exporting {limit} documents")
        else:
            limit = total_docs
            print(f"Exporting all {total_docs} documents")

        # Get documents
        print("Fetching data...")
        cursor = collection.find().limit(limit)
        documents = list(cursor)

        if not documents:
            print("No documents found!")
            return False

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{collection_name}_{timestamp}.{format}"

        # Export based on format
        if format.lower() == 'csv':
            export_to_csv(documents, filename)
        elif format.lower() == 'json':
            export_to_json(documents, filename)
        else:
            print(f"Unsupported format: {format}")
            return False

        print(f"Export completed: {filename}")
        print(f"Exported {len(documents)} documents")
        return True

    except Exception as e:
        print(f"Export failed: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def export_to_csv(documents, filename):
    """Export documents to CSV format"""
    print(f"Saving as CSV: {filename}")

    # Get all unique keys from all documents
    all_keys = set()
    for doc in documents:
        all_keys.update(doc.keys())

    # Remove _id if present and add it at the beginning
    if '_id' in all_keys:
        all_keys.remove('_id')
        fieldnames = ['_id'] + sorted(list(all_keys))
    else:
        fieldnames = sorted(list(all_keys))

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for doc in documents:
            # Convert ObjectId to string and handle complex types
            row = {}
            for key in fieldnames:
                value = doc.get(key, '')
                if hasattr(value, '__iter__') and not isinstance(value, str):
                    # Convert lists/dicts to JSON string
                    row[key] = json.dumps(value, default=str)
                else:
                    row[key] = str(value) if value is not None else ''
            writer.writerow(row)

def export_to_json(documents, filename):
    """Export documents to JSON format"""
    print(f"Saving as JSON: {filename}")

    # Convert ObjectId to string for JSON serialization
    json_docs = []
    for doc in documents:
        json_doc = {}
        for key, value in doc.items():
            json_doc[key] = str(value) if hasattr(value, '__str__') else value
        json_docs.append(json_doc)

    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(json_docs, jsonfile, indent=2, ensure_ascii=False, default=str)

def list_collections(db_name='publishers'):
    """List all collections in a database"""
    connection_string = DATABASES.get(db_name, DATABASES['publishers'])

    try:
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)

        if db_name == 'publishers':
            db = client.publishers
        else:
            db = client.getlinks_pro_prod

        collections = db.list_collection_names()
        print(f"\nCollections in {db_name}:")
        for i, col in enumerate(collections, 1):
            doc_count = db[col].count_documents({})
            print(f"  {i:2d}. {col:<30} ({doc_count:,} docs)")
        client.close()
        return collections
    except Exception as e:
        print(f"Could not list collections: {e}")
        return []

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mongo_export.py <collection_name> [db_name] [format] [limit]")
        print("DB names: publishers, getlinks (default: publishers)")
        print("Formats: csv, json (default: csv)")
        print("Limit: number of documents to export (default: all)")

        print("\n--- Publishers DB ---")
        list_collections('publishers')
        print("\n--- GetLinks DB ---")
        list_collections('getlinks')
        return

    collection_name = sys.argv[1]
    db_name = sys.argv[2] if len(sys.argv) > 2 else 'publishers'
    format_type = sys.argv[3] if len(sys.argv) > 3 else 'csv'
    limit = sys.argv[4] if len(sys.argv) > 4 else None

    export_collection(collection_name, db_name, format_type, limit)

if __name__ == "__main__":
    main()
