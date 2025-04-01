#   _             _  
#  /_|   (  /    /_| 
# (  |.  |_/ .  (  | 
# 
# An acromion for Advanced Virtual Assistant                 

import discord
from discord.ext import commands
import os
import google.generativeai as genai
from dotenv import load_dotenv
import asyncio # Added for loading cogs

load_dotenv()

# Replace with your actual bot token
TOKEN = os.getenv("DISCORD-TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE-API")

genai.configure(api_key=GOOGLE_API_KEY)
# Try the 'gemini-1.5-flash-latest' model
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# Set up the bot with slash commands
intents = discord.Intents.default()
intents.message_content = True # Ensure message content intent is enabled if needed by cogs

# Define the bot instance
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)

# Store the model globally or pass it appropriately
# For simplicity, keeping it global here, but consider dependency injection for larger bots
genai_model = model

@bot.event
async def on_ready():
    """Event triggered when the bot is ready."""
    print(f'{bot.user.name} has woken up from her slumber!')
    await bot.change_presence(activity=discord.Game(name="Something Something say gex and/or Sesbian Lex"))
    print("Attempting to sync commands...")
    try:
        # Sync commands registered via cogs
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

async def load_extensions():
    """Loads all command extensions (cogs)."""
    initial_extensions = [
        'ping_command',
        'fortnite_commands',
        'genshin_commands'
    ]
    for extension_name in initial_extensions:
        try:
            # Pass the genai_model to setups that need it
            if extension_name in ['fortnite_commands', 'genshin_commands']:
                 # Dynamically import the setup function and call it with the model
                module = __import__(extension_name)
                if hasattr(module, 'setup'):
                    await module.setup(bot, genai_model)
                    print(f'Successfully loaded extension {extension_name} with model.')
                else:
                     print(f'Error loading {extension_name}: setup function not found.')
            else:
                await bot.load_extension(extension_name)
                print(f'Successfully loaded extension {extension_name}.')
        except commands.ExtensionNotFound:
            print(f'Error loading extension {extension_name}: Not found.')
        except commands.ExtensionAlreadyLoaded:
            print(f'Extension {extension_name} is already loaded.')
        except Exception as e:
            print(f'Failed to load extension {extension_name}. Error: {e}')
            import traceback
            traceback.print_exc()


async def main():
    """Main entry point for the bot."""
    async with bot:
        await load_extensions()
        await bot.start(TOKEN)

if __name__ == "__main__":
    # Run the main async function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutting down.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Made with <3
# By Eliyuh S.
