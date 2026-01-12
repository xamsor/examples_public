#!/usr/bin/env python3
"""
Google Analytics 4 Data API client

Uses service account authentication to fetch GA4 reports.

Usage:
    python3 db_api/ga4_client.py                    # Test connection, show last 7 days
    python3 db_api/ga4_client.py realtime           # Realtime active users
    python3 db_api/ga4_client.py pages              # Top pages last 7 days
    python3 db_api/ga4_client.py sources            # Traffic sources last 7 days
    python3 db_api/ga4_client.py countries          # Top countries last 7 days
"""

import os
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

# Check for required package
try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest,
        RunRealtimeReportRequest,
        DateRange,
        Dimension,
        Metric,
    )
    from google.oauth2 import service_account
except ImportError:
    print("Required packages not installed. Run:")
    print("  pip3 install google-analytics-data google-auth")
    sys.exit(1)

# Configuration
GA4_PROPERTY_ID = os.getenv('GA4_PROPERTY_ID', '480666040')
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    'GOOGLE_SERVICE_ACCOUNT_FILE',
    os.path.join(os.path.dirname(__file__), 'getlinkspro-453615-c0e5ea39671a.json')
)


class GA4Client:
    def __init__(self, property_id=None, credentials_file=None):
        self.property_id = property_id or GA4_PROPERTY_ID
        self.credentials_file = credentials_file or GOOGLE_SERVICE_ACCOUNT_FILE

        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Service account file not found: {self.credentials_file}")

        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_file,
            scopes=['https://www.googleapis.com/auth/analytics.readonly']
        )
        self.client = BetaAnalyticsDataClient(credentials=credentials)
        self.property = f"properties/{self.property_id}"

    def run_report(self, dimensions, metrics, start_date='7daysAgo', end_date='today', limit=10):
        """Run a GA4 report with specified dimensions and metrics"""
        request = RunReportRequest(
            property=self.property,
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=limit
        )
        return self.client.run_report(request)

    def get_realtime(self):
        """Get realtime active users"""
        request = RunRealtimeReportRequest(
            property=self.property,
            dimensions=[Dimension(name='country')],
            metrics=[Metric(name='activeUsers')]
        )
        return self.client.run_realtime_report(request)

    def get_overview(self, start_date='7daysAgo', end_date='today'):
        """Get basic traffic overview"""
        return self.run_report(
            dimensions=['date'],
            metrics=['sessions', 'totalUsers', 'newUsers', 'screenPageViews', 'averageSessionDuration'],
            start_date=start_date,
            end_date=end_date,
            limit=30
        )

    def get_top_pages(self, start_date='7daysAgo', end_date='today', limit=20):
        """Get top pages by pageviews"""
        return self.run_report(
            dimensions=['pagePath'],
            metrics=['screenPageViews', 'totalUsers', 'averageSessionDuration'],
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

    def get_traffic_sources(self, start_date='7daysAgo', end_date='today', limit=10):
        """Get traffic sources"""
        return self.run_report(
            dimensions=['sessionSource', 'sessionMedium'],
            metrics=['sessions', 'totalUsers', 'newUsers'],
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

    def get_countries(self, start_date='7daysAgo', end_date='today', limit=15):
        """Get top countries"""
        return self.run_report(
            dimensions=['country'],
            metrics=['sessions', 'totalUsers', 'screenPageViews'],
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

    def get_devices(self, start_date='7daysAgo', end_date='today'):
        """Get device breakdown"""
        return self.run_report(
            dimensions=['deviceCategory'],
            metrics=['sessions', 'totalUsers'],
            start_date=start_date,
            end_date=end_date,
            limit=10
        )


def print_report(response, title):
    """Pretty print a GA4 report response"""
    print(f"\n{title}")
    print("=" * 60)

    if not response.rows:
        print("No data")
        return

    # Get headers
    dim_headers = [h.name for h in response.dimension_headers]
    metric_headers = [h.name for h in response.metric_headers]

    # Print header
    header = dim_headers + metric_headers
    print(" | ".join(f"{h:<20}" for h in header))
    print("-" * 60)

    # Print rows
    for row in response.rows:
        dims = [d.value for d in row.dimension_values]
        metrics = [m.value for m in row.metric_values]
        values = dims + metrics
        print(" | ".join(f"{v:<20}" for v in values))


def main():
    try:
        client = GA4Client()
        print(f"GA4 Property: {client.property_id}")
        print(f"Credentials: {os.path.basename(client.credentials_file)}")
    except Exception as e:
        print(f"Failed to initialize GA4 client: {e}")
        sys.exit(1)

    cmd = sys.argv[1] if len(sys.argv) > 1 else 'overview'

    try:
        if cmd == 'realtime':
            response = client.get_realtime()
            print_report(response, "Realtime Active Users by Country")
        elif cmd == 'pages':
            response = client.get_top_pages()
            print_report(response, "Top Pages (Last 7 Days)")
        elif cmd == 'sources':
            response = client.get_traffic_sources()
            print_report(response, "Traffic Sources (Last 7 Days)")
        elif cmd == 'countries':
            response = client.get_countries()
            print_report(response, "Top Countries (Last 7 Days)")
        elif cmd == 'devices':
            response = client.get_devices()
            print_report(response, "Devices (Last 7 Days)")
        else:  # overview
            response = client.get_overview()
            print_report(response, "Traffic Overview (Last 7 Days)")

        print("\nGA4 connection successful!")

    except Exception as e:
        print(f"Error running report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
