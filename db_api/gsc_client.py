#!/usr/bin/env python3
"""
Google Search Console API client

Uses service account authentication to fetch search performance data.

Usage:
    python3 db_api/gsc_client.py                         # Test connection, last 7 days summary
    python3 db_api/gsc_client.py queries                 # Top search queries
    python3 db_api/gsc_client.py pages                   # Top pages
    python3 db_api/gsc_client.py countries               # Performance by country
    python3 db_api/gsc_client.py devices                 # Performance by device
    python3 db_api/gsc_client.py "query filter"          # Search for specific query
"""

import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

# Check for required package
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print("Required packages not installed. Run:")
    print("  pip3 install google-api-python-client google-auth")
    sys.exit(1)

# Configuration
GSC_SITE_URL = os.getenv('GSC_SITE_URL', 'https://fatgrid.com/')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    'GOOGLE_SERVICE_ACCOUNT_FILE',
    os.path.join(os.path.dirname(__file__), 'getlinkspro-453615-c0e5ea39671a.json')
)


class GSCClient:
    def __init__(self, site_url=None, credentials_file=None):
        self.site_url = site_url or GSC_SITE_URL
        self.credentials_file = credentials_file or GOOGLE_SERVICE_ACCOUNT_FILE

        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Service account file not found: {self.credentials_file}")

        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_file,
            scopes=['https://www.googleapis.com/auth/webmasters.readonly']
        )
        self.service = build('searchconsole', 'v1', credentials=credentials)

    def query(self, start_date=None, end_date=None, dimensions=None, filters=None, row_limit=25):
        """
        Query Search Console data

        Args:
            start_date: Start date (YYYY-MM-DD), defaults to 7 days ago
            end_date: End date (YYYY-MM-DD), defaults to today
            dimensions: List of dimensions ['query', 'page', 'country', 'device', 'date']
            filters: List of filter dicts with 'dimension', 'operator', 'expression'
            row_limit: Max rows to return (max 25000)
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        request = {
            'startDate': start_date,
            'endDate': end_date,
            'rowLimit': row_limit
        }

        if dimensions:
            request['dimensions'] = dimensions
        if filters:
            request['dimensionFilterGroups'] = [{'filters': filters}]

        response = self.service.searchanalytics().query(
            siteUrl=self.site_url,
            body=request
        ).execute()

        return response

    def get_summary(self, days=7):
        """Get overall performance summary"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        return self.query(start_date, end_date, dimensions=['date'])

    def get_top_queries(self, days=7, limit=25):
        """Get top search queries"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        return self.query(start_date, end_date, dimensions=['query'], row_limit=limit)

    def get_top_pages(self, days=7, limit=25):
        """Get top pages"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        return self.query(start_date, end_date, dimensions=['page'], row_limit=limit)

    def get_countries(self, days=7, limit=15):
        """Get performance by country"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        return self.query(start_date, end_date, dimensions=['country'], row_limit=limit)

    def get_devices(self, days=7):
        """Get performance by device"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        return self.query(start_date, end_date, dimensions=['device'])

    def search_query(self, query_filter, days=7, limit=25):
        """Search for specific query containing text"""
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        filters = [{
            'dimension': 'query',
            'operator': 'contains',
            'expression': query_filter
        }]
        return self.query(start_date, end_date, dimensions=['query'], filters=filters, row_limit=limit)

    def list_sites(self):
        """List all sites accessible by this service account"""
        response = self.service.sites().list().execute()
        return response.get('siteEntry', [])


def print_report(response, title, dimensions=None):
    """Pretty print a GSC report response"""
    print(f"\n{title}")
    print("=" * 80)

    rows = response.get('rows', [])
    if not rows:
        print("No data")
        return

    # Print header
    headers = (dimensions or []) + ['Clicks', 'Impressions', 'CTR', 'Position']
    print(" | ".join(f"{h:<25}" for h in headers))
    print("-" * 80)

    # Print rows
    for row in rows:
        keys = row.get('keys', [])
        clicks = row.get('clicks', 0)
        impressions = row.get('impressions', 0)
        ctr = row.get('ctr', 0) * 100
        position = row.get('position', 0)

        values = keys + [str(clicks), str(impressions), f"{ctr:.1f}%", f"{position:.1f}"]
        print(" | ".join(f"{v:<25}" for v in values))


def main():
    try:
        client = GSCClient()
        print(f"Search Console Site: {client.site_url}")
        print(f"Credentials: {os.path.basename(client.credentials_file)}")
    except Exception as e:
        print(f"Failed to initialize GSC client: {e}")
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else 'summary'

    try:
        if cmd == 'sites':
            sites = client.list_sites()
            print("\nAccessible Sites:")
            for site in sites:
                print(f"  - {site.get('siteUrl')} ({site.get('permissionLevel')})")
        elif cmd == 'queries':
            response = client.get_top_queries()
            print_report(response, "Top Search Queries (Last 7 Days)", ['Query'])
        elif cmd == 'pages':
            response = client.get_top_pages()
            print_report(response, "Top Pages (Last 7 Days)", ['Page'])
        elif cmd == 'countries':
            response = client.get_countries()
            print_report(response, "Performance by Country (Last 7 Days)", ['Country'])
        elif cmd == 'devices':
            response = client.get_devices()
            print_report(response, "Performance by Device (Last 7 Days)", ['Device'])
        elif cmd == 'summary':
            response = client.get_summary()
            print_report(response, "Daily Performance (Last 7 Days)", ['Date'])
        else:
            # Treat as query filter
            response = client.search_query(cmd)
            print_report(response, f"Queries containing '{cmd}' (Last 7 Days)", ['Query'])

        print("\nGSC connection successful!")

    except Exception as e:
        print(f"Error: {e}")
        if 'forbidden' in str(e).lower() or '403' in str(e):
            print("\nMake sure the service account email has access to Search Console:")
            print(f"  Email: fatgrid-gsc-indexing@getlinkspro-453615.iam.gserviceaccount.com")
            print(f"  Site: {client.site_url}")
        sys.exit(1)


if __name__ == "__main__":
    main()
