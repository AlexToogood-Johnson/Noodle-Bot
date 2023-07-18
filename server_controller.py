import discord
from discord.ext import commands
import asyncio
import subprocess
from datetime import datetime, timedelta

TOKEN = 'ENTER DISCORD TOKEN'
COMMAND_COOLDOWN_SECONDS = 120  # 2 minutes

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Custom role ID that grants permission to control the server
AUTHORIZED_ROLE_ID = 1234567890

last_command_time = None  # Variable to store the timestamp of the last command execution

async def start_minecraft_server():
    try:
        proc = await asyncio.create_subprocess_exec(
            'java', '-Xmx1G', '-Xms1G', '-jar', '/path/to/paper.jar', 'nogui',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except subprocess.SubprocessError as e:
        print(f"Error starting the server: {e}")
        return False

async def stop_minecraft_server():
    try:
        result = await asyncio.subprocess.run(
            ['screen', '-S', 'minecraft_server', '-X', 'stuff', 'list^M'],
            capture_output=True, text=True
        )
        player_list = result.stdout.strip()
        if player_list:
            return False

        await asyncio.subprocess.run(['screen', '-S', 'minecraft_server', '-X', 'stuff', 'stop^M'])
        return True
    except subprocess.SubprocessError as e:
        print(f"Error stopping the server: {e}")
        return False

def can_execute_command(ctx):
    global last_command_time
    if not AUTHORIZED_ROLE_ID in [role.id for role in ctx.author.roles]:
        asyncio.create_task(ctx.send('You do not have permission to start/stop the server.'))
        return False

    if last_command_time and datetime.now() - last_command_time < timedelta(seconds=COMMAND_COOLDOWN_SECONDS):
        cooldown_remaining = (last_command_time + timedelta(seconds=COMMAND_COOLDOWN_SECONDS)) - datetime.now()
        asyncio.create_task(ctx.send(f"Please wait {cooldown_remaining.seconds} seconds before using this command again."))
        return False

    return True

@bot.event
async def on_ready():
    print(f'Bot is online! Logged in as {bot.user.name} ({bot.user.id})')
    await bot.change_presence(activity=discord.Game(name='Server is OFF'))
    try:
        await bot.sync_commands()
        print("Commands synced with Discord")
    except Exception as e:
        print(e)

@bot.slash_command(name="start", description="Starts the Minecraft server.")
async def start_server(ctx):
    if can_execute_command(ctx):
        if not await start_minecraft_server():
            await ctx.send('Error starting the server.')
            return

        global last_command_time
        last_command_time = datetime.now()
        await bot.change_presence(activity=discord.Game(name='Server is ON'))
        await ctx.send('Server started')

@bot.slash_command(name="stop", description="Stops the Minecraft server.")
async def stop_server(ctx):
    if can_execute_command(ctx):
        if not await stop_minecraft_server():
            await ctx.send('Error stopping the server.')
            return

        global last_command_time
        last_command_time = datetime.now()
        await bot.change_presence(activity=discord.Game(name='Server is OFF'))
        await ctx.send('Server stopped')

@bot.slash_command(name="update", description="Updates the spigot-geyser package.")
async def update_package(ctx):
    if can_execute_command(ctx):
        try:
            subprocess.run(['sudo', 'apt-get', 'update', 'spigot-geyser'])
            await ctx.send('spigot-geyser package updated successfully.')
        except Exception as e:
            await ctx.send('Error updating the spigot-geyser package.')
            print(f"Error updating the spigot-geyser package: {e}")

bot.run(TOKEN)
