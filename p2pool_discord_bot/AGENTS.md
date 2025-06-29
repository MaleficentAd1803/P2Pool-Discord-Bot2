## Agent Instructions for P2Pool Discord Bot

This document provides guidance for AI agents working on the P2Pool Discord Bot project.

### Project Overview

The bot monitors the P2Pool Mini sidechain (Monero) using the `mini.p2pool.observer` API. It offers slash commands for users to query miner and pool information, and it sends real-time notifications to a designated Discord channel when new blocks are found using a WebSocket connection.

### Key Technologies

*   **Python 3:** The primary programming language.
*   **discord.py:** Library for interacting with the Discord API.
*   **requests:** Library for making HTTP requests to the P2Pool Observer API.
*   **websockets:** Library for WebSocket communication for real-time events.
*   **python-dotenv:** For managing environment variables (API keys, tokens, etc.).

### File Structure

*   `bot.py`: Main application file containing the bot's logic, event handlers, command definitions, and WebSocket client.
*   `p2pool_api.py`: Module for handling interactions with the P2Pool Observer HTTP API.
*   `requirements.txt`: Lists Python package dependencies.
*   `.env`: (User-created, not in repo) Stores sensitive information like the Discord bot token and notification channel ID. The `P2POOL_API_URL` is no longer used for the observer; its base URL is hardcoded in `p2pool_api.py`.
*   `README.md`: User-facing documentation for setup and usage.
*   `AGENTS.md`: This file.

### Development Guidelines

1.  **Configuration:**
    *   Sensitive data (Discord token, notification channel ID) MUST be loaded from environment variables using `python-dotenv` and a `.env` file.
    *   The `P2POOL_API_URL` environment variable is deprecated for observer functionality. The base URL `https://mini.p2pool.observer/api` is now hardcoded in `p2pool_api.py`.
    *   The `.env` file should be listed in `.gitignore`.

2.  **API Interaction (P2Pool Observer):**
    *   HTTP API interactions are managed in `p2pool_api.py`.
        *   Pool Info: `https://mini.p2pool.observer/api/pool_info`
        *   Miner Info: `https://mini.p2pool.observer/api/miner_info/<ADDRESS>`
    *   WebSocket API for real-time events: `wss://mini.p2pool.observer/api/events`. This is handled in `bot.py`.
    *   Implement robust error handling for API requests and WebSocket connections (e.g., timeouts, connection errors, unexpected response codes, reconnection logic for WebSockets).
    *   Refer to the [P2Pool Observer API Documentation](https://mini.p2pool.observer/api-documentation) for specific endpoints and data structures.
    *   **Key information for block notifications (from WebSocket):** Event type (`side_block`, `found_block`), block height, timestamp, miner address, difficulty.

3.  **Discord Interaction (discord.py):**
    *   Use slash commands (`@tree.command`) for user interactions.
    *   Ensure necessary intents are enabled (default intents are currently used).
    *   Use embeds for rich message formatting.
    *   The primary mechanism for new block notifications is now the WebSocket listener. The polling task (`check_for_new_blocks`) is kept as a potential fallback but is disabled by default.

4.  **Error Handling & Logging:**
    *   Implement comprehensive error handling throughout the bot.
    *   Use Python's `logging` module for logging important events, errors, and debug information. Avoid using `print()` for logging in production-ready code.

5.  **Code Style & Quality:**
    *   Follow PEP 8 Python style guidelines.
    *   Write clear, concise, and well-commented code.
    *   Ensure code is modular and functions have clear responsibilities.

6.  **Dependencies:**
    *   Keep `requirements.txt` updated with all necessary packages and their versions.

7.  **Virtual Environment:**
    *   Always develop and test within a Python virtual environment (`.venv`) to manage dependencies effectively. The `.venv` directory is specified in `.gitignore`.

8.  **Testing (Future Consideration):**
    *   While not explicitly requested in the initial setup, if adding significant new features, consider writing unit tests for API interaction logic and helper functions. Mocking external APIs will be necessary for this.

### Specific Tasks & Considerations

*   **Slash Command Implementation:**
    *   `/miner_info <miner_address>`: Fetches and displays stats for the given Monero address from the P2Pool Observer API.
    *   `/latest_block`: Fetches and displays information about the most recent block from the P2Pool Observer API (`/api/pool_info`).
*   **Block Notification Service:**
    *   Primarily handled by a WebSocket client connecting to `wss://mini.p2pool.observer/api/events`.
    *   Listens for `side_block` and `found_block` events.
    *   Formats and sends notifications to the Discord channel specified by `NOTIFICATION_CHANNEL_ID`.
    *   A polling-based background task (`check_for_new_blocks`) exists as a fallback but is not started by default.

### What to Ask the User For

*   Confirmation of the Discord Bot Token.
*   Confirmation of the Discord Channel ID for notifications (`NOTIFICATION_CHANNEL_ID` in `.env`).
*   (No longer needed: P2Pool API URL, as it's now specific to `mini.p2pool.observer` and hardcoded).

Remember to update this `AGENTS.md` if new conventions or critical information emerges during development.
