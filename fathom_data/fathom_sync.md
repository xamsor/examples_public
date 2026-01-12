# Fathom Meeting Transcript RAG System

A local RAG (Retrieval-Augmented Generation) system for searching and discussing team meeting transcripts from Fathom.

## Architecture

```
Fathom API → fathom_client.py → fathom_sync.py → Local Storage
                                      ↓
                              transcript_rag.py → Qdrant Vector DB (../qdrant_data/)
                                      ↓
                              OpenAI Embeddings + GPT-4o-mini → Q&A Interface
```

## Files

| File | Purpose |
|------|---------|
| `fathom_client.py` | Fathom API wrapper - fetches meetings, transcripts, summaries |
| `fathom_sync.py` | Orchestration - syncs transcripts & manages embeddings |
| `transcript_rag.py` | RAG implementation - chunking, embeddings, search, Q&A |
| `sync_state.json` | Tracks synced recordings and embedding status |
| `team_calls_transcripts.txt` | Aggregated transcripts archive |
| `transcripts/` | Individual transcript files |

## Fathom API

- **Endpoint**: `https://api.fathom.ai/external/v1`
- **Auth**: `X-Api-Key` header (set `FATHOM_API_KEY` in `.env`)
- **Capabilities**: List meetings, get transcripts, get summaries, webhooks

## Data Storage

### Transcript File Format
```
MEETING: [Title]
DATE: [ISO timestamp]
RECORDING_ID: [ID]
URL: [Fathom URL]
INVITEES: [emails]
================================================================================
[00:00:05] Speaker Name: Transcript text...
```

### sync_state.json
Tracks which recordings have been synced and embedded:
```json
{
  "synced_recordings": ["rec_123", "rec_456"],
  "embedded_recordings": ["rec_123", "rec_456"],
  "last_sync": "2026-01-08T08:57:28"
}
```

### Vector Database
- Location: `../qdrant_data/`
- Collection: `transcripts`
- Distance metric: Cosine similarity

## CLI Commands

```bash
# Sync new transcripts from Fathom
python fathom_data/fathom_sync.py sync

# Embed unembedded transcripts into vector DB
python fathom_data/fathom_sync.py embed

# Combined sync + embed
python fathom_data/fathom_sync.py sync-embed

# Interactive Q&A mode
python fathom_data/fathom_sync.py ask

# Search transcripts
python fathom_data/fathom_sync.py search "your query"

# Show status (counts, last sync time)
python fathom_data/fathom_sync.py status

# List all transcripts
python fathom_data/fathom_sync.py list

# Force re-sync all
python fathom_data/fathom_sync.py force-sync

# Force re-embed all
python fathom_data/fathom_sync.py force-embed
```

## Python Usage

```python
from fathom_data.transcript_rag import TranscriptRAG

rag = TranscriptRAG()

# Search for relevant chunks
results = rag.search("marketing strategy", limit=5)

# Ask questions with cited answers
answer = rag.ask("What did we discuss about the product roadmap?")
print(answer)

# Get stats
stats = rag.get_stats()
```

## Technical Details

### Chunking Strategy
- Transcripts split into ~15 conversation turns per chunk
- Metadata preserved (meeting title, date)
- Empty lines buffered intelligently

### Embedding Pipeline
1. Load transcript file
2. Extract metadata (title, date)
3. Split into chunks
4. Generate embeddings via OpenAI (`text-embedding-3-small`, 1536 dimensions)
5. Upsert into Qdrant with payload

### RAG Query Pipeline
1. Convert question to embedding
2. Search Qdrant for top-k similar chunks
3. Build context from retrieved chunks
4. Send to GPT-4o-mini with system prompt
5. Return answer with citations

### Language Support
- Primary: Russian, Ukrainian
- System prompt instructs model to respond in question's language

## Current State (as of Jan 8, 2026)

- **Synced recordings**: 31
- **Date range**: Dec 2, 2025 - Jan 7, 2026
- **All embedded**: Yes
- **Last sync**: 2026-01-08T08:57:28

### Meeting Types Captured
- FatGrid Team Syncs
- Daria/Max 1-on-1s
- Daily standups
- Client demos (WSS x Fatgrid)
- External calls (Vladimir Babarykin, Kris Vlasyuk, Anna Deinego)
- Impromptu meetings (Zoom, Google Meet, MS Teams)

## Troubleshooting

### Re-index everything
```bash
python fathom_data/fathom_sync.py force-embed
```

### Clear vector database
```python
from fathom_data.transcript_rag import TranscriptRAG
rag = TranscriptRAG()
rag.clear()
```

### Check API connectivity
```python
from fathom_data.fathom_client import FathomClient
client = FathomClient()
meetings = client.list_meetings()
print(f"Found {len(meetings)} meetings")
```

## Environment Variables

Required in `.env`:
```
FATHOM_API_KEY=your_fathom_key
OPENAI_API_KEY=your_openai_key
FATHOM_WEBHOOK_SECRET=your_webhook_secret  # optional
```

## Ideas / Next Steps

- [ ] Automatic scheduled sync (cron job)
- [ ] Web UI for Q&A interface
- [ ] ClickUp integration - create tasks from action items
- [ ] Meeting summaries extraction
- [ ] Topic clustering across meetings
- [ ] Speaker-specific search filters
- [ ] Webhook for real-time new meeting ingestion
