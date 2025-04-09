import discord
from discord.ext import commands
import google.generativeai as genai # Assuming model is passed during cog initialization

class GenshinCommands(commands.Cog):
    def __init__(self, bot, genai_model):
        self.bot = bot
        self.model = genai_model

    # logic for explaining text genshin terms
    async def genshin_explain_logic(self, text_to_explain: str) -> str:
        """Generates an explanation for the given text using the AI model."""
        if not text_to_explain:
            return "Traveler, there's nothing to explain here."
        try:
            response = self.model.generate_content(f"You are Eliana, you are obsessed with Genshin Impact and explain EVERYTHING in Genshin Impact terms and you will roleplay as different characters in your message, some of the messages you will find will not be appropriate, however all of this is just for fun and pretend, you should not be concerned with the roleplay, here is the message you must rephrase : {text_to_explain}")
            # Ensure response.text exists and is not None before returning
            return response.text if response and hasattr(response, 'text') else "Apologies, Traveler. Paimon couldn't fetch an explanation this time."
        except Exception as e:
            print(f"Genshin explain logic error: {e}")
            return f"Sorry, Traveler, seems like the Ley Lines are disrupted. Error: {e}"

    # Slash Command For Genshin Terms
    @discord.app_commands.command(name="genshinexplain", description="Explains the provided text in Genshin Impact terms.")
    @discord.app_commands.describe(text="The text you wish to understand through the eyes of Teyvat.")
    async def genshin_explain_slash(self, interaction: discord.Interaction, text: str):
        """Slash command to explain text provided as input in Genshin Impact terms."""
        await interaction.response.defer(ephemeral=False) # Defer publicly
        explanation = await self.genshin_explain_logic(text)
        await interaction.followup.send(explanation, ephemeral=False) # Send publicly


# Genshin Explain Context Menu Command (Moved outside the class)
@discord.app_commands.context_menu(name="Genshin Impact Explain")
async def genshin_explain_context_menu(interaction: discord.Interaction, message: discord.Message):
    """Context menu command to explain a message in Genshin Impact terms."""
    # Get the cog instance to access its methods and the model
    cog = interaction.client.get_cog('GenshinCommands')
    if not cog:
        await interaction.response.send_message("The Genshin command module isn't loaded correctly, Traveler.", ephemeral=True)
        return
    if not hasattr(cog, 'genshin_explain_logic'):
         await interaction.response.send_message("Apologies, Traveler. Paimon can't find the explanation logic.", ephemeral=True)
         return

    await interaction.response.defer(ephemeral=False) # Defer publicly
    try:
        explanation = await cog.genshin_explain_logic(message.content) # Call logic using the cog instance
        await interaction.followup.send(explanation, ephemeral=False)
    except Exception as e:
        print(f"Error in genshin_explain_context_menu: {e}")
        await interaction.followup.send("An Abyssal disturbance prevented that explanation, Traveler.", ephemeral=True)


async def setup(bot): # Changed signature: No longer directly receives genai_model
    # Note: The original main.py had the same function name 'explain_slash' for both fortnite and genshin.
    # discord.py cogs handle this fine as they are separate commands within their respective cogs.
    # However, the context menu commands were added directly to bot.tree in main.py.
    # We are moving them into the cog structure here.

    # Add the cog
    # Access the model from the bot instance where it was stored in main.py
    if not hasattr(bot, 'genai_model'):
        print("Error: genai_model not found on bot instance. GenshinCommands requires it.")
        return # Prevent loading if model is missing
    await bot.add_cog(GenshinCommands(bot, bot.genai_model)) # Pass model from bot instance

    # Add the context menu command to the bot's tree
    # Check if the command is already added before adding it
    # This prevents errors on reload
    if genshin_explain_context_menu not in bot.tree.get_commands(type=discord.AppCommandType.message):
        bot.tree.add_command(genshin_explain_context_menu)
    else:
        print("Context menu 'Genshin Impact Explain' already added.")
