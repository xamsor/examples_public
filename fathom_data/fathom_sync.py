"""
Fathom transcript sync and RAG system.

Syncs Fathom call transcripts locally and embeds them on demand.
Only fetches new calls since last sync.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from fathom_client import FathomClient
from transcript_rag import TranscriptRAG

load_dotenv()


def log(msg: str):
    """Print with flush for real-time output."""
    print(msg, flush=True)

DATA_DIR = Path(__file__).parent / "fathom_data"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
SYNC_STATE_FILE = DATA_DIR / "sync_state.json"


class FathomSync:
    def __init__(self):
        self.fathom = FathomClient()
        self.rag = TranscriptRAG()
        self._ensure_dirs()
        self.sync_state = self._load_sync_state()

    def _ensure_dirs(self):
        """Create data directories if they don't exist."""
        DATA_DIR.mkdir(exist_ok=True)
        TRANSCRIPTS_DIR.mkdir(exist_ok=True)

    def _load_sync_state(self) -> dict:
        """Load sync state from file."""
        if SYNC_STATE_FILE.exists():
            with open(SYNC_STATE_FILE) as f:
                return json.load(f)
        return {
            "last_sync": None,
            "synced_recordings": {},  # recording_id -> {"synced_at": ..., "embedded": bool}
        }

    def _save_sync_state(self):
        """Save sync state to file."""
        with open(SYNC_STATE_FILE, "w") as f:
            json.dump(self.sync_state, f, indent=2)

    def _get_transcript_path(self, recording_id: int, meeting_title: str, date: str) -> Path:
        """Get path for storing a transcript."""
        # Clean title for filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in meeting_title)
        safe_title = safe_title[:50].strip()
        date_str = date.split("T")[0]
        filename = f"{date_str}_{recording_id}_{safe_title}.txt"
        return TRANSCRIPTS_DIR / filename

    def sync(self, force: bool = False) -> dict:
        """
        Sync transcripts from Fathom.

        Args:
            force: If True, re-fetch all transcripts even if already synced

        Returns:
            Dict with sync stats
        """
        log("Fetching meetings from Fathom...")

        # Get all meetings
        meetings = self.fathom.get_all_meetings()
        total = len(meetings)
        log(f"Found {total} total meetings")

        new_count = 0
        skipped_count = 0
        error_count = 0

        for i, meeting in enumerate(meetings, 1):
            recording_id = str(meeting["recording_id"])
            title = meeting.get("meeting_title") or meeting.get("title", "Untitled")
            date = meeting["created_at"]

            # Skip if already synced (unless force)
            if not force and recording_id in self.sync_state["synced_recordings"]:
                skipped_count += 1
                log(f"[{i}/{total}] SKIP: {title[:40]} ({date[:10]})")
                continue

            log(f"[{i}/{total}] SYNC: {title[:40]} ({date[:10]})...")

            try:
                transcript_data = self.fathom.get_transcript(meeting["recording_id"])
                transcript_entries = transcript_data.get("transcript", [])

                if not transcript_entries:
                    log(f"         No transcript available")
                    continue

                # Format transcript
                lines = []
                lines.append(f"MEETING: {title}")
                lines.append(f"DATE: {date}")
                lines.append(f"RECORDING_ID: {recording_id}")
                lines.append(f"URL: {meeting.get('url', '')}")
                lines.append(f"INVITEES: {', '.join(i.get('email', '') for i in meeting.get('calendar_invitees', []))}")
                lines.append("=" * 80)
                lines.append("")

                for entry in transcript_entries:
                    speaker = entry["speaker"]["display_name"]
                    text = entry["text"]
                    timestamp = entry["timestamp"]
                    lines.append(f"[{timestamp}] {speaker}: {text}")

                # Save to file
                transcript_path = self._get_transcript_path(
                    meeting["recording_id"], title, date
                )
                with open(transcript_path, "w") as f:
                    f.write("\n".join(lines))

                # Update sync state (save after each to avoid losing progress)
                self.sync_state["synced_recordings"][recording_id] = {
                    "synced_at": datetime.now().isoformat(),
                    "embedded": False,
                    "file": str(transcript_path),
                    "title": title,
                    "date": date,
                }
                self._save_sync_state()
                new_count += 1
                log(f"         Saved ({len(transcript_entries)} entries)")

            except Exception as e:
                log(f"         ERROR: {e}")
                error_count += 1

        self.sync_state["last_sync"] = datetime.now().isoformat()
        self._save_sync_state()

        log(f"\n=== Sync complete: {new_count} new, {skipped_count} skipped, {error_count} errors ===")
        return {
            "new": new_count,
            "skipped": skipped_count,
            "errors": error_count,
            "total": len(self.sync_state["synced_recordings"]),
        }

    def embed(self, force: bool = False) -> dict:
        """
        Embed unembedded transcripts into the RAG system.

        Args:
            force: If True, re-embed all transcripts

        Returns:
            Dict with embedding stats
        """
        if force:
            log("Force re-embedding: clearing existing embeddings...")
            self.rag.clear()
            for rec_id in self.sync_state["synced_recordings"]:
                self.sync_state["synced_recordings"][rec_id]["embedded"] = False

        to_embed = [
            (rec_id, info)
            for rec_id, info in self.sync_state["synced_recordings"].items()
            if not info.get("embedded", False)
        ]

        if not to_embed:
            log("All transcripts already embedded")
            return {"embedded": 0, "total": len(self.sync_state["synced_recordings"])}

        total = len(to_embed)
        log(f"Embedding {total} transcripts...")

        embedded_count = 0
        for i, (rec_id, info) in enumerate(to_embed, 1):
            file_path = info.get("file")
            if not file_path or not Path(file_path).exists():
                log(f"[{i}/{total}] SKIP: {rec_id} - file not found")
                continue

            log(f"[{i}/{total}] EMBED: {info['title'][:40]} ({info['date'][:10]})")
            self.rag.index_transcript_file(file_path)

            self.sync_state["synced_recordings"][rec_id]["embedded"] = True
            self._save_sync_state()
            embedded_count += 1

        stats = self.rag.get_stats()
        log(f"\n=== Embedding complete: {embedded_count} embedded, {stats['total_chunks']} total chunks ===")
        return {
            "embedded": embedded_count,
            "total_chunks": stats["total_chunks"],
        }

    def sync_and_embed(self, force: bool = False) -> dict:
        """Sync from Fathom and embed new transcripts."""
        sync_stats = self.sync(force=force)
        embed_stats = self.embed(force=force)
        return {"sync": sync_stats, "embed": embed_stats}

    def status(self) -> dict:
        """Get sync and embedding status."""
        synced = self.sync_state["synced_recordings"]
        embedded_count = sum(1 for info in synced.values() if info.get("embedded"))
        rag_stats = self.rag.get_stats()

        return {
            "last_sync": self.sync_state["last_sync"],
            "total_synced": len(synced),
            "total_embedded": embedded_count,
            "pending_embed": len(synced) - embedded_count,
            "rag_chunks": rag_stats["total_chunks"],
        }

    def list_transcripts(self) -> list[dict]:
        """List all synced transcripts."""
        return [
            {
                "recording_id": rec_id,
                "title": info["title"],
                "date": info["date"],
                "embedded": info.get("embedded", False),
            }
            for rec_id, info in self.sync_state["synced_recordings"].items()
        ]

    def ask(self, question: str, limit: int = 5) -> str:
        """Ask a question about the transcripts."""
        return self.rag.ask(question, limit=limit)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search transcripts."""
        return self.rag.search(query, limit=limit)


if __name__ == "__main__":
    import sys

    sync = FathomSync()

    if len(sys.argv) < 2:
        print("Usage: python fathom_sync.py <command>")
        print("\nCommands:")
        print("  sync        - Fetch new transcripts from Fathom")
        print("  embed       - Embed unembedded transcripts")
        print("  sync-embed  - Sync and embed in one step")
        print("  status      - Show sync/embed status")
        print("  list        - List all synced transcripts")
        print("  ask         - Interactive Q&A mode")
        print("  force-sync  - Re-fetch all transcripts")
        print("  force-embed - Re-embed all transcripts")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "sync":
        sync.sync()
    elif cmd == "embed":
        sync.embed()
    elif cmd == "sync-embed":
        sync.sync_and_embed()
    elif cmd == "status":
        status = sync.status()
        print(f"Last sync: {status['last_sync'] or 'Never'}")
        print(f"Synced transcripts: {status['total_synced']}")
        print(f"Embedded: {status['total_embedded']}")
        print(f"Pending embed: {status['pending_embed']}")
        print(f"RAG chunks: {status['rag_chunks']}")
    elif cmd == "list":
        transcripts = sync.list_transcripts()
        for t in transcripts:
            status = "✓" if t["embedded"] else "○"
            print(f"{status} [{t['date'][:10]}] {t['title']}")
    elif cmd == "ask":
        print("\nFathom Transcript Q&A")
        print("Type 'quit' to exit\n")
        while True:
            try:
                q = input("You: ").strip()
                if q.lower() in ["quit", "exit", "q"]:
                    break
                if not q:
                    continue
                print("\nThinking...\n")
                answer = sync.ask(q)
                print(f"Assistant: {answer}\n")
            except KeyboardInterrupt:
                break
    elif cmd == "force-sync":
        sync.sync(force=True)
    elif cmd == "force-embed":
        sync.embed(force=True)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
