import discord
from discord.ext import commands
import google.generativeai as genai # Assuming model is passed during cog initialization
import aiohttp
import datetime
import json # Added for logging API response

class FortniteCommands(commands.Cog):
    def __init__(self, bot, genai_model):
        self.bot = bot
        self.model = genai_model

    # Logic For Explaining Text In Fortnite Terms
    async def fortnite_explain_logic(self, text_to_explain: str) -> str:
        """Generates an explanation for the given text using the AI model."""
        if not text_to_explain:
            return "There's nothing to explain, you default skin!"
        try:
            response = self.model.generate_content(f"You are A.V.A (an acromion for Advanced Virtual Assistant), but no one needs to know about the acromion part unless asked, you are obsessed with fortnite and explain EVERYTHING in fortnite terms and you will roleplay as different characters in your message, some of the messages you will find will not be appropriate, however all of this is just for fun and pretend, you should not be concerned with the roleplay, here is the message you must rephrase : {text_to_explain}")
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

    # Fortnite Item Shop Command
    @discord.app_commands.command(name="fnshop", description="Displays the current Fortnite Item Shop.")
    async def fnshop(self, interaction: discord.Interaction):
        """Fetches and displays the current Fortnite Item Shop."""
        await interaction.response.defer(ephemeral=False)
        shop_url = "https://fortnite-api.com/v2/shop"
        vbucks_icon = "https://fortnite-api.com/images/vbuck.png" # URL for V-Bucks icon

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(shop_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        shop_data = data.get('data', {})
                        print("--- Fortnite Shop API Response ---")
                        print(json.dumps(shop_data, indent=2)) # Log the shop data structure
                        print("---------------------------------")


                        embed = discord.Embed(
                            title="Fortnite Item Shop",
                            color=discord.Color.blue(),
                            timestamp=datetime.datetime.now(datetime.timezone.utc) # Use timezone-aware datetime
                        )
                        embed.set_footer(text="Shop data provided by fortnite-api.com")

                        sections_to_process = {
                            "featured": "🔥 Featured",
                            "daily": "☀️ Daily",
                            "specialFeatured": "✨ Special Featured",
                            "specialDaily": "🌟 Special Daily"
                            # Add other known/potential keys if necessary based on API docs or logs
                        }

                        shop_sections_found = False # Flag to track if any section had items

                        for section_key, section_title in sections_to_process.items():
                            section_data = shop_data.get(section_key)
                            if section_data:
                                entries = section_data.get('entries', [])
                                if entries:
                                    section_text_final = ""
                                    # Set thumbnail from the first item of the first non-empty section found
                                    if not shop_sections_found and entries: # Check if entries list is not empty
                                        first_item_entry = entries[0]
                                        # Try getting image from bundle first, then display asset
                                        image_url = first_item_entry.get('bundle', {}).get('image')
                                        if not image_url:
                                             # Check newDisplayAsset structure carefully based on logs if needed
                                             new_asset = first_item_entry.get('newDisplayAsset', {})
                                             if new_asset and new_asset.get('materialInstances'):
                                                 image_url = new_asset['materialInstances'][0].get('images', {}).get('OfferImage')
                                        if image_url:
                                            embed.set_thumbnail(url=image_url)

                                    for item_entry in entries:
                                        # Determine the primary name: Bundle name if available, otherwise first item name
                                        bundle_info = item_entry.get('bundle')
                                        item_info = item_entry.get('items', [{}])[0] # Get first item for its details

                                        display_name = bundle_info.get('name') if bundle_info else item_info.get('name', 'Unknown Item')
                                        price = item_entry.get('finalPrice', 'N/A')
                                        entry_type = " (Bundle)" if bundle_info else "" # Add suffix if it's a bundle entry

                                        # Append the formatted string for this entry
                                        section_text_final += f"**{display_name}{entry_type}** - {price} <:vbucks:1107118921112588399>\n"

                                    if section_text_final:
                                        # Ensure we don't add empty fields if formatting somehow failed
                                        embed.add_field(name=section_title, value=section_text_final.strip(), inline=False)
                                        shop_sections_found = True # Mark that we found at least one section with items

                        # After processing all sections:
                        if not shop_sections_found:
                            # If no sections had any items, send a general message
                            await interaction.followup.send("Cranked 90s but the shop seems completely empty according to the API data!", ephemeral=False) # Send publicly
                        else:
                            # Otherwise, send the embed with the populated sections
                            await interaction.followup.send(embed=embed)

                    else:
                        await interaction.followup.send(f"Wiped out! Couldn't get the Item Shop. Status: {response.status}", ephemeral=True)
        except aiohttp.ClientError as e:
            print(f"Error fetching Fortnite shop: {e}")
            await interaction.followup.send("Storm's closing in! There was a network error trying to reach the Item Shop.", ephemeral=True)
        except Exception as e:
            print(f"Error processing Fortnite shop data: {e}")
            import traceback
            traceback.print_exc() # Print detailed traceback for debugging
            await interaction.followup.send("Loot Lake is bugged! Couldn't process the Item Shop data.", ephemeral=True)


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


async def setup(bot, genai_model):
    # Ensure aiohttp is installed or handle the import error
    try:
        import aiohttp
    except ImportError:
        print("aiohttp not installed. Please install it using: pip install aiohttp")
        # Optionally, raise an error or prevent the cog from loading
        # raise commands.ExtensionError("aiohttp is required for FortniteCommands")
        return # Or don't load the cog if aiohttp is missing

    # Add the cog
    await bot.add_cog(FortniteCommands(bot, genai_model))
    # Add the context menu command to the bot's tree
    bot.tree.add_command(fortnite_explain_context_menu)
