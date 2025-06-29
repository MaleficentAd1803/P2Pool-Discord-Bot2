# Main bot code will go here
import discord
import os
from dotenv import load_dotenv
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Load Environment Variables ---
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
# P2POOL_API_URL = os.getenv("P2POOL_API_URL") # Deprecated, API base URL is now hardcoded in p2pool_api.py
NOTIFICATION_CHANNEL_ID_STR = os.getenv("NOTIFICATION_CHANNEL_ID")
GUILD_ID_STR = os.getenv("GUILD_ID")

# --- Validate Environment Variables ---
if not DISCORD_TOKEN:
    logger.error("CRITICAL: DISCORD_TOKEN not found in .env file or environment variables. Bot cannot start.")
    exit()

# P2POOL_API_URL is no longer directly used by bot.py for validation here,
# as p2pool_api.py now hardcodes the base URL.
# If P2POOL_API_URL was intended for other purposes, that logic would need review.
# For now, removing the check here.
# if not P2POOL_API_URL:
#     logger.error("CRITICAL: P2POOL_API_URL not found in .env file or environment variables. Bot cannot start.")
#     exit()

NOTIFICATION_CHANNEL_ID = 0
if NOTIFICATION_CHANNEL_ID_STR:
    try:
        NOTIFICATION_CHANNEL_ID = int(NOTIFICATION_CHANNEL_ID_STR)
    except ValueError:
        logger.error(f"Invalid NOTIFICATION_CHANNEL_ID: {NOTIFICATION_CHANNEL_ID_STR}. Must be an integer.")
        # Decide if this is critical enough to exit, or if the bot can run without notifications.
        # For now, we'll let it run but notifications will likely fail or go nowhere.
else:
    logger.warning("NOTIFICATION_CHANNEL_ID not set. New block notifications will not be sent.")

GUILD_ID = None
if GUILD_ID_STR:
    try:
        GUILD_ID = discord.Object(id=int(GUILD_ID_STR))
        logger.info(f"GUILD_ID set to {GUILD_ID_STR} for slash command syncing.")
    except ValueError:
        logger.error(f"Invalid GUILD_ID: {GUILD_ID_STR}. Must be an integer. Will attempt global sync.")


# --- Bot Setup ---
intents = discord.Intents.default()
# If you ever need to read message content (e.g., for non-slash commands or specific message events):
# intents.message_content = True
# client = discord.Client(intents=intents)
# For a bot primarily focused on slash commands, discord.Bot can be more straightforward.
# However, using discord.Client and CommandTree is perfectly fine and offers flexibility.
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

# --- Event: Bot Ready ---
@client.event
async def on_ready():
    logger.info(f'Logged in as {client.user.name} (ID: {client.user.id})')

    # Start the background task if it's not already running
    if not check_for_new_blocks.is_running():
        # Injecting helper methods for one-time logging into the task object.
        # This is a bit unconventional but keeps them tied to the task instance.
        # A cleaner way might involve a class for the task with these as methods.
        setattr(check_for_new_blocks, 'set_logged_once', lambda key: set_task_logged_once(check_for_new_blocks.get_task_name(), key))
        setattr(check_for_new_blocks, 'has_been_logged', lambda key: has_task_logged_once(check_for_new_blocks.get_task_name(), key))

        # check_for_new_blocks.start() # Polling task can be disabled if WebSocket is preferred
        # logger.info("Started 'check_for_new_blocks' background task (polling).")
        logger.info("'check_for_new_blocks' (polling) task is available but not started by default. WebSocket is preferred.")


    # Start WebSocket client
    if not hasattr(client, 'websocket_task') or client.websocket_task.done():
        client.websocket_task = asyncio.create_task(start_websocket_listener())
        logger.info("Attempting to start WebSocket listener task.")


    logger.info('------')
    try:
        if GUILD_ID:
            await tree.sync(guild=GUILD_ID)
            logger.info(f"Slash commands synced to guild {GUILD_ID.id}.")
        else:
            await tree.sync()
            logger.info("Slash commands synced globally. This might take up to an hour to reflect everywhere.")
        logger.info("Bot is ready and commands are synced.")
    except Exception as e:
        logger.error(f"Error syncing slash commands: {e}", exc_info=True)

# --- API Interaction (using asyncio.to_thread for synchronous requests library) ---
import asyncio
from p2pool_api import get_miner_info as api_get_miner_info
from p2pool_api import get_p2pool_sidechain_stats as api_get_sidechain_stats

# --- Helper function to format API data into embeds ---
def format_miner_info_embed(miner_address: str, data: dict) -> discord.Embed:
    """Formats miner data into a Discord embed."""
    if not data:
        embed = discord.Embed(
            title="Miner Not Found",
            description=f"Could not retrieve information for miner: `{miner_address}`\nThe address might be invalid or not found on the pool.",
            color=discord.Color.red()
        )
        return embed

    embed = discord.Embed(
        title=f"Miner Information: {miner_address[:12]}...{miner_address[-6:]}",
        color=discord.Color.blue()
    )
    # API fields: id, address, shares (list of dicts), last_share_height, last_share_timestamp
    embed.add_field(name="Miner ID", value=data.get('id', 'N/A'), inline=True)
    embed.add_field(name="Address", value=f"`{data.get('address', 'N/A')}`", inline=False)

    shares_info = data.get('shares', [])
    if shares_info:
        # Displaying sum of shares and uncles as an example. Could be more detailed.
        total_shares = sum(s.get('shares', 0) for s in shares_info)
        total_uncles = sum(s.get('uncles', 0) for s in shares_info)
        embed.add_field(name="Total Shares", value=total_shares, inline=True)
        embed.add_field(name="Total Uncles", value=total_uncles, inline=True)
    else:
        embed.add_field(name="Shares", value="No share data found", inline=True)

    last_share_ts = data.get('last_share_timestamp')
    if last_share_ts:
        embed.add_field(name="Last Share Submitted", value=f"<t:{last_share_ts}:R>", inline=True)
    else:
        embed.add_field(name="Last Share Submitted", value='N/A', inline=True)

    embed.add_field(name="Last Share Height", value=data.get('last_share_height', 'N/A'), inline=True)

    embed.set_footer(text="Data from mini.p2pool.observer")
    return embed

def format_latest_block_embed(data: dict, context: str = "latest_block") -> discord.Embed:
    """
    Formats latest block data from /api/pool_info into a Discord embed.
    Can be used for general latest block info or for new block notifications.
    """
    if not data or 'sidechain' not in data:
        return discord.Embed(title="Error", description="Invalid or empty sidechain data received.", color=discord.Color.red())

    sidechain_info = data.get('sidechain', {})
    last_block = sidechain_info.get('last_block') # This is the current tip
    last_found_block_info = sidechain_info.get('last_found', {}).get('main_block') # This is the last block that P2Pool found on Monero mainnet

    if not last_block:
        embed = discord.Embed(
            title="Latest Block Information",
            description="Could not retrieve latest block information from the sidechain.",
            color=discord.Color.orange()
        )
        return embed

    # Fields from sidechain.last_block
    height = last_block.get('side_height', 'N/A')
    block_hash = last_block.get('main_id', 'N/A') # API uses 'main_id' for the block hash
    template_id = last_block.get('template_id', 'N/A')
    timestamp_unix = last_block.get('timestamp', 0)
    difficulty = last_block.get('difficulty', 'N/A')
    miner_address_found = last_block.get('miner_address', 'N/A') # Address of the miner of this sidechain block

    title = "Latest P2Pool Mini Sidechain Block"
    if context == "new_block_notification":
        title = "🎉 New Block Found on P2Pool Mini!"

    embed = discord.Embed(title=title, color=discord.Color.green())
    embed.add_field(name="Sidechain Height", value=height, inline=True)
    embed.add_field(name="Block Hash (Main ID)", value=f"`{block_hash[:16]}...`" if block_hash != 'N/A' else 'N/A', inline=True)
    embed.add_field(name="Template ID", value=f"`{template_id[:16]}...`" if template_id != 'N/A' else 'N/A', inline=True)
    embed.add_field(name="Timestamp", value=f"<t:{timestamp_unix}:R>" if timestamp_unix else "N/A", inline=True)
    embed.add_field(name="Difficulty", value=f"{difficulty:,}" if isinstance(difficulty, int) else difficulty, inline=True)
    embed.add_field(name="Found By (Sidechain)", value=f"`{miner_address_found[:8]}...{miner_address_found[-4:]}`" if miner_address_found != 'N/A' else 'N/A', inline=True)

    if last_found_block_info: # Info about the last Monero block found by P2Pool
        embed.add_field(name="--- Last Monero Block Found by Pool ---", value="\u200b", inline=False) # Separator
        embed.add_field(name="Mainnet Height", value=last_found_block_info.get('height','N/A'), inline=True)
        main_block_id = last_found_block_info.get('id','N/A')
        embed.add_field(name="Mainnet Block ID", value=f"`{main_block_id[:16]}...`" if main_block_id != 'N/A' else 'N/A', inline=True)
        reward_atomic = last_found_block_info.get('reward', 0)
        reward_xmr = reward_atomic / 10**12
        embed.add_field(name="Mainnet Reward", value=f"{reward_xmr:.6f} XMR" if reward_atomic else "N/A", inline=True)

    embed.set_footer(text="Data from mini.p2pool.observer")
    return embed

# --- Background Task for Block Notification ---
from discord.ext import tasks

# Store the last known block height/hash to detect new blocks.
# For simplicity, using block height. A hash would be more robust against reorgs if the API provides it easily.
last_known_block_height = None
# How often to check for new blocks (in seconds)
BLOCK_CHECK_INTERVAL_SECONDS = 60

# One-time logging helper for the task loop
task_logged_states = {}
def set_task_logged_once(task_name: str, key: str):
    task_logged_states[f"{task_name}_{key}"] = True
def has_task_logged_once(task_name: str, key: str):
    return task_logged_states.get(f"{task_name}_{key}", False)


@tasks.loop(seconds=BLOCK_CHECK_INTERVAL_SECONDS)
async def check_for_new_blocks():
    global last_known_block_height
    task_name = "check_for_new_blocks"
    logger.info(f"Task '{task_name}': Running...")

    if NOTIFICATION_CHANNEL_ID == 0:
        if not has_task_logged_once(task_name, "no_channel_id"):
            logger.warning(f"Task '{task_name}': NOTIFICATION_CHANNEL_ID is not set. New block notifications will not be sent.")
            set_task_logged_once(task_name, "no_channel_id")
        return

    channel = client.get_channel(NOTIFICATION_CHANNEL_ID)
    if not channel:
        if not has_task_logged_once(task_name, f"no_channel_{NOTIFICATION_CHANNEL_ID}"):
            logger.error(f"Task '{task_name}': Cannot find notification channel with ID: {NOTIFICATION_CHANNEL_ID}. Notifications will not be sent.")
            set_task_logged_once(task_name, f"no_channel_{NOTIFICATION_CHANNEL_ID}")
        return

    sidechain_data, error = await asyncio.to_thread(api_get_sidechain_stats)

    if error:
        logger.error(f"Task '{task_name}': Error fetching pool info: {error}")
        return

    if not sidechain_data or 'sidechain' not in sidechain_data:
        if not has_task_logged_once(task_name, "no_sidechain_key_in_pool_info"):
            logger.warning(f"Task '{task_name}': 'sidechain' key not found in pool_info response. API response: {str(sidechain_data)[:500]}")
            set_task_logged_once(task_name, "no_sidechain_key_in_pool_info")
        return

    current_block_info = sidechain_data['sidechain'].get('last_block')
    if not current_block_info or 'side_height' not in current_block_info:
        if not has_task_logged_once(task_name, "no_last_block_or_side_height"):
            logger.warning(f"Task '{task_name}': 'last_block' or 'side_height' not found in sidechain info. Data: {sidechain_data['sidechain']}")
            set_task_logged_once(task_name, "no_last_block_or_side_height")
        return

    try:
        current_block_height = int(current_block_info['side_height'])

        if last_known_block_height is None:
            last_known_block_height = current_block_height
            logger.info(f"Task '{task_name}': Initialized last known block height to {last_known_block_height}.")
            # Optionally send a startup message with the current latest block
            # embed = format_latest_block_embed(sidechain_data, context="initial_block")
            # await channel.send(content="Block monitoring started. Current latest block:", embed=embed)
            return

        if current_block_height > last_known_block_height:
            logger.info(f"Task '{task_name}': New block detected! Height: {current_block_height} (previously {last_known_block_height})")

            # Use the full sidechain_data for formatting, context helps tailor the message
            embed = format_latest_block_embed(sidechain_data, context="new_block_notification")
            # The title is now set within format_latest_block_embed
            # notification_message = f"🎉 **New Block Found on P2Pool Mini!** Height: {current_block_height}"

            try:
                await channel.send(embed=embed) # Send only embed as it contains title
                logger.info(f"Task '{task_name}': Sent new block notification to channel {NOTIFICATION_CHANNEL_ID} for block {current_block_height}.")
            except discord.Forbidden:
                logger.error(f"Task '{task_name}': Permission error sending to channel {NOTIFICATION_CHANNEL_ID}. Check bot permissions.")
            except discord.HTTPException as e_http:
                logger.error(f"Task '{task_name}': HTTP error sending notification: {e_http}")

            last_known_block_height = current_block_height
        elif current_block_height < last_known_block_height:
            # This could indicate a chain reorg or an issue with the API/data source
            logger.warning(f"Task '{task_name}': Current block height {current_block_height} is less than last known height {last_known_block_height}. Possible reorg or API issue.")
            # Decide how to handle this - for now, just update to current to avoid spamming if it's a persistent API issue.
            last_known_block_height = current_block_height
        # else: No new block, current height is same as last known.
            # logger.debug(f"Task '{task_name}': No new block. Current height {current_block_height}, last known {last_known_block_height}")

    except (IndexError, ValueError, KeyError) as e_parse:
        logger.error(f"Task '{task_name}': Error parsing block data from API response: {e_parse}. Block data: {sidechain_data.get('sidechain', {}).get('blocks', 'N/A')[:200]}")
    except Exception as e_unexpected:
        logger.error(f"Task '{task_name}': Unexpected error in new block check: {e_unexpected}", exc_info=True)

# --- WebSocket Client for Real-time Notifications ---
import websockets # Make sure to add 'websockets' to requirements.txt
import json

WEBSOCKET_URI = "wss://mini.p2pool.observer/api/events"
WEBSOCKET_RECONNECT_DELAY = 30  # seconds

async def handle_websocket_message(message_data: dict):
    """Handles incoming WebSocket messages."""
    global last_known_block_height # Access the global for comparison if needed, though WebSocket provides new blocks directly

    event_type = message_data.get('type')
    logger.debug(f"WebSocket: Received event type: {event_type}")

    if event_type in ['side_block', 'found_block']:
        block_data = message_data.get(event_type) # 'side_block' or 'found_block' key contains the data
        if not block_data:
            logger.warning(f"WebSocket: Event '{event_type}' had no associated block data.")
            return

        current_block_height = block_data.get('side_height') or block_data.get('height') # 'height' for found_block.main_block.height
        if current_block_height is None:
            logger.warning(f"WebSocket: Could not determine block height from event: {block_data}")
            return

        current_block_height = int(current_block_height)

        # Optional: Update last_known_block_height if using polling as fallback or for other checks
        # For pure WebSocket, this comparison might be less critical if we trust every event is 'new'
        # However, it's good for consistency and to avoid double-posting if polling is also active.
        if last_known_block_height is not None and current_block_height <= last_known_block_height:
            logger.info(f"WebSocket: Received block height {current_block_height} which is not newer than known {last_known_block_height}. Skipping notification.")
            return
        last_known_block_height = current_block_height


        logger.info(f"WebSocket: New block event! Type: {event_type}, Height: {current_block_height}")

        notification_channel_id_ws = NOTIFICATION_CHANNEL_ID # Use the globally configured channel ID
        if notification_channel_id_ws == 0:
            logger.warning("WebSocket: NOTIFICATION_CHANNEL_ID is not set. Cannot send new block notification.")
            return

        channel = client.get_channel(notification_channel_id_ws)
        if not channel:
            logger.error(f"WebSocket: Cannot find notification channel with ID: {notification_channel_id_ws}.")
            return

        # We need to adapt block_data to what format_latest_block_embed expects,
        # or create a new formatter for WebSocket events.
        # The format_latest_block_embed expects data similar to /api/pool_info.
        # Let's create a simplified embed for WebSocket for now, or adapt.

        embed_title = f"🎉 New P2Pool Mini Block ({event_type.replace('_', ' ').title()})!"
        embed = discord.Embed(title=embed_title, color=discord.Color.teal())

        if 'side_height' in block_data: # Common for side_block
             embed.add_field(name="Sidechain Height", value=block_data.get('side_height', 'N/A'), inline=True)
        if 'main_height' in block_data: # Common for side_block
             embed.add_field(name="Mainchain Height", value=block_data.get('main_height', 'N/A'), inline=True)

        if 'id' in block_data and event_type == 'found_block': # For main_block.id in found_block
            embed.add_field(name="Main Block ID", value=f"`{block_data.get('id', 'N/A')[:16]}...`", inline=True)
        elif 'template_id' in block_data : # For side_block
            embed.add_field(name="Template ID", value=f"`{block_data.get('template_id', 'N/A')[:16]}...`", inline=True)

        ts = block_data.get('timestamp')
        if ts:
            embed.add_field(name="Timestamp", value=f"<t:{ts}:R>", inline=True)

        difficulty = block_data.get('difficulty')
        if difficulty:
            embed.add_field(name="Difficulty", value=f"{difficulty:,}" if isinstance(difficulty, int) else difficulty, inline=True)

        miner_addr = block_data.get('miner_address') # Available in side_block directly
        if miner_addr:
            embed.add_field(name="Found By", value=f"`{miner_addr[:8]}...{miner_addr[-4:]}`", inline=True)

        if event_type == 'found_block' and 'main_block' in message_data: # More detailed for found_block
            main_block_details = message_data['main_block']
            embed.add_field(name="Mainnet Reward", value=f"{main_block_details.get('reward', 0) / 10**12:.6f} XMR", inline=True)


        embed.set_footer(text="Realtime via mini.p2pool.observer WebSocket")

        try:
            await channel.send(embed=embed)
            logger.info(f"WebSocket: Sent new block notification via WebSocket for height {current_block_height}.")
        except discord.Forbidden:
            logger.error(f"WebSocket: Permission error sending to channel {notification_channel_id_ws}.")
        except discord.HTTPException as e_http:
            logger.error(f"WebSocket: HTTP error sending notification: {e_http}")

    elif event_type == 'orphaned_block':
        # Handle orphaned blocks if desired
        logger.info(f"WebSocket: Orphaned block event received: {message_data}")
        # Potentially send a notification for orphaned blocks too
    else:
        logger.debug(f"WebSocket: Unhandled event type '{event_type}': {message_data}")


async def start_websocket_listener():
    """Connects to the WebSocket and listens for messages."""
    await client.wait_until_ready() # Ensure bot is ready before trying to send messages
    logger.info(f"WebSocket: Initiating connection to {WEBSOCKET_URI}")
    while True:
        try:
            async with websockets.connect(WEBSOCKET_URI) as websocket:
                logger.info(f"WebSocket: Connected to {WEBSOCKET_URI}")
                set_task_logged_once("websocket_listener", "connection_failed", value=False) # Reset failed log
                async for message in websocket:
                    try:
                        message_data = json.loads(message)
                        await handle_websocket_message(message_data)
                    except json.JSONDecodeError:
                        logger.error(f"WebSocket: Error decoding JSON from message: {message}")
                    except Exception as e:
                        logger.error(f"WebSocket: Error handling message: {e}", exc_info=True)
        except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
            if not has_task_logged_once("websocket_listener", "connection_closed_once"):
                logger.warning(f"WebSocket: Connection closed: {e}. Reconnecting in {WEBSOCKET_RECONNECT_DELAY}s.")
                set_task_logged_once("websocket_listener", "connection_closed_once")
            await asyncio.sleep(WEBSOCKET_RECONNECT_DELAY)
        except ConnectionRefusedError as e:
            if not has_task_logged_once("websocket_listener", "connection_refused_once"):
                logger.error(f"WebSocket: Connection refused to {WEBSOCKET_URI}: {e}. Retrying in {WEBSOCKET_RECONNECT_DELAY}s.")
                set_task_logged_once("websocket_listener", "connection_refused_once")
            await asyncio.sleep(WEBSOCKET_RECONNECT_DELAY)
        except Exception as e:
            if not has_task_logged_once("websocket_listener", "generic_error_once"):
                logger.error(f"WebSocket: Unexpected error in listener: {e}. Retrying in {WEBSOCKET_RECONNECT_DELAY}s.", exc_info=True)
                set_task_logged_once("websocket_listener", "generic_error_once")
            await asyncio.sleep(WEBSOCKET_RECONNECT_DELAY)


# --- Slash Commands ---

@tree.command(
    name="miner_info",
    description="Get P2Pool stats for a specific Monero miner address.",
    guild=GUILD_ID # Uses GUILD_ID if set, otherwise global
)
@discord.app_commands.describe(miner_address="The Monero wallet address of the miner")
async def miner_info_command(interaction: discord.Interaction, miner_address: str):
    """Slash command to get miner information."""
    logger.info(f"Received /miner_info command for address: {miner_address} from {interaction.user.name}")
    await interaction.response.defer(ephemeral=True) # Acknowledge interaction, thinking...

    # Use asyncio.to_thread to run the synchronous API call in a separate thread
    miner_data, error = await asyncio.to_thread(api_get_miner_info, miner_address)

    if error:
        logger.error(f"Error fetching miner info for {miner_address}: {error}")
        await interaction.followup.send(f"Error: {error}", ephemeral=True)
        return

    if not miner_data: # Should be caught by error, but as a safeguard
        logger.warning(f"No data returned for miner {miner_address}, though no explicit error.")
        await interaction.followup.send(f"Could not retrieve information for miner: `{miner_address}`.", ephemeral=True)
        return

    # Format and send the data
    # This part is highly dependent on the actual structure of `miner_data`
    # For now, sending raw-ish data. An embed would be much nicer.
    embed = format_miner_info_embed(miner_address, miner_data)
    await interaction.followup.send(embed=embed, ephemeral=True)


@tree.command(
    name="latest_block",
    description="Get information about the latest block on the P2Pool mini sidechain.",
    guild=GUILD_ID # Uses GUILD_ID if set, otherwise global
)
async def latest_block_command(interaction: discord.Interaction):
    """Slash command to get the latest block information."""
    logger.info(f"Received /latest_block command from {interaction.user.name}")
    await interaction.response.defer(ephemeral=True) # Acknowledge interaction

    sidechain_data, error = await asyncio.to_thread(api_get_sidechain_stats)

    if error:
        logger.error(f"Error fetching sidechain stats for /latest_block: {error}")
        await interaction.followup.send(f"Error: {error}", ephemeral=True)
        return

    if not sidechain_data:
        logger.warning("No sidechain data returned for /latest_block, though no explicit error.")
        await interaction.followup.send("Could not retrieve latest block information.", ephemeral=True)
        return

    # Assuming sidechain_data contains info about the latest block
    # The structure of this data needs to be known to extract block details.
    # For example, if it's in `sidechain_data['pool_statistics']['last_block_found']`
    # Or if `sidechain_data` itself is the block info.
    # This is a placeholder until the actual API structure is known.
    embed = format_latest_block_embed(sidechain_data) # Pass the whole data, formatter will parse
    await interaction.followup.send(embed=embed, ephemeral=True)


# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Initializing bot...")
    # The DISCORD_TOKEN and P2POOL_API_URL are checked at the start, so no need to re-check here.
    try:
        # client.run(DISCORD_TOKEN) # Keep this commented until all features are ready for live testing.
        logger.info("Bot script initialized. To run the bot, uncomment 'client.run(DISCORD_TOKEN)' in bot.py.")
        logger.warning("Remember to set your DISCORD_TOKEN and NOTIFICATION_CHANNEL_ID in the .env file. P2POOL_API_URL is now managed internally for the observer.")
        if GUILD_ID:
            logger.info(f"Test commands will be synced to GUILD ID: {GUILD_ID.id}")
        else:
            logger.info("Commands will be synced globally (may take time to propagate). Consider setting a GUILD_ID in .env for faster testing.")

    except Exception as e:
        logger.critical(f"An error occurred during bot startup or runtime: {e}", exc_info=True)
        # No need to call exit() here as the critical checks for tokens/URLs are done earlier.
        # If client.run() fails, it will raise its own exceptions.
    finally:
        logger.info("Bot script execution finished or was interrupted if client.run was not called.")
