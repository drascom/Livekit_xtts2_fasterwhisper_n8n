# n8n Credentials Reference

This file tells the workflow builder (Claude/Gemini) what credentials are available in your n8n instance. Update this list to match your setup.

## How to Use

1. Set up credentials in n8n (Settings > Credentials)
2. Update this file with your credential names
3. The AI workflow builder will reference these when creating workflows

## Template

```
## API Services
- **google_calendar** - Google Calendar OAuth2
- **gmail** - Gmail OAuth2

## Home Services
- **home_assistant** - Home Assistant API (long-lived access token)
- **radarr** - Header Auth (API key)
- **sonarr** - Header Auth (API key)

## Infrastructure
- **n8n** - Header Auth (n8n API key for self-management)
- **ssh_server** - SSH credentials for CLI tools (optional, for Gemini CLI integration)

## Notes
- Use credential names exactly as shown when creating workflows
- If a service needs credentials not listed here, set them up in n8n first
- Credentials with "Header Auth" typically use X-Api-Key header
```

## Your Credentials

<!-- Update the list below with your actual n8n credential names -->

- **home_assistant** - Home Assistant API
- **n8n** - n8n API key
