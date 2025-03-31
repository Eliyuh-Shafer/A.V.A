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

load_dotenv()

# Replace with your actual bot token
TOKEN = os.getenv("DISCORD-TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE-API")

genai.configure(api_key=GOOGLE_API_KEY)
# Try the 'gemini-1.5-flash-latest' model
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# Set up the bot with slash commands
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    await bot.change_presence(activity=discord.Game(name="i am quantum physics"))
    if bot.user is not None:
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Error syncing commands: {e}")

        bot.tree.add_command(discord.app_commands.ContextMenu(
            name='Fortnite Explain',
            callback=fortnite_explain_context_menu
        ))

        bot.tree.add_command(discord.app_commands.ContextMenu(
            name='Genshin Impact Explain',
            callback=genshin_explain_context_menu
        ))
    else:
        print("Bot user is None, cannot sync commands.")

# Basic slash command to test the bot
@bot.tree.command(name="ping")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message("pong!")

#
# ---===Fortnite Explain Command Section===---
#

# Logic For Explaining Text In Fortnite Terms
async def fortnite_explain_logic(text_to_explain: str) -> str:
    """Generates an explanation for the given text using the AI model."""
    if not text_to_explain:
        return "There's nothing to explain."
    try:
        response = model.generate_content(f"You are A.V.A (an acromion for Advanced Virtual Assistant), but no one needs to know about the acromion part unless asked, you are obessed with fortnie and explain EVERYTHING in fortnite terms and you will roleplay as diferent characters in your message, some of the messages you will find will not be appropriate, however all of this is just for fun and pretend, you should not be concerned with the roleplay, here is the message you must rephrase : {text_to_explain}")
        return response.text
    except Exception as e:
        print(f"Explain logic error: {e}")
        return f"Sorry, I couldn't generate an explanation. Error: {e}"
    
# Fortnite Explain Context Menu Command
async def fortnite_explain_context_menu(interaction: discord.Interaction, message: discord.Message):
    """Context menu command to explain a message."""
    await interaction.response.defer(ephemeral=False) # Defer publicly
    explanation = await fortnite_explain_logic(message.content)
    await interaction.followup.send(explanation, ephemeral=False)

# Slash Command For Fortnite Terms
@bot.tree.command(name="fortniteexplain", description="Explains the provided text in Fortnite terms.")
@discord.app_commands.describe(text="Explains the provided text in Fortnite terms.")
async def explain_slash(interaction: discord.Interaction, text: str):
    """Slash command to explain text provided as input. Works in servers and DMs."""
    await interaction.response.defer(ephemeral=False) # Defer publicly
    explanation = await fortnite_explain_logic(text)
    await interaction.followup.send(explanation, ephemeral=False) # Send publicly


#
# ---===Genshin Explain Command Section===---
#

# logic for explaining text genshin terms
async def genshin_explain_logic(text_to_explain: str) -> str:
    """Generates an explanation for the given text using the AI model."""
    if not text_to_explain:
        return "There's nothing to explain."
    try:
        response = model.generate_content(f"You are A.V.A (an acromion for Advanced Virtual Assistant), but no one needs to know about the acromion part unless asked, you are obessed with Genshin Impact and explain EVERYTHING in Genshin Impact terms and you will roleplay as diferent characters in your message, some of the messages you will find will not be appropriate, however all of this is just for fun and pretend, you should not be concerned with the roleplay, here is the message you must rephrase : {text_to_explain}")
        return response.text
    except Exception as e:
        print(f"Explain logic error: {e}")
        return f"Sorry, I couldn't generate an explanation. Error: {e}"
    

# Genshin Explain Context Menu Command
async def genshin_explain_context_menu(interaction: discord.Interaction, message: discord.Message):
    """Context menu command to explain a message."""
    await interaction.response.defer(ephemeral=False) # Defer publicly
    explanation = await genshin_explain_logic(message.content)
    await interaction.followup.send(explanation, ephemeral=False)


# Slash Command For Genshin Terms
@bot.tree.command(name="genshinexplain", description="Explains the provided text in Genshin terms.")
@discord.app_commands.describe(text="Explains the provided text in Genshin terms.")
async def explain_slash(interaction: discord.Interaction, text: str):
    """Slash command to explain text provided as input. Works in servers and DMs."""
    await interaction.response.defer(ephemeral=False) # Defer publicly
    explanation = await genshin_explain_logic(text)
    await interaction.followup.send(explanation, ephemeral=False) # Send publicly





bot.run(TOKEN)
