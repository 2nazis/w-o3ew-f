import discord
from discord.ext import commands, tasks
import asyncio
import requests
import random
import time
import os
from discord import File
import json

intents = discord.Intents.default()
intents.message_content = True

# Create an instance of the bot
bot = commands.Bot(command_prefix='!', intents=intents)

class TokenBucket:
    def __init__(self, capacity, fill_rate):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = self.capacity
        self.last_update = time.time()

    def consume(self, amount):
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        else:
            return False

    def refill(self):
        current_time = time.time()
        time_passed = current_time - self.last_update
        self.tokens = min(self.capacity, self.tokens + time_passed * self.fill_rate)
        self.last_update = current_time

# Initialize a TokenBucket with a capacity of 25 and a fill rate of 20 tokens per minute
token_bucket = TokenBucket(capacity=25, fill_rate=20)

# Dictionary to store user-specific cooldown timestamps
user_cooldowns = {}

@tasks.loop(minutes=1)
async def generate_promos():
    token_bucket.refill()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    print('------')
    generate_promos.start()

# Read configuration from iconfig.json
with open('iconfig.json', 'r') as config_file:
    config = json.load(config_file)

# Retrieve bot token, admin IDs, and allowed channel ID from the config file
bot_token = config['Bot']['token']
admin_ids = config['Admins']['admin_ids']
allowed_channel_id = config['Channel']['allowed_channel_id']

# Check if the user is an admin
def is_admin(ctx):
    return ctx.author.id in admin_ids

# Cooldown for the generate_promos_command, 900 seconds (15 minutes) cooldown for each user
@commands.cooldown(1, 900, commands.BucketType.user)
@bot.command(name='gen')  # Change command name from 'promo' to 'gen'
async def generate_promos_command(ctx, amount: int = 25):
    if ctx.channel.id != allowed_channel_id:
        embed = discord.Embed(
            title="Invalid Channel",
            description="This command can only be used in the designated channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if amount > 25:
        embed = discord.Embed(
            title="Invalid Amount",
            description="You can only generate a maximum of 25 promos at a time.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if token_bucket.consume(amount):
        print(f"Received command: !gen {amount}")

        print(f"Generating {amount} promo codes...")

        # Record the start time
        start_time = time.time()

        # Generate promo codes
        promos = []
        for _ in range(amount):
            promo = generate_promo()
            promos.append(promo)

        # Ensure the directory exists
        os.makedirs('.gg', exist_ok=True)

        # Send promo codes to the user's DM
        file_content = '\n'.join(promos)
        file_path = '.gg/cmos.txt'
        with open(file_path, 'w') as file:
            file.write(file_content)

        embed = discord.Embed(
            title="Promo Code Generation Complete",
            description=f"Generated {amount} promo codes in {time.strftime('%M:%S', time.gmtime(time.time() - start_time))}.",
            color=discord.Color.green()
        )
        await ctx.author.send("Here are your promo codes:", files=[File(file_path)], embed=embed)

        # Send an embedded message
        await ctx.send(embed=embed)

        # Delete the promo codes file
        os.remove(file_path)
        print("Promo codes file deleted.")
    else:
        remaining_time = round(commands.CooldownMapping.from_cooldown(1, 900, commands.BucketType.user).get_bucket(ctx.message).update_rate_limit(time.time()))
        remaining_minutes, remaining_seconds = divmod(remaining_time, 60)

        embed = discord.Embed(
            title="Rate Limit Exceeded",
            description=f"{ctx.author.mention}, you need to wait {remaining_minutes} minutes and {remaining_seconds} seconds before using the command again.",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

        # Get the user's remaining cooldown time
        remaining_cooldown = commands.CooldownMapping.from_cooldown(1, 900, commands.BucketType.user).get_bucket(ctx.message).get_retry_after()
        if ctx.author.id not in user_cooldowns or remaining_cooldown > user_cooldowns[ctx.author.id]:
            user_cooldowns[ctx.author.id] = remaining_cooldown

            # Notify the user in the channel about the remaining cooldown time
            await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        remaining_minutes, remaining_seconds = divmod(error.retry_after, 60)

        embed = discord.Embed(
            title="Cooldown",
            description=f"{ctx.author.mention}, you need to wait {int(remaining_minutes)} minutes and {int(remaining_seconds)} seconds before using the command again.",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

def generate_promo():
    headers = {
        'authority': 'api.discord.gx.games',
        'accept': '*/*',
        'accept-language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
        'content-type': 'application/json',
        'origin': 'https://www.opera.com',
        'referer': 'https://www.opera.com/',
        'sec-ch-ua': '"Opera GX";v="105", "Chromium";v="119", "Not?A_Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0 (Edition std-1)',
    }

    json_data = {
        'partnerUserId': generate_string(),
    }

    response = requests.post('https://api.discord.gx.games/v1/direct-fulfillment', headers=headers, json=json_data)
    if response.status_code == 200:
        promo = response.json()['token']
        promo = f'discord.com/billing/partner-promotions/1180231712274387115/{promo}'
        print(f"Generated promo code: {promo}")
        return promo
    else:
        print("Ratelimited, sleeping for 5 minutes...")
        time.sleep(300)
        return generate_promo()

def generate_string():
    string = ''
    for _ in range(64):
        string += random.choice('0123456789abcdef')
    return string

# Run the bot using asyncio.run
if __name__ == "__main__":
    asyncio.run(bot.start(bot_token))
