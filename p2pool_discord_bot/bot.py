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
P2POOL_API_URL = os.getenv("P2POOL_API_URL")
NOTIFICATION_CHANNEL_ID_STR = os.getenv("NOTIFICATION_CHANNEL_ID")
GUILD_ID_STR = os.getenv("GUILD_ID")

# --- Validate Environment Variables ---
if not DISCORD_TOKEN:
    logger.error("CRITICAL: DISCORD_TOKEN not found in .env file or environment variables. Bot cannot start.")
    exit()

if not P2POOL_API_URL:
    logger.error("CRITICAL: P2POOL_API_URL not found in .env file or environment variables. Bot cannot start.")
    exit()

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

        check_for_new_blocks.start()
        logger.info("Started 'check_for_new_blocks' background task.")

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
    embed.add_field(name="Hashrate (Current)", value=data.get('hashrate_24h', 'N/A'), inline=True) # Example field
    embed.add_field(name="Total Hashes", value=data.get('total_hashes', 'N/A'), inline=True) # Example field
    embed.add_field(name="Last Share Submitted", value=data.get('last_share_timestamp', 'N/A'), inline=True) # Example field
    embed.add_field(name="Balance Due", value=data.get('balance_due', 'N/A'), inline=True) # Example field
    embed.add_field(name="Total Paid", value=data.get('total_paid', 'N/A'), inline=True) # Example field

    # Add more fields as available and relevant from your P2Pool API
    # This is highly dependent on the actual API response structure.
    # For example:
    # if 'charts' in data and 'hashrate' in data['charts']:
    #     embed.add_field(name="Historical Hashrate", value="See chart data (if available)", inline=False)

    embed.set_footer(text="Data from P2Pool Mini Sidechain")
    return embed

def format_latest_block_embed(data: dict) -> discord.Embed:
    """Formats latest block data into a Discord embed."""
    if not data or 'sidechain' not in data or not data['sidechain'].get('blocks'):
        embed = discord.Embed(
            title="Latest Block Information",
            description="Could not retrieve latest block information or no blocks found.",
            color=discord.Color.orange()
        )
        return embed

    # Assuming 'blocks' is a list of block strings like "height:hash:timestamp:difficulty:value"
    # And the first one is the latest. This structure is a guess based on some P2Pool APIs.
    # The actual structure from YOUR P2Pool Mini API /stats endpoint needs to be confirmed.

    latest_block_str = data['sidechain']['blocks'][0] # Example: "height:hash:timestamp:difficulty:value"
    parts = latest_block_str.split(':')

    if len(parts) < 5:
        return discord.Embed(title="Error", description="Latest block data format is unrecognized.", color=discord.Color.red())

    height = parts[0]
    block_hash = parts[1]
    # timestamp = datetime.fromtimestamp(int(parts[2])).strftime('%Y-%m-%d %H:%M:%S UTC') if parts[2].isdigit() else 'N/A'
    timestamp_unix = int(parts[2]) if parts[2].isdigit() else 0
    difficulty = parts[3]
    # value_atomic = int(parts[4])
    # value_xmr = value_atomic / 10**12 # Monero has 12 decimal places

    embed = discord.Embed(
        title="New Block Found on P2Pool Mini!",
        color=discord.Color.green()
    )
    embed.add_field(name="Height", value=height, inline=True)
    embed.add_field(name="Hash", value=f"`{block_hash[:16]}...`", inline=True)
    embed.add_field(name="Timestamp", value=f"<t:{timestamp_unix}:R>" if timestamp_unix else "N/A", inline=True) # Relative time
    embed.add_field(name="Difficulty", value=difficulty, inline=True)
    # embed.add_field(name="Reward", value=f"{value_xmr:.6f} XMR", inline=True) # Example for Monero

    # Add other relevant fields like effort, miner if available
    # miner_address = data['sidechain'].get('miners_found_blocks', {}).get(height, 'N/A')
    # embed.add_field(name="Found By", value=f"`{miner_address[:8]}...`" if miner_address != 'N/A' else 'N/A', inline=True)

    embed.set_footer(text="P2Pool Mini Sidechain Monitor")
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
        logger.error(f"Task '{task_name}': Error fetching sidechain stats: {error}")
        return

    if not sidechain_data or 'sidechain' not in sidechain_data or not sidechain_data['sidechain'].get('blocks'):
        if not has_task_logged_once(task_name, "no_valid_block_data"):
            logger.warning(f"Task '{task_name}': No valid block data found in sidechain stats response. API response: {str(sidechain_data)[:500]}")
            set_task_logged_once(task_name, "no_valid_block_data")
        return

    try:
        # Assuming 'blocks' is a list of block strings "height:hash:timestamp:difficulty:value"
        # and the first one is the latest. This structure needs confirmation from the user/API docs.
        latest_block_str = sidechain_data['sidechain']['blocks'][0]
        parts = latest_block_str.split(':')
        if len(parts) < 1 or not parts[0].isdigit(): # Basic check for height
            logger.error(f"Task '{task_name}': Could not parse block height from block string: {latest_block_str}")
            return

        current_block_height = int(parts[0])

        if last_known_block_height is None:
            # First run after bot starts or variable reset
            last_known_block_height = current_block_height
            logger.info(f"Task '{task_name}': Initialized last known block height to {last_known_block_height}.")
            # Optionally, send a startup message or the current latest block on first successful check
            # embed = format_latest_block_embed(sidechain_data)
            # await channel.send(f"Block monitoring started. Current latest block on P2Pool Mini:", embed=embed)
            return

        if current_block_height > last_known_block_height:
            logger.info(f"Task '{task_name}': New block detected! Height: {current_block_height} (previously {last_known_block_height})")

            embed = format_latest_block_embed(sidechain_data) # Use the same embed formatter
            notification_message = f"🎉 **New Block Found on P2Pool Mini!** Height: {current_block_height}"

            try:
                await channel.send(content=notification_message, embed=embed)
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
        logger.warning("Remember to set your DISCORD_TOKEN, P2POOL_API_URL, and NOTIFICATION_CHANNEL_ID in the .env file.")
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
