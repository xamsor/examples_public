import os
import hmac
import hashlib
import base64
import requests
from dotenv import load_dotenv

load_dotenv()


class FathomClient:
    BASE_URL = "https://api.fathom.ai/external/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("FATHOM_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Set FATHOM_API_KEY in .env or pass it directly.")
        self.headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        if response.text:
            return response.json()
        return {}

    # Meetings
    def list_meetings(
        self,
        cursor: str = None,
        include_transcript: bool = False,
        include_summary: bool = False,
        include_action_items: bool = False,
        include_crm_matches: bool = False,
        created_after: str = None,
        created_before: str = None,
        recorded_by: list = None,
        teams: list = None,
        calendar_invitees_domains: list = None,
        calendar_invitees_domains_type: str = None,
    ) -> dict:
        """
        List meetings with optional filters.

        Args:
            cursor: Pagination cursor from previous response
            include_transcript: Include transcript in response
            include_summary: Include meeting summary
            include_action_items: Include action items
            include_crm_matches: Include CRM data
            created_after: ISO 8601 timestamp (e.g., "2025-01-01T00:00:00Z")
            created_before: ISO 8601 timestamp
            recorded_by: List of email addresses
            teams: List of team names
            calendar_invitees_domains: List of company domains to filter by
            calendar_invitees_domains_type: "all", "only_internal", or "one_or_more_external"
        """
        params = {}
        if cursor:
            params["cursor"] = cursor
        if include_transcript:
            params["include_transcript"] = "true"
        if include_summary:
            params["include_summary"] = "true"
        if include_action_items:
            params["include_action_items"] = "true"
        if include_crm_matches:
            params["include_crm_matches"] = "true"
        if created_after:
            params["created_after"] = created_after
        if created_before:
            params["created_before"] = created_before
        if recorded_by:
            params["recorded_by[]"] = recorded_by
        if teams:
            params["teams[]"] = teams
        if calendar_invitees_domains:
            params["calendar_invitees_domains[]"] = calendar_invitees_domains
        if calendar_invitees_domains_type:
            params["calendar_invitees_domains_type"] = calendar_invitees_domains_type

        return self._request("GET", "meetings", params=params)

    def get_all_meetings(self, **kwargs) -> list:
        """Fetch all meetings using pagination."""
        all_meetings = []
        cursor = None
        while True:
            response = self.list_meetings(cursor=cursor, **kwargs)
            all_meetings.extend(response.get("items", []))
            cursor = response.get("next_cursor")
            if not cursor:
                break
        return all_meetings

    # Recordings
    def get_transcript(self, recording_id: int, destination_url: str = None) -> dict:
        """
        Get transcript for a recording.

        Args:
            recording_id: The meeting recording ID
            destination_url: Optional URL to POST the transcript to (async mode)
        """
        params = {}
        if destination_url:
            params["destination_url"] = destination_url
        return self._request("GET", f"recordings/{recording_id}/transcript", params=params)

    def get_summary(self, recording_id: int, destination_url: str = None) -> dict:
        """
        Get summary for a recording.

        Args:
            recording_id: The meeting recording ID
            destination_url: Optional URL to POST the summary to (async mode)
        """
        params = {}
        if destination_url:
            params["destination_url"] = destination_url
        return self._request("GET", f"recordings/{recording_id}/summary", params=params)

    # Teams
    def list_teams(self) -> dict:
        """List all teams."""
        return self._request("GET", "teams")

    def list_team_members(self, team_id: str) -> dict:
        """List members of a team."""
        return self._request("GET", f"teams/{team_id}/members")

    # Webhooks
    def create_webhook(
        self,
        destination_url: str,
        triggered_for: list,
        include_transcript: bool = False,
        include_summary: bool = False,
        include_action_items: bool = False,
        include_crm_matches: bool = False,
    ) -> dict:
        """
        Create a webhook for meeting notifications.

        Args:
            destination_url: URL to receive webhook events
            triggered_for: List of recording types that trigger the webhook:
                - "my_recordings": Your private recordings
                - "shared_external_recordings": Recordings shared by others
                - "my_shared_with_team_recordings": Your recordings shared with teams
                - "shared_team_recordings": Team-accessible recordings
            include_transcript: Include transcript in webhook payload
            include_summary: Include summary in webhook payload
            include_action_items: Include action items in webhook payload
            include_crm_matches: Include CRM matches in webhook payload

        Note: At least one of include_* must be True.
        """
        data = {
            "destination_url": destination_url,
            "triggered_for": triggered_for,
            "include_transcript": include_transcript,
            "include_summary": include_summary,
            "include_action_items": include_action_items,
            "include_crm_matches": include_crm_matches,
        }
        return self._request("POST", "webhooks", json=data)

    def delete_webhook(self, webhook_id: str) -> dict:
        """Delete a webhook."""
        return self._request("DELETE", f"webhooks/{webhook_id}")

    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        webhook_id: str,
        timestamp: str,
        signature: str,
        secret: str = None,
    ) -> bool:
        """
        Verify a webhook signature.

        Args:
            payload: Raw request body bytes
            webhook_id: Value from 'webhook-id' header
            timestamp: Value from 'webhook-timestamp' header
            signature: Value from 'webhook-signature' header
            secret: Webhook secret (defaults to FATHOM_WEBHOOK_SECRET env var)

        Returns:
            True if signature is valid, False otherwise
        """
        secret = secret or os.getenv("FATHOM_WEBHOOK_SECRET")
        if not secret:
            raise ValueError("Webhook secret is required")

        # Remove 'whsec_' prefix if present
        if secret.startswith("whsec_"):
            secret = secret[6:]

        # Construct the signed payload
        signed_payload = f"{webhook_id}.{timestamp}.{payload.decode('utf-8')}"

        # Compute expected signature
        expected_sig = hmac.new(
            base64.b64decode(secret),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_sig_b64 = base64.b64encode(expected_sig).decode("utf-8")

        # The signature header contains version-prefixed signatures (e.g., "v1,base64sig")
        for sig_part in signature.split(" "):
            if "," in sig_part:
                version, sig_value = sig_part.split(",", 1)
                if version == "v1" and hmac.compare_digest(sig_value, expected_sig_b64):
                    return True

        return False


if __name__ == "__main__":
    client = FathomClient()

    # Test: List meetings
    print("=== Recent Meetings ===")
    meetings = client.list_meetings()
    for meeting in meetings.get("items", [])[:5]:
        print(f"- {meeting['title']}")
        print(f"  Recording ID: {meeting['recording_id']}")
        print(f"  Date: {meeting['created_at']}")
        print(f"  URL: {meeting['url']}")
        print()

    # Test: Get transcript for first meeting
    if meetings.get("items"):
        first_meeting = meetings["items"][0]
        recording_id = first_meeting["recording_id"]
        print(f"=== Transcript for '{first_meeting['title']}' ===")
        try:
            transcript = client.get_transcript(recording_id)
            for entry in transcript.get("transcript", [])[:5]:
                speaker = entry["speaker"]["display_name"]
                text = entry["text"][:100] + "..." if len(entry["text"]) > 100 else entry["text"]
                print(f"[{entry['timestamp']}] {speaker}: {text}")
        except Exception as e:
            print(f"Could not fetch transcript: {e}")

        print()
        print(f"=== Summary for '{first_meeting['title']}' ===")
        try:
            summary = client.get_summary(recording_id)
            if summary.get("summary"):
                print(summary["summary"].get("markdown_formatted", "No summary available"))
        except Exception as e:
            print(f"Could not fetch summary: {e}")
