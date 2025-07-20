# Discord Weather Bot

A Discord bot that provides weather information using Japan Meteorological Agency (JMA) API with AI-generated positive messages.

## Features

- Current weather information for Japanese locations
- 7-day weather forecasts
- Weather alerts and warnings
- Scheduled weather notifications via DM
- AI-generated positive messages using Google Gemini
- User location preferences storage
- Japanese language support

## Setup

### Prerequisites

- Python 3.9 or higher
- Discord Bot Token
- Google Gemini API Key (optional, for AI messages)

### Installation

1. Clone the repository
2. Install uv (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Install dependencies:
   ```bash
   uv sync
   ```

4. Copy the environment file and configure:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` file with your configuration:
   - `DISCORD_TOKEN`: Your Discord bot token
   - `GEMINI_API_KEY`: Your Google Gemini API key (optional)
   - Other configuration options as needed

### Running the Bot

```bash
uv run python run.py
```

## Project Structure

```
src/
├── __init__.py
├── bot.py              # Main bot entry point
├── config.py           # Configuration management
├── commands/           # Discord command handlers
├── models/             # Database models
├── services/           # Business logic services
└── utils/              # Utility functions
    └── logging.py      # Logging configuration
```

## Configuration

The bot uses environment variables for configuration. See `.env.example` for all available options.

### Required Environment Variables

- `DISCORD_TOKEN`: Discord bot token

### Optional Environment Variables

- `GEMINI_API_KEY`: Google Gemini API key for AI messages
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `LOG_LEVEL`: Logging level (defaults to INFO)

## License

This project is licensed under the MIT License.