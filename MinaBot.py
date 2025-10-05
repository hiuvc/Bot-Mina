# MinaBot.py
# Patch bỏ audioop cho Python 3.13
import sys, types
if "audioop" not in sys.modules:
    sys.modules["audioop"] = types.ModuleType("audioop")

import os
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import aiohttp
from keep_alive import keep_alive  # chắc chắn keep_alive.py cùng thư mục

# ================= CONFIG =================
TOKEN = os.getenv("DISCORD_TOKEN")
API_URL = "https://fruitsstockapi.onrender.com/fruitstock"
CHANNEL_ID = 1423695651610427524  # thay bằng ID kênh của bạn

# ================= INTENTS =================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= STORAGE =================
stock_messages = {}  # lưu message ID per channel
last_snapshot = {}

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
    "Portal-Portal": "<:Portal_fruit:1422210170401849344>",
}

IGNORE_FRUITS = ["Rocket-Rocket", "Spin-Spin"]

def get_emoji(name: str) -> str:
    return FRUIT_EMOJI.get(name, "🍎")

# ================= SNAPSHOT =================
def make_snapshot(data):
    snapshot = {}
    for section in ["normalStock", "mirageStock"]:
        fruits = data.get(section, [])
        snapshot[section] = {f['name']: f['price'] for f in fruits}
    return snapshot

# ================= COOL DOWN =================
last_change_time = {
    "normalStock": None,
    "mirageStock": None
}

COOLDOWN = {
    "normalStock": timedelta(hours=4),
    "mirageStock": timedelta(hours=2)
}

def get_cooldown_remaining(section):
    last_time = last_change_time.get(section)
    if not last_time:
        return "Chưa có thay đổi"
    remaining = last_time + COOLDOWN[section] - datetime.now()
    if remaining.total_seconds() <= 0:
        return "Đã reset"
    hours, remainder = divmod(int(remaining.total_seconds()), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

# ================= FORMAT EMBED =================
STOCK_NAME = {
    "normalStock": "🛒 Normal Stock 🛒",
    "mirageStock": "🏝️ Mirage Stock 🏝️"
}

def format_embed(data):
    embed = discord.Embed(title=" Blox Fruits Stock ", color=0x00ff99)
    for section in ["normalStock", "mirageStock"]:
        fruits = data.get(section, [])
        lines = []
        for f in fruits:
            if f['name'] in IGNORE_FRUITS:
                continue
            emoji = get_emoji(f['name'])
            lines.append(f"{emoji} **{f['name']}** → 💰 {f['price']:,} Beli")
        # Thêm cooldown
        lines.append(f"⏱️ New fruits in: {get_cooldown_remaining(section)}")
        display_name = STOCK_NAME.get(section, section)
        embed.add_field(name=display_name,
                        value="\n".join(lines) or "Không có dữ liệu",
                        inline=False)
    return embed

# ================= FETCH API =================
async def fetch_stock():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, timeout=30) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"⚠️ Lỗi API: {response.status}")
                    return None
    except Exception as e:
        print(f"⚠️ Exception khi fetch API: {e}")
        return None

# ================= TASK AUTO UPDATE =================
@tasks.loop(seconds=10)
async def auto_update_stock():
    global last_snapshot
    try:
        data = await fetch_stock()
        if not data:
            return
        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print("⚠️ Không tìm thấy kênh Discord!")
            return
        new_snapshot = make_snapshot(data)
        if not last_snapshot:
            last_snapshot = new_snapshot
            embed = format_embed(data)
            msg = await channel.send(embed=embed)
            stock_messages[channel.id] = msg.id
            print("✅ Gửi embed stock ban đầu")
            return
        if new_snapshot != last_snapshot:
            for section in ["normalStock", "mirageStock"]:
                old_fruits = last_snapshot.get(section, {})
                new_fruits = new_snapshot.get(section, {})
                if old_fruits != new_fruits:
                    last_change_time[section] = datetime.now()
            embed = format_embed(data)
            try:
                msg_id = stock_messages.get(channel.id)
                if msg_id:
                    msg = await channel.fetch_message(msg_id)
                    await msg.edit(embed=embed)
                    print("✏️ Đã edit embed với stock mới")
                else:
                    msg = await channel.send(embed=embed)
                    stock_messages[channel.id] = msg.id
                    print("🆕 Gửi embed mới vì không tìm thấy message cũ")
            except Exception as e:
                print(f"⚠️ Lỗi khi edit message: {e}")
                msg = await channel.send(embed=embed)
                stock_messages[channel.id] = msg.id
            last_snapshot = new_snapshot
    except Exception as e:
        print(f"⚠️ Lỗi trong auto_update_stock: {e}")

# ================= TASK UPDATE COUNTDOWN REALTIME =================
@tasks.loop(minutes=1)
async def update_cooldown_embed():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return
    msg_id = stock_messages.get(channel.id)
    if not msg_id:
        return
    try:
        msg = await channel.fetch_message(msg_id)
        embed = msg.embeds[0]
        for i, section in enumerate(["normalStock", "mirageStock"]):
            value_lines = embed.fields[i].value.split("\n")
            value_lines[-1] = f"⏱️ New fruits in: {get_cooldown_remaining(section)}"
            embed.set_field_at(i, name=embed.fields[i].name,
                               value="\n".join(value_lines), inline=False)
        await msg.edit(embed=embed)
    except Exception as e:
        print(f"⚠️ Lỗi update cooldown: {e}")

# ================= COMMAND !stock =================
@bot.command()
async def stock(ctx):
    try:
        data = await fetch_stock()
        if not data:
            await ctx.send("⚠️ Không lấy được dữ liệu stock")
            return
        embed = format_embed(data)
        msg = await ctx.send(embed=embed)
        stock_messages[ctx.channel.id] = msg.id
        last_snapshot[ctx.channel.id] = make_snapshot(data)
    except Exception as e:
        await ctx.send(f"⚠️ Lỗi khi chạy lệnh !stock: {e}")

# ================= BOT READY =================
@bot.event
async def on_ready():
    print(f"🤖 Bot đã online: {bot.user}")
    auto_update_stock.start()
    update_cooldown_embed.start()

# ================= KEEP ALIVE =================
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
