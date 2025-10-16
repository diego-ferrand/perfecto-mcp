# Perfecto MCP

A Model Context Protocol (MCP) server for Perfecto Mobile Cloud Platform integration.

## Setup

1. Create a token file:
```json
{"token": "YOUR_TOKEN", "cloud_environment": "YOUR_CLOUD"}
```

2. Configure your MCP client:
```json
{
  "mcpServers": {
    "perfecto MCP": {
      "command": "/path/to/perfecto-mcp-macos-amd64",
      "args": ["--token-file", "/path/to/token.json"]
    }
  }
}
```

## Available Tools

## Development

### Running locally
```bash
uv run python main.py --token-file /path/to/token.json
```

### Building binary
```bash
uv run python build.py
```

## Requirements

- Python 3.11+
- Perfecto API token and cloud environment