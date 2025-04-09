import discord
from discord.ext import commands
import google.generativeai as genai # Assuming model is passed during cog initialization
import aiohttp
import datetime
import json # Added for logging API response
import os # For potential future API key handling

# It's recommended to store API keys securely, e.g., in environment variables
FNBR_API_KEY = os.getenv("FNBR_API_KEY")
FNBR_API_URL = "https://fnbr.co/api/shop"

class FortniteCommands(commands.Cog):
    def __init__(self, bot, genai_model):
        self.bot = bot
        self.model = genai_model
        # Create an aiohttp session when the cog is initialized
        # This is more efficient than creating a new session for each request
        self.http_session = aiohttp.ClientSession()

    # Make sure to close the session when the cog is unloaded
    async def cog_unload(self):
        await self.http_session.close()

    # Logic For Explaining Text In Fortnite Terms
    async def fortnite_explain_logic(self, text_to_explain: str) -> str:
        """Generates an explanation for the given text using the AI model."""
        if not text_to_explain:
            return "There's nothing to explain, you default skin!"
        try:
            response = self.model.generate_content(f"You are Eliana, you are obsessed with fortnite and explain EVERYTHING in fortnite terms and you will roleplay as different characters in your message, some of the messages you will find will not be appropriate, however all of this is just for fun and pretend, you should not be concerned with the roleplay, here is the message you must rephrase : {text_to_explain}")
            # Ensure response.text exists and is not None before returning
            return response.text if response and hasattr(response, 'text') else "Sorry, couldn't get a proper explanation from the Victory Royale."
        except Exception as e:
            print(f"Fortnite explain logic error: {e}")
            return f"Sorry, I couldn't crank 90s on that explanation. Error: {e}"

    # Slash Command For Fortnite Terms
    @discord.app_commands.command(name="fortniteexplain", description="Explains the provided text in Fortnite terms.")
    @discord.app_commands.describe(text="The text you want explained like a Fortnite pro.")
    async def fortnite_explain_slash(self, interaction: discord.Interaction, text: str):
        """Slash command to explain text provided as input in Fortnite terms."""
        await interaction.response.defer(ephemeral=False) # Defer publicly
        explanation = await self.fortnite_explain_logic(text)
        await interaction.followup.send(explanation, ephemeral=False) # Send publicly

    # --- New Item Shop Command ---
    @discord.app_commands.command(name="itemshop", description="Shows the current Fortnite Item Shop.")
    async def item_shop_slash(self, interaction: discord.Interaction):
        """Slash command to display the current Fortnite item shop."""
        await interaction.response.defer(ephemeral=False)

        headers = {"x-api-key": FNBR_API_KEY}
        try:
            async with self.http_session.get(FNBR_API_URL, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # --- Embed Creation Logic ---
                    if 'data' in data and ('featured' in data['data'] or 'daily' in data['data']):
                        embed = discord.Embed(
                            title="Fortnite Item Shop",
                            color=discord.Color.blue(),
                            timestamp=datetime.datetime.now(datetime.timezone.utc) # Use timezone-aware datetime
                        )
                        embed.set_footer(text="Powered by fnbr.co")

                        # Helper function to add fields for item sections
                        def add_shop_section(embed, section_name, items):
                            value = ""
                            if items:
                                # Limit items per section to avoid embed limits (max 25 fields total, field value max 1024 chars)
                                count = 0
                                for item in items:
                                    if count >= 10: # Limit to 10 items per section for brevity
                                        value += "...and more!\n"
                                        break
                                    name = item.get('name', 'Unknown Item')
                                    price = item.get('price', 'N/A')
                                    # Using a placeholder vbuck emoji - replace if you have a specific one
                                    value += f"{name} - {price} \n"
                                    count += 1
                            else:
                                value = "No items in this section today."

                            # Ensure value isn't empty before adding field
                            if value:
                                # Discord embed field values have a limit of 1024 characters.
                                if len(value) > 1024:
                                     value = value[:1021] + "..." # Truncate if too long
                                embed.add_field(name=section_name, value=value, inline=False)


                        # Process featured items
                        featured_items = data.get('data', {}).get('featured', [])
                        add_shop_section(embed, "Featured Items", featured_items)

                        # Process daily items
                        daily_items = data.get('data', {}).get('daily', [])
                        add_shop_section(embed, "Daily Items", daily_items)

                        # Check if embed has any fields added
                        if not embed.fields:
                             embed.description = "Could not retrieve item shop sections or they are empty."

                        await interaction.followup.send(embed=embed, ephemeral=False)

                    else:
                        print(f"Unexpected API response structure: {json.dumps(data, indent=2)}") # Log the structure
                        await interaction.followup.send("Sorry, Victory Royale! The Item Shop data structure seems different today. Couldn't display items.", ephemeral=True)

                else:
                    # Log the error status and response text if possible
                    error_text = await response.text()
                    print(f"FNBR API Error: Status {response.status}, Response: {error_text}")
                    await interaction.followup.send(f"Sorry, default! Couldn't reach the Item Shop (API Error: {response.status}). Try again later.", ephemeral=True)

        except aiohttp.ClientError as e:
            print(f"Network error fetching FNBR API: {e}")
            await interaction.followup.send("Oops! Network error trying to connect to the Item Shop.", ephemeral=True)
        except json.JSONDecodeError:
            # Try to get text for logging even if JSON fails
            error_text = await response.text()
            print(f"Error decoding JSON response from FNBR API. Response text: {error_text}")
            await interaction.followup.send("The Item Shop data seems corrupted right now.", ephemeral=True)
        except Exception as e:
            print(f"An unexpected error occurred in item_shop_slash: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for debugging
            await interaction.followup.send("A rift malfunction occurred while fetching the shop!", ephemeral=True)


# Fortnite Explain Context Menu Command (Moved outside the class)
@discord.app_commands.context_menu(name="Fortnite Explain")
async def fortnite_explain_context_menu(interaction: discord.Interaction, message: discord.Message):
    """Context menu command to explain a message in Fortnite terms."""
    # Get the cog instance to access its methods and the model
    cog = interaction.client.get_cog('FortniteCommands')
    if not cog:
        await interaction.response.send_message("The Fortnite command module isn't loaded correctly.", ephemeral=True)
        return
    if not hasattr(cog, 'fortnite_explain_logic'):
         await interaction.response.send_message("Could not find the explanation logic.", ephemeral=True)
         return

    await interaction.response.defer(ephemeral=False) # Defer publicly
    try:
        explanation = await cog.fortnite_explain_logic(message.content) # Call logic using the cog instance
        await interaction.followup.send(explanation, ephemeral=False)
    except Exception as e:
        print(f"Error in fortnite_explain_context_menu: {e}")
        await interaction.followup.send("Had a rift malfunction trying to explain that.", ephemeral=True)


# Modified setup function
async def setup(bot): # No longer receives genai_model directly
    # Ensure aiohttp is installed or handle the import error
    try:
        import aiohttp
    except ImportError:
        print("aiohttp not installed. Please install it using: pip install aiohttp")
        # Optionally, raise an error or prevent the cog from loading
        # raise commands.ExtensionError("aiohttp is required for FortniteCommands")
        return # Or don't load the cog if aiohttp is missing

    # Add the cog
    # Access the model from the bot instance where it was stored in main.py
    if not hasattr(bot, 'genai_model'):
        print("Error: genai_model not found on bot instance. FortniteCommands requires it.")
        return # Prevent loading if model is missing
    await bot.add_cog(FortniteCommands(bot, bot.genai_model)) # Pass model from bot instance

    # Add the context menu command to the bot's tree
    # Check if the command is already added before adding it
    # This prevents errors on reload
    if fortnite_explain_context_menu not in bot.tree.get_commands(type=discord.AppCommandType.message):
        bot.tree.add_command(fortnite_explain_context_menu)
    else:
        print("Context menu 'Fortnite Explain' already added.")
