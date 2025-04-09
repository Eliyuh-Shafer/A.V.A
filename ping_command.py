import discord
from discord.ext import commands

class PingCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="ping", description="Responds with the bot's latency.")
    async def ping(self, interaction: discord.Interaction):
        """Slash command to check the bot's latency."""
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! (Latency: {latency_ms}ms)")

async def setup(bot):
    await bot.add_cog(PingCommand(bot))
