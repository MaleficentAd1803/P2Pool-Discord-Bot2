# P2Pool Mini Discord Bot

This bot monitors a P2Pool mini sidechain using its API and provides information via Discord slash commands. It also sends notifications for new blocks found on the sidechain.

## Setup

1.  **Clone the repository (or download the files).**
2.  **Create a Discord Bot Application:**
    *   Go to the [Discord Developer Portal](https://discord.com/developers/applications).
    *   Click "New Application".
    *   Give your application a name and click "Create".
    *   Go to the "Bot" tab on the left.
    *   Click "Add Bot" and confirm.
    *   Under "Token", click "Copy" to get your bot token. **Keep this token secret!**
    *   Enable "Message Content Intent" under "Privileged Gateway Intents" if you plan to add commands that read message content (not strictly necessary for slash commands initially).
3.  **Install Dependencies:**
    *   It's highly recommended to use a virtual environment.
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
        ```
    *   Install the required Python libraries:
        ```bash
        pip install -r requirements.txt
        ```
4.  **Configure the Bot:**
    *   Create a file named `.env` in the `p2pool_discord_bot` directory.
    *   Add the following lines to the `.env` file, replacing the placeholder values with your actual data:
        ```env
        DISCORD_TOKEN="YOUR_BOT_TOKEN_HERE"
        P2POOL_API_URL="YOUR_P2POOL_MINI_API_ENDPOINT_HERE" # e.g., "http://127.0.0.1:9327"
        NOTIFICATION_CHANNEL_ID="YOUR_DISCORD_CHANNEL_ID_FOR_NOTIFICATIONS"
        ```
        *   `DISCORD_TOKEN`: The token you copied from the Discord Developer Portal.
        *   `P2POOL_API_URL`: The HTTP API endpoint for your P2Pool mini node (e.g., `http://<your_node_ip>:9327`).
        *   `NOTIFICATION_CHANNEL_ID`: The ID of the Discord channel where new block notifications should be sent. To get a channel ID, enable Developer Mode in Discord (User Settings > Advanced > Developer Mode), then right-click the channel and select "Copy ID".
5.  **Invite the Bot to Your Server:**
    *   In the Discord Developer Portal, go to your application, then "OAuth2" -> "URL Generator".
    *   Select the `bot` and `application.commands` scopes.
    *   Under "Bot Permissions", select necessary permissions. At a minimum, you'll likely need:
        *   `Send Messages`
        *   `Embed Links` (if you plan to use embeds for cleaner messages)
        *   `Read Message History` (for the bot to see commands, though slash commands work differently)
    *   Copy the generated URL and paste it into your browser. Select the server you want to add the bot to and authorize it.

6.  **Run the Bot:**
    ```bash
    cd p2pool_discord_bot
    python bot.py
    ```

## Slash Commands

*   `/miner_info <miner_address>`: Displays information about the specified Monero miner address from the P2Pool.
*   `/latest_block`: Shows details about the latest block found on the P2Pool mini sidechain.

## Block Notifications

The bot will automatically monitor the P2Pool mini sidechain for new blocks. When a new block is detected, a notification will be sent to the channel specified by `NOTIFICATION_CHANNEL_ID` in your `.env` file.

## Troubleshooting

*   **Bot doesn't come online:**
    *   Check that your `DISCORD_TOKEN` is correct in the `.env` file.
    *   Ensure `bot.py` is running and there are no error messages in the console.
    *   Verify your internet connection.
*   **Slash commands don't appear:**
    *   It can sometimes take Discord up to an hour to register new slash commands globally. Try inviting the bot to a test server first, as guild (server-specific) commands often update faster.
    *   Ensure the bot was invited with the `application.commands` scope.
    *   Check the bot's console output for any errors related to command syncing.
*   **API errors / No data from P2Pool:**
    *   Verify that your `P2POOL_API_URL` is correct and accessible from where the bot is running.
    *   Check if the P2Pool node is running and its API is enabled.

## Contributing

Feel free to fork the project, create a feature branch, and submit a pull request.
For major changes, please open an issue first to discuss what you would like to change.
Ensure any new code is linted and tested.
