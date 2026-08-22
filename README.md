# WhatsApp MCP Server

This is a Model Context Protocol (MCP) server for WhatsApp.

With this you can search and read your personal Whatsapp messages (including images, videos, documents, and audio messages), search your contacts and send messages to either individuals or groups. You can also send media files including images, videos, documents, and audio messages.

It connects to your **personal WhatsApp account** directly via the Whatsapp web multidevice API (using the [whatsmeow](https://github.com/tulir/whatsmeow) library). All your messages are stored locally in a SQLite database and only sent to an LLM (such as Claude) when the agent accesses them through tools (which you control).

Here's an example of what you can do when it's connected to Claude.

![WhatsApp MCP](./example-use.png)

> To get updates on this and other projects I work on [enter your email here](https://docs.google.com/forms/d/1rTF9wMBTN0vPfzWuQa2BjfGKdKIpTbyeKxhPMcEzgyI/preview)

> *Caution:* as with many MCP servers, the WhatsApp MCP is subject to [the lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/). This means that project injection could lead to private data exfiltration.

## Changes in this fork

This fork moves the whole project into Docker, following [the Twelve-Factor App](https://12factor.net/) methodology:

- **No host dependencies**: Go, Python, uv and FFmpeg are no longer required on the machine running this — both services build and run entirely inside containers (`whatsapp-bridge/Dockerfile`, `whatsapp-mcp-server/Dockerfile`, `docker-compose.yml`).
- **Config via environment**: the MCP server's bridge URL and database path (`WHATSAPP_API_BASE_URL`, `MESSAGES_DB_PATH`) are now read from the environment instead of being hardcoded, matching how the Go bridge already worked. See `.env.example`.
- **Portable data storage**: the WhatsApp session, message database and downloaded media live in a single bind-mounted directory (`WHATSAPP_DATA_DIR`, default `./data/whatsapp-store`) shared by both containers, so moving the deployment to another machine is just a matter of copying that directory over.
- **CI**: `scripts/ci.sh` builds both images and runs the Go and Python test suites, all through Docker — mirrored in `.github/workflows/ci.yml`. A new `whatsapp-mcp-server/test_whatsapp.py` covers the env-var config behavior.

See the [Installation](#installation) section below for the updated Docker-based setup.

## Installation

The project runs entirely in Docker — no Go, Python, uv or FFmpeg needs to be installed on the host.

### Prerequisites

- Docker and Docker Compose
- Anthropic Claude Desktop app (or Cursor)

### Steps

1. **Clone this repository**

   ```bash
   git clone https://github.com/lharries/whatsapp-mcp.git
   cd whatsapp-mcp
   ```

2. **Configure**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` if you want the WhatsApp session/database/media stored somewhere other than `./data/whatsapp-store`, or if your host UID/GID (`id -u` / `id -g`) differ from the defaults.

3. **Build and start the WhatsApp bridge**

   ```bash
   docker compose --profile mcp build
   docker compose up -d whatsapp-bridge
   docker compose logs -f whatsapp-bridge
   ```

   The first time you run it, a QR code will be printed to the logs — scan it with your WhatsApp mobile app to authenticate. Once connected, `Ctrl+C` out of the logs (the container keeps running in the background). The session persists in `WHATSAPP_DATA_DIR`, so you won't need to scan again on restart.

   After approximately 20 days, you might need to re-authenticate.

4. **Connect to the MCP server**

   Copy the below json with the appropriate {{PATH}} value:

   ```json
   {
     "mcpServers": {
       "whatsapp": {
         "command": "docker",
         "args": [
           "compose",
           "-f",
           "{{PATH_TO_SRC}}/whatsapp-mcp/docker-compose.yml", // cd into the repo, run `pwd` and enter the output here + "/docker-compose.yml"
           "run",
           "--rm",
           "-T",
           "whatsapp-mcp-server"
         ]
       }
     }
   }
   ```

   For **Claude**, save this as `claude_desktop_config.json` in your Claude Desktop configuration directory at:

   ```
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

   For **Cursor**, save this as `mcp.json` in your Cursor configuration directory at:

   ```
   ~/.cursor/mcp.json
   ```

5. **Restart Claude Desktop / Cursor**

   Open Claude Desktop and you should now see WhatsApp as an available integration.

   Or restart Cursor.

## Architecture Overview

This application consists of two main components:

1. **Go WhatsApp Bridge** (`whatsapp-bridge/`): A Go application that connects to WhatsApp's web API, handles authentication via QR code, and stores message history in SQLite. It serves as the bridge between WhatsApp and the MCP server.

2. **Python MCP Server** (`whatsapp-mcp-server/`): A Python server implementing the Model Context Protocol (MCP), which provides standardized tools for Claude to interact with WhatsApp data and send/receive messages.

### Data Storage

- All message history is stored in a SQLite database within `$WHATSAPP_DATA_DIR` (`./data/whatsapp-store` by default), bind-mounted into both containers at `/app/store`
- The database maintains tables for chats and messages
- Messages are indexed for efficient searching and retrieval
- Downloaded media also lands in `$WHATSAPP_DATA_DIR`, so it stays accessible from the host after `download_media` runs

## Usage

Once connected, you can interact with your WhatsApp contacts through Claude, leveraging Claude's AI capabilities in your WhatsApp conversations.

### MCP Tools

Claude can access the following tools to interact with WhatsApp:

- **search_contacts**: Search for contacts by name or phone number
- **list_messages**: Retrieve messages with optional filters and context
- **list_chats**: List available chats with metadata
- **get_chat**: Get information about a specific chat
- **get_direct_chat_by_contact**: Find a direct chat with a specific contact
- **get_contact_chats**: List all chats involving a specific contact
- **get_last_interaction**: Get the most recent message with a contact
- **get_message_context**: Retrieve context around a specific message
- **send_message**: Send a WhatsApp message to a specified phone number or group JID
- **send_file**: Send a file (image, video, raw audio, document) to a specified recipient
- **send_audio_message**: Send an audio file as a WhatsApp voice message (requires the file to be an .ogg opus file or ffmpeg must be installed)
- **download_media**: Download media from a WhatsApp message and get the local file path

### Media Handling Features

The MCP server supports both sending and receiving various media types:

#### Media Sending

You can send various media types to your WhatsApp contacts:

- **Images, Videos, Documents**: Use the `send_file` tool to share any supported media type.
- **Voice Messages**: Use the `send_audio_message` tool to send audio files as playable WhatsApp voice messages.
  - For optimal compatibility, audio files should be in `.ogg` Opus format.
  - With FFmpeg installed, the system will automatically convert other audio formats (MP3, WAV, etc.) to the required format.
  - Without FFmpeg, you can still send raw audio files using the `send_file` tool, but they won't appear as playable voice messages.

#### Media Downloading

By default, just the metadata of the media is stored in the local database. The message will indicate that media was sent. To access this media you need to use the download_media tool which takes the `message_id` and `chat_jid` (which are shown when printing messages containing the meda), this downloads the media and then returns the file path which can be then opened or passed to another tool.

## Technical Details

1. Claude sends requests to the Python MCP server
2. The MCP server queries the Go bridge for WhatsApp data or directly to the SQLite database
3. The Go accesses the WhatsApp API and keeps the SQLite database up to date
4. Data flows back through the chain to Claude
5. When sending messages, the request flows from Claude through the MCP server to the Go bridge and to WhatsApp

## Troubleshooting

- Make sure the `whatsapp-bridge` container is running (`docker compose ps`) — the MCP server container is started on demand by Claude Desktop/Cursor and depends on the bridge being reachable at `WHATSAPP_API_BASE_URL`.

### Authentication Issues

- **QR Code Not Displaying**: If the QR code doesn't appear, try restarting the authentication script. If issues persist, check if your terminal supports displaying QR codes.
- **WhatsApp Already Logged In**: If your session is already active, the Go bridge will automatically reconnect without showing a QR code.
- **Device Limit Reached**: WhatsApp limits the number of linked devices. If you reach this limit, you'll need to remove an existing device from WhatsApp on your phone (Settings > Linked Devices).
- **No Messages Loading**: After initial authentication, it can take several minutes for your message history to load, especially if you have many chats.
- **WhatsApp Out of Sync**: If your WhatsApp messages get out of sync with the bridge, delete both database files (`messages.db` and `whatsapp.db` inside `$WHATSAPP_DATA_DIR`) and restart the bridge (`docker compose restart whatsapp-bridge`) to re-authenticate.

For additional Claude Desktop integration troubleshooting, see the [MCP documentation](https://modelcontextprotocol.io/quickstart/server#claude-for-desktop-integration-issues). The documentation includes helpful tips for checking logs and resolving common issues.
