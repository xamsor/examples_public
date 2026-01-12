#!/usr/bin/env python3
"""
MongoDB connection test and database exploration script
Tests both Publishers and GetLinks Pro databases
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    from pymongo import MongoClient
except ImportError:
    print("pymongo not installed. Install with: pip3 install pymongo")
    exit(1)

# Database configurations
DATABASES = {
    'publishers': {
        'uri': os.getenv('MONGO_PUBLISHERS_URI', 'mongodb://pub_w:StrongPassword123%40%40%26%261a@116.203.48.70:27017/publishers'),
        'db_name': 'publishers',
        'description': 'Publisher data (116.203.48.70:27017)'
    },
    'getlinks': {
        'uri': os.getenv('MONGO_URI', 'mongodb://read_user:Kd4VbFRvPu5u@5.161.52.116:27018/?authMechanism=DEFAULT&authSource=getlinks_pro_prod&directConnection=true'),
        'db_name': 'getlinks_pro_prod',
        'description': 'GetLinks Pro Prod (5.161.52.116:27018)'
    }
}

def test_mongo_connection(db_key='publishers'):
    config = DATABASES.get(db_key)
    if not config:
        print(f"Unknown database: {db_key}")
        return False

    connection_string = config['uri']
    db_name = config['db_name']

    try:
        print(f"Testing MongoDB connection to {config['description']}...")
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)

        # Test connection
        client.admin.command('ping')
        print("MongoDB connection successful!")

        # Get database
        db = client[db_name]
        print(f"\nConnected to database: {db.name}")

        # List collections
        collections = db.list_collection_names()
        print(f"\nCollections in database ({len(collections)}):")
        for i, collection in enumerate(collections, 1):
            print(f"  {i}. {collection}")

        # Explore each collection
        print("\nCollection details:")
        for collection_name in collections:
            collection = db[collection_name]
            count = collection.count_documents({})
            print(f"\n  Collection: {collection_name}")
            print(f"  Documents: {count:,}")

            # Get sample document to show structure
            if count > 0:
                sample = collection.find_one()
                print(f"  Sample document structure:")
                for key in sample.keys():
                    value_type = type(sample[key]).__name__
                    print(f"    - {key}: {value_type}")

        print("\nDatabase exploration complete!")
        return True

    except Exception as e:
        print(f"Connection failed: {e}")
        return False
    finally:
        if 'client' in locals():
            client.close()

def test_all_connections():
    """Test all configured MongoDB connections"""
    print("=" * 60)
    print("MongoDB Connection Test")
    print("=" * 60)

    results = {}
    for db_key in DATABASES:
        print(f"\n{'=' * 60}")
        results[db_key] = test_mongo_connection(db_key)

    print(f"\n{'=' * 60}")
    print("Summary:")
    for db_key, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {db_key}: {status}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_mongo_connection(sys.argv[1])
    else:
        test_all_connections()
