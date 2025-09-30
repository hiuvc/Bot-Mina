import os
import discord
from discord.ext import commands, tasks
import aiohttp
from datetime import datetime

# ================= CONFIG =================
TOKEN = os.getenv("DISCORD_TOKEN")  # Token bot lấy từ Environment Variable
API_URL = "https://fruitsstockapi.onrender.com/fruitstock"

# ================= INTENTS =================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= STORAGE =================
stock_messages = {}
last_stock = {}

# ================= FRUIT → EMOJI =================
FRUIT_EMOJI = {
    "Rocket-Rocket": "<:Rocket_fruit:1422206917106733227>",  
    "Spin-Spin": "<:Spin_fruit:1422212836796534804>",
    "Blade-Blade": "<:Blade_fruit:1422212358297882715>",
    "Sand-Sand": "<:Sand_fruit:1422212111685124208>",
    "Ice-Ice": "<:Ice_fruit:1422215625064972401>",
    "Eagle-Eagle": "<:Eagle_fruit:1422211868314960032>",
    "Rubber-Rubber": "<:Rubber_fruit:1422209600433950720>",
    "Spike-Spike": "<:Spike_fruit:1422215734305624124>",
    "Bomb-Bomb": "<:Bomb_fruit:1422214714494025748>",
    "Flame-Flame": "<:Flame_fruit:1422207593073606676>",
    "Spring-Spring": "<:Spring_fruit:1422215879780728993>",
    "Diamond-Diamond": "<:Diamond_fruit:1422210581548630026>",
    "Smoke-Smoke": "<:Smoke_fruit:1422217080777867385>",
    "Dark-Dark": "<:Dark_fruit:1422207695494316083>",
    "Light-Light": "<:Light_fruit:1422208146222354484>",
    "Ghost-Ghost": "<:Ghost_fruit:1422208434110992466>",
    "Magma-Magma": "<:Magma_fruit:1422207498852499596>",
    "Quake-Quake": "<:Quake_fruit:1422209144504717456>",
    "Buddha-Buddha": "<:Buddha_fruit:1422210777385013298>",
    "Love-Love": "<:Love_Fruit:1422207155125354536>",
    "Creation-Creation": "<:Creation_fruit:1422212923954167908>",
    "Spider-Spider": "<:Spider_fruit:1422209019858255943>",
    "Sound-Sound": "<:Sound_fruit:1422212666386157648>",
    "Phoenix-Phoenix": "<:Phoenix_fruit:1422208556995842210>",
    "Lightning-Lightning": "<:Rumble_fruit:1422210336509136906>",
    "Rumble-Rumble": "<:Rumble_fruit:1422210336509136906>",
    "Pain-Pain": "<:Pain_fruit:1422209692473757869>",
    "Blizzard-Blizzard": "<:Blizard_fruit:1422207837517385818>",
    "Gravity-Gravity": "<:Gravity_fruit:1422211766179332186>",
    "Mammoth-Mammoth": "<:Mammoth_fruit:1422210462136799262>",
    "T-Rex-T-Rex": "<:Trex_fruit:1422212443311964212>",
    "Dough-Dough": "<:Douth_fruit:1422208017230856243>",
    "Shadow-Shadow": "<:Shadow_fruit:1422210692026470502>",
    "Venom-Venom": "<:Venom_fruit:1422208847858241596>",
    "Control-Control": "<:Control_fruit:1422209407001038929>",
    "Gas-Gas": "<:Gas_fruit:1422213901621133322>",
    "Spirit-Spirit": "<:Spirit_fruit:1422208664097259640>",
    "Leopard-Leopard": "<:Leopard_fruit:1422208240288010373>",
    "Yeti-Yeti": "<:Yeti_fruit:1422211990046117892>",
    "Kitsune-Kitsune": "<:Rocket_fruit:1422213078610743449>",
    "Dragon-Dragon": "<:Dragon_fruit:1422454878202232943>",
}

def get_emoji(fruit_name):
    return FRUIT_EMOJI.get(fruit_name, "🍎")

# ================= FETCH API (ASYNC) =================
async def fetch_stock():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, timeout=30) as response:
                return await response.json()
    except Exception as e:
        print(f"⚠️ Lỗi khi fetch API: {e}")
        return None

# ================= FORMAT EMBED =================
def format_embed(data):
    if not data or data.get("status") != "success":
        return discord.Embed(
            title="❌ Lỗi API",
            description="Không có dữ liệu stock",
            color=0xff0000
        )

    mirage_list = data.get("mirageStock", [])
    normal_list = data.get("normalStock", [])

    normal_lines = []
    mirage_lines = []

    for f in normal_list:
        emoji = get_emoji(f['name'])
        price = f"${f['price']:,}"
        normal_lines.append(f"{emoji} {f['name']} → {price}")

    for f in mirage_list:
        emoji = get_emoji(f['name'])
        price = f"${f['price']:,}"
        mirage_lines.append(f"{emoji} {f['name']} → {price}")

    embed = discord.Embed(title="🍏 Blox Fruits Stock", color=0x00ff99)
    embed.add_field(
        name="🛒 Dealer Stock",
        value="\n".join(normal_lines) or "Không có",
        inline=False
    )
    embed.add_field(
        name="💎 Mirage Stock",
        value="\n".join(mirage_lines) or "Không có",
        inline=False
    )

    now = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    embed.set_footer(text=f"👤 Author: {data.get('author', 'Unknown')} • ⏰ Last update: {now}")

    return embed

# ================= SNAPSHOT =================
def make_snapshot(data):
    return "|".join([
        f"{f['name']}:{f['price']}" for f in data.get("normalStock", []) + data.get("mirageStock", [])
    ])

# ================= AUTO UPDATE =================
@tasks.loop(seconds=60)
async def auto_update_stock():
    global stock_messages, last_stock
    data = await fetch_stock()
    if not data:
        print("⚠️ Không lấy được dữ liệu stock từ API")
        return

    embed = format_embed(data)
    stock_text = make_snapshot(data)

    for channel_id, message in list(stock_messages.items()):
        channel = bot.get_channel(channel_id)
        if not channel:
            continue

        if stock_text != last_stock.get(channel_id, ""):
            try:
                msg = await channel.fetch_message(message.id)
                await msg.edit(embed=embed)
                last_stock[channel_id] = stock_text
                print(f"✅ Stock updated in channel {channel_id}")
            except discord.NotFound:
                msg = await channel.send(embed=embed)
                stock_messages[channel_id] = msg
                last_stock[channel_id] = stock_text
                print(f"✅ Stock message recreated in channel {channel_id}")

# ================= COMMAND =================
@bot.command()
async def stock(ctx):
    global stock_messages, last_stock
    data = await fetch_stock()
    embed = format_embed(data)
    stock_text = make_snapshot(data)

    msg = await ctx.send(embed=embed)
    stock_messages[ctx.channel.id] = msg
    last_stock[ctx.channel.id] = stock_text

# ================= ON READY =================
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập thành {bot.user}")
    auto_update_stock.start()

# ================= RUN BOT =================
bot.run(TOKEN)
