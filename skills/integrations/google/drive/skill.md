# Google Drive Skill

## Capability
Lists and searches files in the user's Google Drive.

## Usage
- `search_files(query, limit)`: Returns a list of files matching the query.
- query examples: "name contains 'budget'", "mimeType = 'application/vnd.google-apps.folder'"

## Setup
Requires `token_default.json` in `06_Operations/integrations/google` with `params: ['https://www.googleapis.com/auth/drive.readonly']`.
