import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import logging
import collections # For deque
from typing import Optional # For type hints

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Define the cache directory
CACHE_DIR = "music_cache"

class VoiceCommands(commands.Cog):
    def __init__(self, bot: commands.Bot): # Added type hint for bot
        self.bot = bot
        self.queues = {} # {guild_id: collections.deque()}
        self.current_track = {} # {guild_id: link}
        self.predownload_tasks = {} # {guild_id: asyncio.Task}
        self.predownloaded_link = {} # {guild_id: link}
        self.predownloaded_path = {} # {guild_id: path}
        # Create cache directory if it doesn't exist
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR)

    def get_queue(self, guild_id: int) -> collections.deque:
        """Gets the queue for a guild, creating it if it doesn't exist."""
        return self.queues.setdefault(guild_id, collections.deque())

    def _get_next_track_path(self, guild_id: int) -> str:
        """Returns the expected path for the pre-downloaded next track."""
        return os.path.join(CACHE_DIR, f"{guild_id}_next_track.opus")

    async def _cancel_predownload(self, guild_id: int):
        """Cancels the pre-download task and cleans up state/files."""
        task = self.predownload_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()
            log.info(f"Cancelled pre-download task for guild {guild_id}")
            # Allow task to finish cancellation
            try:
                await task
            except asyncio.CancelledError:
                log.info(f"Pre-download task cancellation confirmed for guild {guild_id}")
            except Exception as e:
                log.error(f"Error during pre-download task cancellation for guild {guild_id}: {e}")


        # Clear state
        self.predownloaded_link.pop(guild_id, None)
        predownloaded_file = self.predownloaded_path.pop(guild_id, None)

        # Delete the temporary next track file if it exists
        next_track_file = self._get_next_track_path(guild_id)
        if os.path.exists(next_track_file):
            try:
                os.remove(next_track_file)
                log.info(f"Removed pre-downloaded file for guild {guild_id}: {next_track_file}")
            except OSError as e:
                log.error(f"Error removing pre-downloaded file {next_track_file}: {e}")
        elif predownloaded_file and os.path.exists(predownloaded_file): # Check the stored path too
             try:
                 os.remove(predownloaded_file)
                 log.info(f"Removed pre-downloaded file (from state) for guild {guild_id}: {predownloaded_file}")
             except OSError as e:
                 log.error(f"Error removing pre-downloaded file {predownloaded_file}: {e}")


    async def _play_song(self, guild_id: int, link: str, interaction_channel: Optional[discord.TextChannel] = None, previous_track_path: Optional[str] = None):
        """Downloads (or uses pre-downloaded) and plays a single song. Deletes previous track's file."""

        # --- Delete Previous Track File ---
        if previous_track_path and os.path.exists(previous_track_path):
            try:
                os.remove(previous_track_path)
                log.info(f"Deleted previous track file for guild {guild_id}: {previous_track_path}")
            except OSError as e:
                log.error(f"Error deleting previous track file {previous_track_path} for guild {guild_id}: {e}")
        elif previous_track_path:
            log.warning(f"Tried to delete previous track file for guild {guild_id}, but it didn't exist: {previous_track_path}")

        # --- Existing Logic ---
        # Cancel any existing pre-download for *this* guild before starting playback/new download
        await self._cancel_predownload(guild_id)

        guild = self.bot.get_guild(guild_id)
        if not guild:
            log.error(f"_play_song: Guild {guild_id} not found.")
            return False
        voice_client = guild.voice_client
        if not voice_client or not voice_client.is_connected():
            log.error(f"_play_song: Not connected to voice in guild {guild_id}.")
            # Attempt to notify if we have a channel
            if interaction_channel:
                try: await interaction_channel.send("I'm not connected to a voice channel anymore.")
                except discord.HTTPException: pass
            return False

        downloaded_file = None
        used_predownload = False

        # --- Check for Pre-downloaded File ---
        predownload_link = self.predownloaded_link.get(guild_id)
        predownload_path = self.predownloaded_path.get(guild_id)

        if predownload_link == link and predownload_path and os.path.exists(predownload_path):
            log.info(f"Using pre-downloaded file for guild {guild_id}: {predownload_path}")
            downloaded_file = predownload_path
            used_predownload = True
            # Clear pre-download state as it's now being used
            self.predownloaded_link.pop(guild_id, None)
            self.predownloaded_path.pop(guild_id, None)
        else:
            # --- Normal Download Logic ---
            log.info(f"Pre-downloaded file not available or doesn't match for guild {guild_id}. Downloading normally.")
            # Using a consistent name per guild for simplicity since cleanup is disabled
            # Spotdl seems to create a directory even with simple output, let's stick to that pattern
            output_template = os.path.join(CACHE_DIR, f"{guild_id}_current_track.%(ext)s")
            potential_output_dir = os.path.join(CACHE_DIR, f"{guild_id}_current_track.%(ext)s")

            command = f'spotdl "{link}" --output "{output_template}" --format opus --log-level ERROR'
            log.info(f"Running spotdl command for guild {guild_id}: {command}")

            try:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    error_message = stderr.decode().strip() or stdout.decode().strip()
                    log.error(f"spotdl failed for guild {guild_id}: {error_message}")
                    user_error = error_message.splitlines()[-1] if error_message else "Unknown download error."
                    if interaction_channel:
                        try: await interaction_channel.send(f"Failed to download song: {user_error}")
                        except discord.HTTPException: pass
                    return False # Download failed

                # --- Find the downloaded file ---
                if os.path.isdir(potential_output_dir):
                    try:
                        files_in_dir = [f for f in os.listdir(potential_output_dir) if os.path.isfile(os.path.join(potential_output_dir, f))]
                        for file in files_in_dir:
                            if file.lower().endswith('.opus'):
                                downloaded_file = os.path.join(potential_output_dir, file)
                                break
                        if not downloaded_file: # Fallback
                             for file in files_in_dir:
                                 if file.lower().endswith(('.mp3', '.m4a', '.flac', '.ogg')):
                                     downloaded_file = os.path.join(potential_output_dir, file)
                                     log.warning(f"Found non-opus file ({file}) in cache dir for guild {guild_id} despite requesting opus.")
                                     break
                    except OSError as e:
                        log.error(f"Error listing files in cache directory {potential_output_dir}: {e}")

                # Fallback checks (old style)
                if not downloaded_file:
                    potential_file_opus = os.path.join(CACHE_DIR, f"{guild_id}_current_track.opus")
                    potential_file_mp3 = os.path.join(CACHE_DIR, f"{guild_id}_current_track.mp3")
                    if os.path.exists(potential_file_opus): downloaded_file = potential_file_opus
                    elif os.path.exists(potential_file_mp3): downloaded_file = potential_file_mp3

            except Exception as e: # Catch errors during download process
                 log.exception(f"An unexpected error occurred during download for guild {guild_id}:")
                 if interaction_channel:
                     try: await interaction_channel.send(f"An unexpected error occurred during download: {e}")
                     except discord.HTTPException: pass
                 return False # Download failed

        # --- Playback ---
        if not downloaded_file:
            log.error(f"Download process finished for guild {guild_id} but failed to locate the final audio file.")
            if interaction_channel:
                try: await interaction_channel.send("Download finished, but couldn't find the audio file.")
                except discord.HTTPException: pass
            return False

        log.info(f"Attempting to play for guild {guild_id}: {downloaded_file}")
        if interaction_channel and not used_predownload: # Announce only if it wasn't pre-downloaded (already announced)
             try: await interaction_channel.send(f"Now playing: `{link}`")
             except discord.HTTPException: pass
        elif interaction_channel and used_predownload: # Announce we're using the pre-download
             try: await interaction_channel.send(f"Now playing (pre-downloaded): `{link}`")
             except discord.HTTPException: pass


        try: # Start playback block
            audio_source = discord.FFmpegPCMAudio(downloaded_file)
            # Store the link of the track being played
            self.current_track[guild_id] = link
            # Use lambda to pass guild_id and the path of the *current* file to the after callback handler
            current_file_path = downloaded_file
            voice_client.play(audio_source, after=lambda e: self.bot.loop.create_task(self._after_playing(guild_id, current_file_path, e))) # Pass path of song *just played*
            log.info(f"Started playing {current_file_path} in guild {guild_id}")

            # --- Trigger Pre-download for the NEXT song ---
            self.bot.loop.create_task(self._trigger_predownload(guild_id))

            return True # Playback started successfully

        except Exception as e: # Catch errors during playback start
            log.exception(f"An unexpected error occurred starting playback for guild {guild_id}:")
            if interaction_channel:
                try: await interaction_channel.send(f"An unexpected error occurred while trying to play: {e}")
                except discord.HTTPException: pass
            # Clear current track info if playback failed to start
            self.current_track.pop(guild_id, None)
            return False # Playback failed


    async def _trigger_predownload(self, guild_id: int):
        """Checks the queue and starts pre-downloading the next song if appropriate."""
        await asyncio.sleep(1) # Small delay to allow current playback to stabilize

        if guild_id in self.predownload_tasks:
            log.debug(f"Pre-download task already running for guild {guild_id}.")
            return

        queue = self.get_queue(guild_id)
        if not queue:
            log.debug(f"Queue empty for guild {guild_id}, not pre-downloading.")
            return

        next_link = queue[0] # Peek at the next item without removing it
        log.info(f"Triggering pre-download for next song in queue for guild {guild_id}: {next_link}")

        task = self.bot.loop.create_task(self._predownload_next(guild_id, next_link))
        self.predownload_tasks[guild_id] = task

        # Add callback to remove task from dict when done (handles success, failure, cancellation)
        task.add_done_callback(lambda t: self.predownload_tasks.pop(guild_id, None))


    async def _predownload_next(self, guild_id: int, link: str):
        """Downloads the next song in the queue to a temporary location."""
        log.info(f"Starting pre-download task for guild {guild_id}: {link}")
        output_path = self._get_next_track_path(guild_id)
        # Use a simple output filename template for pre-download
        output_template = os.path.join(CACHE_DIR, f"{guild_id}_next_track")

        # Clean up any existing temp file first
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
                log.debug(f"Removed existing temp file before pre-download: {output_path}")
            except OSError as e:
                log.error(f"Error removing existing temp file {output_path}: {e}")
                # Don't necessarily stop, maybe spotdl can overwrite

        command = f'spotdl "{link}" --output "{output_template}" --format opus --log-level ERROR'
        process = None
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # Check if the expected file exists
                if os.path.exists(output_path):
                    self.predownloaded_link[guild_id] = link
                    self.predownloaded_path[guild_id] = output_path
                    log.info(f"Successfully pre-downloaded for guild {guild_id}: {output_path}")
                else:
                    log.error(f"Pre-download spotdl finished for guild {guild_id} but output file not found: {output_path}")
                    # Clean up potentially incorrect state
                    self.predownloaded_link.pop(guild_id, None)
                    self.predownloaded_path.pop(guild_id, None)
            else:
                error_message = stderr.decode().strip() or stdout.decode().strip()
                log.error(f"Pre-download spotdl failed for guild {guild_id}: {error_message}")
                # Clean up state
                self.predownloaded_link.pop(guild_id, None)
                self.predownloaded_path.pop(guild_id, None)

        except asyncio.CancelledError:
             log.info(f"Pre-download task cancelled for guild {guild_id}.")
             # Ensure temp file is deleted on cancellation
             if os.path.exists(output_path):
                 try: os.remove(output_path)
                 except OSError: pass
             raise # Re-raise cancellation

        except Exception as e:
            log.exception(f"Error during pre-download task for guild {guild_id}:")
            # Clean up state on unexpected error
            self.predownloaded_link.pop(guild_id, None)
            self.predownloaded_path.pop(guild_id, None)
            if os.path.exists(output_path):
                 try: os.remove(output_path)
                 except OSError: pass
        finally:
             # Ensure task is removed from dict if it finishes normally or with exception
             # (Done callback handles this now)
             pass


    async def _after_playing(self, guild_id: int, finished_track_path: Optional[str], error: Optional[Exception]):
        """Callback run after a song finishes playing. Plays the next song if available."""
        # --- REMOVED Deletion Logic from here ---

        # --- Original Logic ---
        # Clear current track info *before* starting next song
        current_finished_link = self.current_track.pop(guild_id, None) # Keep link tracking for queue display etc.
        log.info(f"Cleared current track info for guild {guild_id} (was: {current_finished_link})")

        if error:
            log.error(f'Error during playback for guild {guild_id}: {error}')
            # Optionally, notify a channel if possible

        log.info(f'Finished playing song in guild {guild_id}. Checking queue.')
        queue = self.get_queue(guild_id)

        if queue:
            next_link = queue.popleft()
            log.info(f"Playing next song from queue for guild {guild_id}: {next_link}")
            # Try to find a text channel to announce in (this is tricky without context)
            # A simple approach: find the first text channel the bot can see in the guild
            guild = self.bot.get_guild(guild_id)
            announce_channel = None
            if guild:
                for channel in guild.text_channels:
                     if channel.permissions_for(guild.me).send_messages:
                         announce_channel = channel
                         break
            # Pass the finished_track_path to the next _play_song call
            await self._play_song(guild_id, next_link, interaction_channel=announce_channel, previous_track_path=finished_track_path)
        else:
            log.info(f"Queue empty for guild {guild_id}. Playback stopped.")
            # --- Delete the VERY LAST track file when queue is empty ---
            if finished_track_path and os.path.exists(finished_track_path):
                try:
                    os.remove(finished_track_path)
                    log.info(f"Deleted final track file for guild {guild_id}: {finished_track_path}")
                except OSError as e:
                    log.error(f"Error deleting final track file {finished_track_path} for guild {guild_id}: {e}")
            elif finished_track_path:
                 log.warning(f"Tried to delete final track file for guild {guild_id}, but it didn't exist: {finished_track_path}")

            await self._cancel_predownload(guild_id) # Cancel pre-download when stopping
            # Optionally, implement auto-disconnect after inactivity here


    # Updated helper to only accept Context
    async def _ensure_voice(self, ctx: commands.Context, connect_if_needed: bool = True) -> Optional[discord.VoiceClient]:
        """Ensures the bot is connected to the user's voice channel. Uses Context."""
        is_interaction = ctx.interaction is not None
        user = ctx.author # Always available in Context
        guild = ctx.guild

        if not user.voice or not user.voice.channel:
            # ctx.send handles both interaction response/followup and message reply
            await ctx.send("You need to be in a voice channel to use this command.", ephemeral=is_interaction)
            return None

        channel = user.voice.channel
        voice_client = guild.voice_client

        if voice_client is None:
            log.info(f"Connecting to voice channel: {channel.name} in guild {guild.id}")
            try:
                voice_client = await channel.connect()
            except Exception as e:
                log.error(f"Failed to connect to voice channel {channel.name} in guild {guild.id}: {e}")
                await ctx.send("Failed to connect to your voice channel.", ephemeral=is_interaction)
                return None
        elif voice_client.channel != channel:
            log.info(f"Moving to voice channel: {channel.name} in guild {guild.id}")
            try:
                await voice_client.move_to(channel)
            except Exception as e:
                log.error(f"Failed to move to voice channel {channel.name} in guild {guild.id}: {e}")
                await ctx.send("Failed to move to your voice channel.", ephemeral=is_interaction)
            return None # Return None on failure

        # Connect if needed and requested
        if voice_client is None and connect_if_needed:
            log.info(f"Connecting to voice channel: {channel.name} in guild {guild.id}")
            try:
                voice_client = await channel.connect()
            except Exception as e:
                log.error(f"Failed to connect to voice channel {channel.name} in guild {guild.id}: {e}")
                await ctx.send("Failed to connect to your voice channel.", ephemeral=is_interaction)
                return None
        elif voice_client and voice_client.channel != channel: # Already connected, but wrong channel
             log.info(f"Moving to voice channel: {channel.name} in guild {guild.id}")
             try:
                 await voice_client.move_to(channel)
             except Exception as e:
                 log.error(f"Failed to move to voice channel {channel.name} in guild {guild.id}: {e}")
                 await ctx.send("Failed to move to your voice channel.", ephemeral=is_interaction)
                 return None # Return None on failure

        return voice_client # Return the connected/moved client or None if connection failed/not requested

    # Refactored using commands.hybrid_command
    @commands.hybrid_command(name='join', description='Makes the bot join your current voice channel.', aliases=['j'])
    async def join(self, ctx: commands.Context):
        """Joins the voice channel of the user who issued the command."""
        # Hybrid commands pass Context (ctx). Check ctx.interaction for slash command specifics.
        is_interaction = ctx.interaction is not None

        # Defer/Acknowledge if it's an interaction
        if is_interaction:
            await ctx.defer(ephemeral=True)

        # Pass context to helper
        voice_client = await self._ensure_voice(ctx)

        # Send confirmation only if successful
        if voice_client:
             # Use ctx.send() which handles both interaction followup and regular message reply
             await ctx.send(f'Joined {voice_client.channel.name}', ephemeral=is_interaction)
        # _ensure_voice handles the error message if connection failed

    # Refactored using commands.hybrid_command
    @commands.hybrid_command(name='play', description='Adds a song/playlist/album to the queue.', aliases=['p'])
    @app_commands.describe(link='The Spotify track/album/playlist link') # Keep describe for slash command help
    async def play(self, ctx: commands.Context, *, link: str):
        """Adds a song from a Spotify link to the queue and starts playing if idle."""
        is_interaction = ctx.interaction is not None
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)

        # Defer/Acknowledge
        if is_interaction:
            # Defer non-ephemeral for play command initial response
            await ctx.defer(ephemeral=False) # Defer publicly
        else:
            # Add reaction for prefix command feedback
            try:
                 await ctx.message.add_reaction("⏳") # Indicate processing
            except (discord.Forbidden, discord.NotFound):
                 log.warning(f"Could not add reaction in guild {ctx.guild.id}")

        # Ensure voice connection
        voice_client = await self._ensure_voice(ctx, connect_if_needed=True)
        if not voice_client:
            if not is_interaction: # Clean up reaction on failure
                 try: await ctx.message.remove_reaction("⏳", self.bot.user)
                 except (discord.Forbidden, discord.NotFound): pass
            # _ensure_voice already sent the error message
            return

        # Add to queue
        queue.append(link)
        log.info(f"Added to queue for guild {guild_id}: {link}")
        await ctx.send(f"Added to queue: `{link}`") # Use ctx.send for hybrid compatibility

        # If not already playing, start playback
        if not voice_client.is_playing() and not voice_client.is_paused():
            log.info(f"Nothing playing in guild {guild_id}, starting playback immediately.")
            # Pop the link we just added (or the first one if others were added concurrently)
            next_link = queue.popleft()
            # Start playing - pass ctx.channel for announcements, no previous track path for initial play
            await self._play_song(guild_id, next_link, interaction_channel=ctx.channel, previous_track_path=None)
        else:
             log.info(f"Already playing/paused in guild {guild_id}, song remains queued.")

        # Clean up initial reaction if prefix command
        if not is_interaction:
            try: await ctx.message.remove_reaction("⏳", self.bot.user)
            except (discord.Forbidden, discord.NotFound): pass


    @commands.hybrid_command(name='queue', description='Shows the current song queue.', aliases=['q'])
    async def queue(self, ctx: commands.Context):
        """Displays the current song queue."""
        is_interaction = ctx.interaction is not None
        if is_interaction: await ctx.defer(ephemeral=True)

        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        now_playing = self.current_track.get(guild_id)

        if not queue and not now_playing:
            await ctx.send("The queue is currently empty and nothing is playing.", ephemeral=True)
            return

        embed = discord.Embed(title="Song Queue", color=discord.Color.blue())
        description_lines = []

        # Display Now Playing
        if now_playing:
            description_lines.append(f"**Now Playing:**\n`{now_playing}`\n")

        # Display Next Up
        if queue:
            description_lines.append("**Next Up:**")
            queue_list = list(queue)
            for i, link in enumerate(queue_list[:15]): # Limit display length
                description_lines.append(f"{i+1}. `{link}`")

            embed.description = "\n".join(description_lines)
            if len(queue) > 15:
                embed.set_footer(text=f"... and {len(queue) - 15} more queued.")
        elif now_playing: # Only playing, no queue
             embed.description = "\n".join(description_lines)
             embed.set_footer(text="The queue is empty.")
        else: # Should be caught by the initial check, but safety
             embed.description = "The queue is empty."


        await ctx.send(embed=embed, ephemeral=True) # Send queue privately


    @commands.hybrid_command(name='skip', description='Skips the current song and plays the next.', aliases=['s'])
    async def skip(self, ctx: commands.Context):
        """Skips the current song."""
        is_interaction = ctx.interaction is not None
        if is_interaction: await ctx.defer()

        voice_client = await self._ensure_voice(ctx, connect_if_needed=False) # Don't connect if not in VC

        if not voice_client:
             await ctx.send("I'm not connected to a voice channel.", ephemeral=True)
             return
        if not voice_client.is_playing() and not voice_client.is_paused():
             await ctx.send("I'm not playing anything right now.", ephemeral=True)
             return

        log.info(f"Skipping current song in guild {ctx.guild.id} by request of {ctx.author.name}")
        # Cancel pre-download before stopping, as stop() triggers _after_playing
        await self._cancel_predownload(ctx.guild.id)
        voice_client.stop() # Triggers the _after_playing callback which handles the next song
        await ctx.send("Skipped!", ephemeral=True)


    @commands.hybrid_command(name='stop', description='Stops playback and clears the queue.')
    async def stop(self, ctx: commands.Context):
        """Stops playback and clears the queue."""
        is_interaction = ctx.interaction is not None
        if is_interaction: await ctx.defer()

        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        voice_client = await self._ensure_voice(ctx, connect_if_needed=False)

        if not voice_client:
             await ctx.send("I'm not connected to a voice channel.", ephemeral=True)
             return

        # Clear queue
        queue.clear()
        log.info(f"Queue cleared for guild {guild_id} by request of {ctx.author.name}")

        # Cancel pre-download first
        await self._cancel_predownload(guild_id)

        # Clear queue
        queue.clear()
        log.info(f"Queue cleared for guild {guild_id} by request of {ctx.author.name}")

        # Stop playback (also triggers _after_playing which should clear current_track)
        if voice_client.is_playing() or voice_client.is_paused():
            log.info(f"Stopping playback in guild {guild_id} by request of {ctx.author.name}")
            # Explicitly clear current track here too for immediate effect
            self.current_track.pop(guild_id, None)
            voice_client.stop()
            await ctx.send("Playback stopped and queue cleared.")
        else:
            # Ensure current track is cleared even if nothing was playing
            self.current_track.pop(guild_id, None)
            await ctx.send("Queue cleared (nothing was playing).")


    # --- OLD PLAY METHOD CONTENT (Removed/Integrated into _play_song) ---
    # @commands.hybrid_command(name='play_old', description='Downloads and plays a song from a Spotify link.', aliases=['p_old'])
    # @app_commands.describe(link='The Spotify track/album/playlist link') # Keep describe for slash command help
    # async def play_old(self, ctx: commands.Context, *, link: str):
    #     """Downloads a song using spotdl and plays it."""
    #     is_interaction = ctx.interaction is not None
    #     ephemeral_flag = is_interaction # Use ephemeral only for interactions where appropriate
    #
    #     # Defer/Acknowledge
    #     if is_interaction:
    #         # Defer non-ephemeral for play command initial response
    #         await ctx.defer(ephemeral=False)
    #     else:
    #         # Add reaction for prefix command feedback
    #         try:
    #              await ctx.message.add_reaction("🎵")
    #         except (discord.Forbidden, discord.NotFound):
    #              log.warning(f"Could not add reaction in guild {ctx.guild.id}")
    #
    #     # Pass context to helper
    #     voice_client = await self._ensure_voice(ctx)
    #     if not voice_client:
    #         if not is_interaction: # Clean up reaction on failure for prefix commands
    #              try: await ctx.message.remove_reaction("🎵", self.bot.user)
    #              except (discord.Forbidden, discord.NotFound): pass
    #         return # _ensure_voice sent the error message
    #
    #     if voice_client.is_playing() or voice_client.is_paused():
    #         log.info(f"Stopping current playback in guild {ctx.guild.id} for new request.")
    #         voice_client.stop()
    #         await asyncio.sleep(0.5)
    #
    #     # --- Download Logic ---
    #     output_template = os.path.join(CACHE_DIR, f"{ctx.guild.id}_current_track.%(ext)s")
    #     # # Clear previous track for this guild (COMMENTED OUT)
    #     ... (rest of the old download/play logic) ...

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCommands(bot))
