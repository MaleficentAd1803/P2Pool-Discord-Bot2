import requests
import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load P2POOL_API_URL from .env to be self-contained or if used independently
# In bot.py, this is already loaded, but good practice for a module.
load_dotenv()
P2POOL_API_URL = os.getenv("P2POOL_API_URL")

# Standard P2Pool API endpoints (these might vary based on the specific P2Pool instance/fork)
# It's crucial to confirm these with the user or P2Pool documentation.
# For XMR P2Pool, common endpoints are:
# - /stats (general pool stats, often includes sidechain info)
# - /miners/<miner_address> (specific miner stats) - This might not be standard on all pools.
#   Often, miner stats are part of a general /local_stats or similar if connected to your own node,
#   or part of a global miners list on public pool APIs.
# For the mini chain, it might be something like /mini/stats or similar.
# Let's assume generic names for now and they can be adjusted.

API_TIMEOUT_SECONDS = 10 # Configurable timeout for API requests

async def get_p2pool_sidechain_stats():
    """
    Fetches general sidechain statistics from the P2Pool API.
    This should ideally include information about the latest block.
    """
    if not P2POOL_API_URL:
        logger.error("P2POOL_API_URL is not set. Cannot fetch sidechain stats.")
        return None, "P2POOL_API_URL not configured."

    # Common endpoints: /stats, /pool/stats, /network/stats, /mini/stats
    # User needs to confirm the correct endpoint for their mini pool.
    # Using a placeholder relative path for now.
    # IMPORTANT: This endpoint '/stats' is a guess for mini chain.
    endpoint = f"{P2POOL_API_URL.rstrip('/')}/stats"

    logger.debug(f"Fetching P2Pool sidechain stats from: {endpoint}")
    try:
        response = requests.get(endpoint, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        data = response.json()
        logger.debug(f"Successfully fetched sidechain stats: {data}")
        return data, None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching P2Pool stats from {endpoint}: {e}")
        return None, f"API request failed with status {e.response.status_code}."
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error fetching P2Pool stats from {endpoint}: {e}")
        return None, "Could not connect to the P2Pool API."
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout fetching P2Pool stats from {endpoint}: {e}")
        return None, "The request to the P2Pool API timed out."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching P2Pool stats from {endpoint}: {e}")
        return None, "An unexpected error occurred while fetching data from P2Pool."
    except ValueError as e: # Includes JSONDecodeError
        logger.error(f"Error decoding JSON response from {endpoint}: {e}")
        return None, "Invalid JSON response from the P2Pool API."


async def get_miner_info(miner_address: str):
    """
    Fetches statistics for a specific miner from the P2Pool API.
    """
    if not P2POOL_API_URL:
        logger.error("P2POOL_API_URL is not set. Cannot fetch miner info.")
        return None, "P2POOL_API_URL not configured."
    if not miner_address:
        logger.warning("Miner address is empty.")
        return None, "Miner address cannot be empty."

    # Common endpoints: /miners/<address>, /pool/miner/<address>
    # The structure of this data can vary significantly.
    # IMPORTANT: This endpoint '/miners/{miner_address}' is a guess.
    # Some pools might not have a direct per-miner endpoint but include miners in a general stats call.
    endpoint = f"{P2POOL_API_URL.rstrip('/')}/miners/{miner_address}"

    logger.debug(f"Fetching P2Pool miner info for {miner_address} from: {endpoint}")
    try:
        response = requests.get(endpoint, timeout=API_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Successfully fetched miner info for {miner_address}: {data}")
        return data, None
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching miner info from {endpoint} for {miner_address}: {e}")
        if e.response.status_code == 404:
            return None, f"Miner address {miner_address} not found on the pool."
        return None, f"API request failed with status {e.response.status_code}."
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error fetching miner info from {endpoint} for {miner_address}: {e}")
        return None, "Could not connect to the P2Pool API."
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout fetching miner info from {endpoint} for {miner_address}: {e}")
        return None, "The request to the P2Pool API timed out."
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching miner info for {miner_address} from {endpoint}: {e}")
        return None, "An unexpected error occurred while fetching miner data from P2Pool."
    except ValueError as e: # Includes JSONDecodeError
        logger.error(f"Error decoding JSON response from {endpoint} for {miner_address}: {e}")
        return None, "Invalid JSON response from the P2Pool API for miner data."

if __name__ == '__main__':
    # Example usage (for testing this module directly)
    # You would need to have a .env file in the same directory or have environment variables set.
    import asyncio

    async def main():
        print("Testing P2Pool API functions...")
        if not P2POOL_API_URL:
            print("P2POOL_API_URL not set in .env. Please set it for testing.")
            print("Example: P2POOL_API_URL=http://127.0.0.1:9327 (for XMR P2Pool mini)")
            return

        print(f"Using API URL: {P2POOL_API_URL}")

        # Test get_p2pool_sidechain_stats
        stats_data, error = await get_p2pool_sidechain_stats()
        if error:
            print(f"Error fetching sidechain stats: {error}")
        elif stats_data:
            print("\nSidechain Stats (first few items):")
            # Print a snippet of the stats, as it can be large
            if isinstance(stats_data, dict):
                for i, (k, v) in enumerate(stats_data.items()):
                    if i < 5: # Print first 5 key-value pairs
                        print(f"  {k}: {str(v)[:100]}") # Truncate long values
                    else:
                        break
            elif isinstance(stats_data, list) and stats_data:
                 print(f"  {str(stats_data[0])[:200]}") # Print first item if list
            else:
                print(f"  {str(stats_data)[:200]}")


        # Test get_miner_info (replace with a known test miner address if possible)
        # This will likely fail if the endpoint isn't /miners/<address> or if the address is invalid.
        # For Monero, a primary address is 95 chars long.
        test_miner_address = "MONERO_PRIMARY_ADDRESS_HERE_FOR_TESTING"
        # Check if a test address is provided via env for easier testing
        test_miner_address = os.getenv("TEST_MINER_ADDRESS", test_miner_address)

        if "MONERO_PRIMARY_ADDRESS_HERE_FOR_TESTING" in test_miner_address:
            print(f"\nSkipping miner info test as TEST_MINER_ADDRESS is not set in .env or is placeholder.")
        else:
            print(f"\nTesting miner info for address: {test_miner_address}...")
            miner_data, error = await get_miner_info(test_miner_address)
            if error:
                print(f"Error fetching miner info: {error}")
            elif miner_data:
                print("\nMiner Info (first few items):")
                if isinstance(miner_data, dict):
                    for i, (k, v) in enumerate(miner_data.items()):
                        if i < 5:
                             print(f"  {k}: {str(v)[:100]}")
                        else:
                            break
                else:
                    print(f"  {str(miner_data)[:200]}")


    # To run this test part: python p2pool_discord_bot/p2pool_api.py
    # Ensure you have a .env file in p2pool_discord_bot/ with P2POOL_API_URL (and optionally TEST_MINER_ADDRESS)
    # Or, if running from the root, ensure .env is in the root and paths are adjusted or modules handled.
    # For simplicity, this assumes .env is co-located or picked up by load_dotenv().
    if P2POOL_API_URL: # Only run main if API URL is present
        asyncio.run(main())
    else:
        print("P2POOL_API_URL not set. Cannot run p2pool_api.py test functions.")
        print("Please create a .env file in the project root (e.g., p2pool_discord_bot/.env or ./ .env)")
        print("with P2POOL_API_URL='http://your_p2pool_node_ip:port'")
