# CAAL n8n Workflows

Example workflows for CAAL voice assistant. These integrate with n8n's MCP server to give CAAL tool-calling capabilities.

## Quick Start

```bash
# 1. Copy and edit config
cp config.env.example config.env
nano config.env  # Fill in your IPs and API key

# 2. Run setup (creates all workflows in n8n)
python setup.py
```

That's it! The setup script connects to n8n, replaces placeholders with your config values, and creates all workflows.

## Workflows Included

| Workflow | Description |
|----------|-------------|
| `espn_get_nfl_scores.json` | Get live NFL scores from ESPN API |
| `calendar_get_events.json` | Query Google Calendar events |
| `hass_control.json` | Control Home Assistant devices |
| `radarr_search_movies.json` | Search Radarr movie library |
| `n8n_create_caal_tool.json` | Self-modifying: create new workflows via voice (advanced) |

## Configuration

### config.env

Copy `config.env.example` to `config.env` and fill in:

```
N8N_HOST=192.168.1.100:5678      # Your n8n server
N8N_API_KEY=your_api_key_here    # n8n API key (Settings > API)
CAAL_HOST=192.168.1.100:8889     # CAAL webhook server
RADARR_HOST=192.168.1.100:7878   # Radarr (if using radarr workflow)
```

### CREDENTIALS.md

Update this file with your n8n credential names. The workflow builder uses this to know what services are available.

### Placeholders

Workflows use `{{PLACEHOLDER}}` syntax for IPs. Run `setup.py` to replace them with your `config.env` values, or manually find/replace after importing to n8n.

## Scripts

| Script | Usage |
|--------|-------|
| `setup.py` | **Main script** - creates all workflows in n8n |
| `create_workflow.py` | Create a single workflow (used by setup.py) |
| `update_workflow.py` | Update an existing workflow |

## Workflow Builder

`caal-workflow-builder-seed.md` is a prompt for AI assistants (Claude, Gemini) to create new CAAL-compatible workflows. Used by `n8n_create_caal_tool.json` for voice-driven workflow creation. Must update placeholders in here as well.

## Adding to n8n

### Option 1: Use the script
```bash
python create_workflow.py calendar_get_events.json
```

### Option 2: Manual import
1. Open n8n web UI
2. Workflows > Import from File
3. Select the JSON file
4. Update any remaining placeholders
5. Activate the workflow

## Workflow Naming Convention

Follow this pattern: `service_action_object`

- `calendar_get_events` - Get calendar events
- `hass_control` - Control Home Assistant
- `radarr_search_movies` - Search Radarr

This helps CAAL understand what each tool does.

## Creating New Workflows

1. Create workflow in n8n with webhook trigger
2. Set webhook to POST method
3. Add `webhookId` field matching the path (required for API creation)
4. Return `{message: "...", data: [...]}` format
5. Enable "Available in MCP" in workflow settings
6. Export JSON and add to this folder

See `caal-workflow-builder-seed.md` for detailed guidelines.

## Advanced: Self-Modifying Workflow

`n8n_create_caal_tool.json` allows CAAL to create new n8n workflows via voice commands. This is an advanced feature that requires additional setup.

### Requirements

1. **Claude Code** installed on the n8n host with SSH access
2. **n8n credentials** configured:
   - SSH credential for accessing Claude Code
   - HTTP Header Auth credential for n8n API

### Setup

1. Import `n8n_create_caal_tool.json` into n8n
2. Replace placeholders in the workflow:
   - `{{WORKFLOWS_DIR}}` - Path to your n8n-workflows directory
   - `{{SSH_CREDENTIAL_ID}}` / `{{SSH_CREDENTIAL_NAME}}` - Your SSH credential
   - `{{N8N_API_CREDENTIAL_ID}}` - Your n8n API credential
   - `{{CAAL_HOST}}` - CAAL webhook server (e.g., `192.168.1.100:8889`)
3. Update credential references to match your n8n setup
4. Activate the workflow

### Usage

Once configured, you can say things like:
- "Create a tool that gets the current weather from OpenWeatherMap"
- "Build a workflow that checks my email for unread messages"

CAAL will use Claude Code to generate the workflow JSON, create it in n8n, test it, and announce when ready.
