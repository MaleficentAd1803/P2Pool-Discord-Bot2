## Agent Instructions for P2Pool Discord Bot

This document provides guidance for AI agents working on the P2Pool Discord Bot project.

### Project Overview

The bot monitors a P2Pool mini sidechain (Monero) via its HTTP API. It offers slash commands for users to query miner and block information, and it sends notifications to a designated Discord channel when new blocks are found.

### Key Technologies

*   **Python 3:** The primary programming language.
*   **discord.py:** Library for interacting with the Discord API.
*   **requests:** Library for making HTTP requests to the P2Pool API.
*   **python-dotenv:** For managing environment variables (API keys, tokens, etc.).

### File Structure

*   `bot.py`: Main application file containing the bot's logic, event handlers, and command definitions.
*   `config.py`: Placeholder, but configuration is primarily managed via a `.env` file.
*   `requirements.txt`: Lists Python package dependencies.
*   `.env`: (User-created, not in repo) Stores sensitive information like the Discord bot token, P2Pool API URL, and notification channel ID.
*   `README.md`: User-facing documentation for setup and usage.
*   `AGENTS.md`: This file.

### Development Guidelines

1.  **Configuration:**
    *   All sensitive data (Discord token, P2Pool API URL, specific channel IDs) MUST be loaded from environment variables using `python-dotenv` and a `.env` file. Do not hardcode these values.
    *   The `.env` file should be listed in `.gitignore`.
    *   The `config.py` file is largely vestigial; prefer `.env`.

2.  **API Interaction (P2Pool):**
    *   The P2Pool API endpoint is configurable via the `P2POOL_API_URL` environment variable.
    *   Implement robust error handling for API requests (e.g., timeouts, connection errors, unexpected response codes).
    *   Refer to P2Pool API documentation for specific endpoints and data structures. A common base URL might be `http://127.0.0.1:9327/`.
        *   Miner info: `/miners/<MINER_ADDRESS>` (check if this specific path is correct for the mini pool variant) or often part of a general stats endpoint.
        *   Sidechain blocks/stats: `/stats` or `/chain` or similar. The exact endpoint for "latest block" needs to be identified. The mini pool might have different endpoints than the main pool.
    *   **Key information for block notifications:** Block height, timestamp, effort, miner who found it (if available).

3.  **Discord Interaction (discord.py):**
    *   Use slash commands (`@tree.command`) for user interactions rather than traditional prefix-based commands.
    *   Ensure necessary intents are enabled when initializing the bot client. For slash commands and basic functionality, default intents are often sufficient, but if message content is ever needed, the `message_content` intent must be explicitly enabled.
    *   Use embeds for rich message formatting where appropriate (e.g., for displaying miner info or block details).
    *   Background tasks (`@tasks.loop`) should be used for periodic checks (like new block polling). Ensure these tasks handle exceptions gracefully and don't crash the bot.

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
    *   `/miner_info [address]`: Fetch and display stats for the given Monero address from the pool.
    *   `/latest_block`: Fetch and display information about the most recent block found by the pool.
*   **Block Notification Service:**
    *   This will be a background task (`tasks.loop`).
    *   It needs to store the ID/hash of the last known block to detect new ones.
    *   When a new block is found, format a message and send it to the channel specified by `NOTIFICATION_CHANNEL_ID`.

### What to Ask the User For

*   The exact HTTP API endpoint for their P2Pool **mini** sidechain. (e.g., `http://host:port`)
*   Specific API paths for:
    *   Fetching miner statistics (given a miner's address).
    *   Fetching the latest sidechain block information.
*   Confirmation of the Discord Channel ID for notifications.

Remember to update this `AGENTS.md` if new conventions or critical information emerges during development.
