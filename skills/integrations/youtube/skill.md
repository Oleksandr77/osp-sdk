# YouTube Analysis Skill

## Capability
This skill can retrieve the transcript of a YouTube video and summarize its content.

## Usage
Provide a YouTube video URL or ID. The skill will:
1. Fetch the transcript using the `youtube_transcript_api`.
2. Return the transcript text (and optionally a summary if implemented).

## Tools
- `get_transcript(video_id)`: Fetches transcript.
- `execute(params)`: Main entry point receiving arguments.
