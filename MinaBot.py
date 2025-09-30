import discord
from discord.ext import commands, tasks
import aiohttp
import os
from keep_alive import keep_alive

# ================= CONFIG =================
TOKEN = os.getenv("DISCORD_TOKEN")  # Lấy token từ Environment Variable
API_URL = "https://fruitsstockapi.onrender.com/fruitstock"
CHANNEL_ID = 123456789012345678  # Thay bằng ID kênh Discord bạn muốn gửi

# ================= INTENTS =================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ================= STORAGE =================
stock_messages = {}
last_snapshot = {}

# ================= FRUIT → EMOJI =================
FRUIT_EMOJI = {
    "Rocket-Rocket": "<:Rocket_fruit:1422206917106733227>",
    "Spin-Spin": "<:Spin_fruit:1422212836796534804>",
    "Blade-Blade": "<:Blade_fruit:1422212358297882715>",
    "Sand-Sand": "<:Sand_fruit:1422212111685124208>",
    # thêm fruit khác ở đây
}

def get_emoji(name: str) -> str:
    return FRUIT_EMOJI.get(name, "🍎")

# ================= FORMAT =================
def make_snapshot(data):
    """Tạo snapshot đơn giản từ dữ liệu API"""
    snapshot = {}
    for section, fruits in data.items():
        snapshot[section] = {f['name']: f['price'] for f in fruits}
    return snapshot

def compare_snapshot(old, new):
    """So sánh 2 snapshot → log thay đổi"""
    logs = []
    for section in new:
        old_fruits = old.get(section, {})
        new_fruits = new.get(section, {})

        # Kiểm tra fruit mới
        for fruit in new_fruits:
            if fruit not in old_fruits:
                logs.append(f"[{section}] ➕ {fruit} xuất hiện với giá {new_fruits[fruit]:,}")
            elif old_fruits[fruit] != new_fruits[fruit]:
                logs.append(f"[{section}] 🔄 {fruit} đổi giá {old_fruits[fruit]:,} → {new_fruits[fruit]:,}")

        # Kiểm tra fruit bị xoá
        for fruit in old_fruits:
            if fruit not in new_fruits:
                logs.append(f"[{section}] ❌ {fruit} biến mất")
    return logs

def format_embed(data):
    embed = discord.Embed(title="📦 Fruit Stock Update", color=0x00ff99)
    for section, fruits in data.items():
        lines = []
        for f in fruits:
            emoji = get_emoji(f['name'])
            lines.append(f"{emoji} **{f['name']}** — 💵 {f['price']:,}")
        embed.add_field(name=f"📂 {section}", value="\n".join(lines) or "Không có dữ liệu", inline=False)
    return embed

# ================= FETCH =================
async def fetch_stock():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, timeout=20) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"⚠️ Lỗi API: {response.status}")
                    return None
    except Exception as e:
        print(f"⚠️ Exception khi fetch API: {e}")
        return None

# ================= LOOP TASK =================
@tasks.loop(seconds=60)
async def auto_update_stock():
    global last_snapshot

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
        logs = compare_snapshot(last_snapshot, new_snapshot)
        if logs:
            print("\n".join(logs))

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

# ================= START =================
@bot.event
async def on_ready():
    print(f"🤖 Bot đã online: {bot.user}")
    auto_update_stock.start()

if __name__ == "__main__":
    keep_alive()   # giữ cho bot luôn chạy (Repl.it / Render free)
    bot.run(TOKEN)
