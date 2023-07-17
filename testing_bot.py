import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import json
import ujson
from collections import OrderedDict
from fuzzywuzzy import fuzz

# Replace these with your actual tokens
TOKEN = 'DISCORD TOKEN'
TWITCH_CLIENT_ID = 'TWITCH CLIENT ID'
TWITCH_OAUTH_TOKEN = 'TWITCH OAUTH TOKEN'

TWITCH_BASE_URL = 'https://api.twitch.tv/helix'
TWITCH_USERS_URL = f'{TWITCH_BASE_URL}/users'
TWITCH_FOLLOWS_URL = f'{TWITCH_BASE_URL}/users/follows'

COORDS_FILE = 'coordinates.json'
SHOP_FILE = 'shop_data.json'

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Function to read data from the JSON file
def read_coordinates_data():
    """
    Reads location coordinates data from the JSON file.

    Returns:
        dict: The location coordinates data as a dictionary.
    """
    try:
        with open(COORDS_FILE, 'r') as file:
            return ujson.load(file)
    except FileNotFoundError:
        return {}

# Function to write data to the JSON file
def write_coordinates_data(data):
    """
    Writes location coordinates data to the JSON file.

    Args:
        data (dict): The location coordinates data to be written.
    """
    try:
        with open(COORDS_FILE, 'w') as file:
            ujson.dump(data, file, indent=4)
    except Exception as e:
        print(f"Error while writing to the JSON file: {e}")

# Function to validate and convert coordinates to integers
def validate_coordinate(coord_str):
    """
    Validates and converts a coordinate string to an integer.

    Args:
        coord_str (str): The coordinate string to validate.

    Returns:
        int or None: The integer value of the coordinate, or None if invalid.
    """
    try:
        return int(coord_str)
    except ValueError:
        return None

# Function to validate and get the dimension (nether or overworld)
def validate_dimension(dimension_str):
    """
    Validates and gets the dimension (nether or overworld).

    Args:
        dimension_str (str): The dimension string to validate.

    Returns:
        str or None: The validated dimension (nether or overworld), or None if invalid.
    """
    if dimension_str.lower() in ['nether', 'overworld']:
        return dimension_str.lower()
    return None

@bot.event
async def on_ready():
    """
    Event handler for when the bot is ready and online.
    """
    print(f'Bot is online! Logged in as {bot.user.name} ({bot.user.id})')
    await bot.change_presence(activity=discord.Game(name='Noodle is cool'))
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

@bot.tree.command(name="followers")
async def get_twitch_followers(interaction: discord.Interaction):
    """
    Get the number of followers for the Twitch channel 'DaNooodleMan'.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
    """
    try:
        headers = {
            'Client-ID': TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {TWITCH_OAUTH_TOKEN}'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{TWITCH_USERS_URL}?login=danooodleman', headers=headers) as response:
                data = await response.json()
                channel_id = data.get('data', [])[0].get('id')

            if not channel_id:
                await interaction.response.send_message('Twitch channel DaNooodleMan not found.', ephemeral=True)
                return

            async with session.get(f'{TWITCH_FOLLOWS_URL}?to_id={channel_id}', headers=headers) as response:
                data = await response.json()
                num_followers = data.get('total', 0)

        await interaction.response.send_message(f'Noodle has {num_followers} followers!', ephemeral=True)

    except Exception as e:
        error_message = 'An error occurred while fetching data from the Twitch API.'
        print(f'{error_message}\nError Details: {e}')
        await interaction.response.send_message(error_message, ephemeral=True)

@bot.tree.command(name="duration")
@app_commands.describe(username="Enter the username of a Twitch channel")
async def get_follow_duration(interaction: discord.Interaction, username: str):
    """
    Returns how long <username> has been following DaNooodleMan on Twitch.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
        username (str): The Twitch username to check the follow duration for.
    """
    try:
        headers = {
            'Client-ID': TWITCH_CLIENT_ID,
            'Authorization': f'Bearer {TWITCH_OAUTH_TOKEN}'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{TWITCH_USERS_URL}?login={username}', headers=headers) as response:
                data = await response.json()
                user_id = data.get('data', [])[0].get('id')

            if not user_id:
                await interaction.response.send_message(f'User {username} not found on Twitch or not following DaNooodleMan.', ephemereal=True)
                return

            async with session.get(f'{TWITCH_USERS_URL}?login=danooodleman', headers=headers) as response:
                data = await response.json()
                channel_id = data.get('data', [])[0].get('id')

            if not channel_id:
                await interaction.response.send_message('Twitch channel DaNooodleMan not found.', ephemeral=True)
                return

            async with session.get(f'{TWITCH_FOLLOWS_URL}?from_id={user_id}&to_id={channel_id}', headers=headers) as response:
                data = await response.json()
                follow_duration = None

                if data.get('total', 0) > 0:
                    followed_at_str = data.get('data', [])[0].get('followed_at', '')
                    followed_at = datetime.strptime(followed_at_str, '%Y-%m-%dT%H:%M:%SZ')
                    current_time = datetime.utcnow()
                    follow_duration = current_time - followed_at

            if follow_duration:
                days = follow_duration.days
                hours, remainder = divmod(follow_duration.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                follow_date = followed_at.strftime('%d %B %Y')
                await interaction.response.send_message(f'{username} has been following Noodle for {days} days, {hours} hours, and {minutes} minutes, since {follow_date}.', ephemeral=True)
            else:
                await interaction.response.send_message(f'{username} is not following DaNooodleMan', ephemeral=True)

    except Exception as e:
        error_message = 'An error occurred while fetching data from the Twitch API. This Twitch account may not exist.'
        print(f'{error_message}\nError Details: {e}')
        await interaction.response.send_message(error_message, ephemeral=True)

@bot.tree.command(name="locations")
@app_commands.describe(dimension="all | nether | overworld")
async def list_locations(interaction: discord.Interaction, dimension: str):
    """
    Returns a list of location names in the given dimension.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
        dimension (str): The dimension to list locations for (all, nether, or overworld).
    """
    data = read_coordinates_data()

    if dimension.lower() == 'all':
        # Combine and sort locations from 'nether' and 'overworld'
        nether_locations = data.get('nether', {}).keys()
        overworld_locations = data.get('overworld', {}).keys()
        all_locations = sorted(list(nether_locations) + list(overworld_locations), key=str.lower)
        locations = '\n\t'.join([place.capitalize() for place in all_locations])
        await interaction.response.send_message(f'All locations : \n\t{locations}', ephemeral=True)

    elif dimension.lower() == 'nether':
        locations = data.get('nether', {}).keys()
        locations = sorted(locations, key=str.lower)
        locations = '\n\t'.join([place.capitalize() for place in locations])
        await interaction.response.send_message(f'Locations in Nether: \n\t{locations}', ephemeral=True)

    elif dimension.lower() == 'overworld':
        locations = data.get('overworld', {}).keys()
        locations = sorted(locations, key=str.lower)
        locations = '\n\t'.join([place.capitalize() for place in locations])
        await interaction.response.send_message(f'Locations in Overworld: \n\t{locations}', ephemeral=True)
    else:
        await interaction.response.send_message('Invalid dimension. Use Nether, Overworld or All.', ephemeral=True)

@bot.tree.command(name="coordinates")
@app_commands.describe(location="Enter a location name")
async def coordinates(interaction: discord.Interaction, location: str):
    """
    Get the coordinates and dimension of a named location.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
        location (str): The name of the location to get coordinates for.
    """
    data = read_coordinates_data()
    location_lower = location.lower()

    # Combine and sort locations from 'nether' and 'overworld'
    nether_locations = data.get('nether', {})
    overworld_locations = data.get('overworld', {})
    all_locations = {**nether_locations, **overworld_locations}

    if location_lower in all_locations.keys():
        coords = all_locations[location_lower]
        dimension = 'Nether' if location_lower in nether_locations.keys() else 'Overworld'
        await interaction.response.send_message(f'{location.capitalize()} coordinates: {coords} (Dimension: {dimension})', ephemeral=True)
    else:
        await interaction.response.send_message(f'Location {location.capitalize()} not found.', ephemeral=True)

@bot.tree.command(name="undiscover")
@app_commands.describe(location="Enter a location name")
async def undiscover(interaction: discord.Interaction, location: str):
    """
    Deletes a location from the database.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
        location (str): The name of the location to be deleted.
    """
    data = read_coordinates_data()
    location_lower = location.lower()
    for dimension, locations in data.items():
        if location_lower in locations:
            del locations[location_lower]
            write_coordinates_data(data)
            await interaction.response.send_message(f'Location {location.capitalize()} deleted from {dimension.capitalize()}.')
            return

    await interaction.response.send_message(f'Location {location.capitalize()} not found.', ephemeral=True)

@bot.tree.command(name="discover")
@app_commands.describe(location="Location name", dimension="nether | overworld", x="x-coordinate", y="y-coordinate", z="z-coordinate")
async def discover(interaction: discord.Interaction, location: str, dimension: str, x: str, y: str, z: str):
    """
    Adds a location and its corresponding coordinates into the database.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
        location (str): The name of the location to be added.
        dimension (str): The dimension of the location (nether or overworld).
        x (str): The x-coordinate of the location.
        y (str): The y-coordinate of the location.
        z (str): The z-coordinate of the location.
    """
    location_lower = location.lower()
    dimension = validate_dimension(dimension)
    x_coord = validate_coordinate(x)
    y_coord = validate_coordinate(y)
    z_coord = validate_coordinate(z)

    if not dimension:
        await interaction.response.send_message('Invalid dimension. Use Nether or Overworld.', ephemeral=True)
        return

    if None in [x_coord, y_coord, z_coord]:
        await interaction.response.send_message('Invalid coordinates. Please enter valid integer values.', ephemeral=True)
        return

    if dimension == 'overworld' and (y_coord < -64 or y_coord > 319):
        await interaction.response.send_message('Invalid Y-coordinate for Overworld. Y value should be between -64 and 319.', ephemeral=True)
        return

    if dimension == 'nether' and (y_coord < 0 or y_coord > 255):
        await interaction.response.send_message('Invalid Y-coordinate for Nether. Y value should be between 0 and 255.', ephemeral=True)
        return

    if x_coord < -100000 or x_coord > 100000 or z_coord < -100000 or z_coord > 100000:
        await interaction.response.send_message('Invalid X or Z-coordinate. Coordinates should be between -100,000 and 100,000.', ephemeral=True)
        return

    data = read_coordinates_data()

    if location_lower in data["nether"] or location_lower in data["overworld"]:
        await interaction.response.send_message(f'Location with the same name already exists.', ephemeral=True)
    else:
        # Determine the dimension dictionary
        dimension_data = data[dimension]

        # Update the data with the new location
        dimension_data[location_lower] = [x_coord, y_coord, z_coord]

        # Sort the locations alphabetically
        sorted_locations = sorted(dimension_data.items(), key=lambda item: item[0].lower())

        # Create a new ordered dictionary to preserve insertion order
        ordered_dimension_data = OrderedDict(sorted_locations)

        # Update the original dictionary with the ordered dictionary
        data[dimension] = ordered_dimension_data

        # Write the updated data to the JSON file
        write_coordinates_data(data)

        await interaction.response.send_message(f'Location {location.capitalize()} added to {dimension.capitalize()} with coordinates {x_coord}, {y_coord}, {z_coord}.')

# Helper functions
def read_shop_data():
    try:
        with open("shop_data.json", "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    return data

def write_shop_data(data):
    with open("shop_data.json", "w") as file:
        json.dump(data, file)

def validate_quantity(quantity_str):
    try:
        quantity = int(quantity_str)
        if 1 <= quantity <= 64:
            return quantity
    except ValueError:
        pass
    return None

def validate_price(price_str):
    try:
        price = int(price_str)
        if price >= 0:
            return price
    except ValueError:
        pass
    return None

@bot.tree.command(name="sell")
@app_commands.describe(item="Item to sell", quantity="Quantity to sell (maximum 64)", price="Price per item")
async def sell(interaction: discord.Interaction, item: str, quantity: int, price: int):
    """
    Add an item to the player's shop.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
        item (str): The item to sell.
        quantity (int): The quantity of the item to sell (maximum 64).
        price (int): The price per item.
    """
    if quantity <= 0 or quantity > 64:
        await interaction.response.send_message("Invalid quantity. Quantity should be between 1 and 64.", ephemeral=True)
        return

    data = read_shop_data()
    user_name = interaction.user.name.lower()

    if user_name not in data:
        data[user_name] = []

    shop_entry = {
        "item": item.lower(),
        "quantity": quantity,
        "price": price
    }

    data[user_name].append(shop_entry)
    write_shop_data(data)

    await interaction.response.send_message(f"Successfully added {quantity}x {item.capitalize()} for ${price} to your shop.", ephemeral=True)

@bot.tree.command(name="delete")
@app_commands.describe(item="Enter the name of the item to delete from your shop.")
async def delete_item(interaction: discord.Interaction, item: str):
    """
    Deletes an item from the shop of the user.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
        item (str): The name of the item to be deleted.
    """
    data = read_shop_data()
    user_name = interaction.user.name.lower()

    if user_name not in data:
        await interaction.response.send_message("You don't have a shop. Use `/sell` to add items to your shop.", ephemeral=True)
        return

    shop_items = data[user_name]

    # Find the item in the user's shop and remove it
    item_found = False
    for i, shop_item in enumerate(shop_items):
        if shop_item["item"] == item.lower():
            del shop_items[i]
            item_found = True
            break

    if item_found:
        # Save the updated data back to the JSON file
        write_shop_data(data)
        await interaction.response.send_message(f"{item.capitalize()} deleted from your shop.", ephemeral=True)
    else:
        await interaction.response.send_message(f"You don't have {item.capitalize()} in your shop.", ephemeral=True)

@bot.tree.command(name="edit")
@app_commands.describe(item="Enter the name of the item to edit in your shop.", field="quantity | price", value="The new value for the field.")
async def edit_item(interaction: discord.Interaction, item: str, field: str, value: str):
    """
    Edits a field (quantity or price) of an item in the shop of the user.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
        item (str): The name of the item to be edited.
        field (str): The field to be edited (quantity or price).
        value (str): The new value for the field.
    """

    if field.lower() not in ['quantity', 'price']:
        await interaction.response.send_message("Invalid field. Please specify either 'quantity' or 'price'.", ephemeral=True)
        return

    data = read_shop_data()
    user_name = interaction.user.name.lower()

    if user_name not in data:
        await interaction.response.send_message("You don't have a shop. Use `/sell` to add items to your shop.", ephemeral=True)
        return

    shop_items = data[user_name]

    # Find the item in the user's shop and edit the specified field
    item_found = False
    for shop_item in shop_items:
        if shop_item["item"] == item.lower():
            if field == "quantity":
                new_quantity = validate_quantity(value)
                if new_quantity is not None:
                    shop_item["quantity"] = new_quantity
                    item_found = True
            elif field == "price":
                new_price = validate_price(value)
                if new_price is not None:
                    shop_item["price"] = new_price
                    item_found = True
            break

    if item_found:
        # Save the updated data back to the JSON file
        write_shop_data(data)
        await interaction.response.send_message(f"{field.capitalize()} of {item.capitalize()} updated to {value}.", ephemeral=True)
    else:
        await interaction.response.send_message(f"You don't have {item.capitalize()} in your shop.", ephemeral=True)

@bot.tree.command(name="viewshops")
@app_commands.describe()
async def view_shops(interaction: discord.Interaction):
    """
    View a list of all Discord members who have shops, along with the number of items for sale in each.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
    """
    data = read_shop_data()

    if not data:
        await interaction.response.send_message("No shops found.", ephemeral=True)
        return

    message = "List of shops :\n\n"

    for user_name, shop_items in data.items():
        shop_owner = user_name
        num_items = len(shop_items)
        message += f"{shop_owner}: {num_items} item{'s' if num_items != 1 else ''} for sale\n"

    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="shop")
@app_commands.describe(member="Discord member (or 'me' to view your own shop)")
async def view_shop(interaction: discord.Interaction, member: str):
    """
    View the shop and items for sale of a specific Discord member.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
        member (str): The Discord member or 'me' to view your own shop.
    """
    data = read_shop_data()

    if member.lower() == "me":
        user_name = interaction.user.name.lower()
    else:
        user_name = member.lower()

    shop_items = data.get(user_name)

    if not shop_items:
        if member.lower() == "me":
            await interaction.response.send_message("You have no items for sale in your shop.", ephemeral=True)
        else:
            await interaction.response.send_message("The specified Discord member has no items for sale in their shop.", ephemeral=True)
        return

    message = f"Shop items for {member} :\n\n"

    for item in shop_items:
        item_name = item["item"]
        quantity = item["quantity"]
        price = item["price"]
        message += f"{quantity}x {item_name} for {price}\n"

    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="search")
@app_commands.describe(item="Item to search for in the shops")
async def search_listings(interaction: discord.Interaction, item: str):
    """
    Search for listings with the specified item in the shops.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
        item (str): The item to search for in the shops.
    """
    data = read_shop_data()
    exact_matches = []
    similiar_matches = []

    for user_name, shop_items in data.items():
        for shop_item in shop_items:
            item_name = shop_item["item"]
            item_price = shop_item["price"]
            item_quantity = shop_item["quantity"]

            if item.lower() == item_name or item.lower() in item_name:
                exact_matches.append((user_name, item_name, item_price, item_quantity))
            else:
                ratio = fuzz.partial_ratio(item.lower(), item_name)
                if ratio >= 70:
                    similiar_matches.append((user_name, item_name, item_price, item_quantity))

    if len(exact_matches) == 0 and len(similiar_matches) == 0:
        await interaction.response.send_message("No listings found for the specified item.", ephemeral=True)
        return

    if len(exact_matches) > 0:
        message = "Listings found:\n\n"
        for match in exact_matches:
            user_name, item_name, item_price, item_quantity = match
            message += f"{item_name.capitalize()}: ${item_price} for {item_quantity} by {user_name}\n"
    else: message = "No exact listings found\n"

    if len(exact_matches) < 5:
        remaining_slots = 5 - len(exact_matches)
        message += "Similar listings :\n\n"
        for match in similiar_matches[:remaining_slots]:
            user_name, item_name, item_price, item_quantity = match
            message += f"{item_name.capitalize()}: ${item_price} for {item_quantity} by {user_name}\n"

    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="noodle-help")
@app_commands.describe()
async def noodle_help(interaction: discord.Interaction):
    """
    Provides information about the usage of NoodleBot commands.

    Args:
        interaction (discord.Interaction): The interaction object for the command.
    """
    help_message = (
        "**NoodleBot Commands**:\n\n"

        # Command Group: Location Database
        "**Location Database** :\n\n"
        "/locations <all | nether | overworld> : List locations in the specified dimension.\n"
        "/coordinates <location> : Get the coordinates and dimension of a named location.\n"
        "/undiscover <location> : Deletes a location from the database.\n"
        "/discover <location> <dimension> <x> <y> <z> : Adds a location and its coordinates to the database.\n\n"

        # Command Group: Twitch Followers
        "**Twitch Followers** :\n\n"
        "/followers : Get the number of followers for the Twitch channel 'DaNooodleMan'.\n"
        "/duration <username> : Returns how long <username> has been following DaNooodleMan on Twitch.\n\n"

        # Command Group: Shop System
        "**Shop System** :\n\n"
        "/sell <item> <quantity> <price> : Sell an item with the specified quantity and price.\n"
        "/delete <item> : Deletes a listed item from your shop.\n"
        "/edit <item> <quantity|price> <value> : Edit the quantity or price of a listed item in your shop.\n"
        "/viewshops : View a list of all Discord members who have shops and the number of items for sale in each.\n"
        "/shop <player | me> : View the shop of an individual Discord member or your own shop.\n"
        "/search <item> : Search for listings matching <item> or similar items in the shop database.\n"
    )

    await interaction.response.send_message(help_message, ephemeral=True)

@bot.tree.command(name="coolest")
@app_commands.describe()
async def coolest(interaction: discord.Interaction):
    """Who is the coolest player?"""
    await interaction.response.send_message('Alex is the coolest')

bot.run(TOKEN)
