import os
import threading
import sqlite3
from flask import Flask

import discord
from discord.ext import commands
from discord import app_commands

# =========================
# RENDER WEB SERVER
# =========================

app = Flask(__name__)

@app.route("/")
def home():
    return "National Euro Bank Bot Running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
# BOT SETUP
# =========================

TOKEN = os.getenv("TOKEN")

GUILD_ID = discord.Object(id=1510218934929068072)

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# DATABASE
# =========================

db = sqlite3.connect("bank.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")
db.commit()

def ensure_user(user_id):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users(user_id, balance) VALUES (?, ?)", (user_id, 0))
        db.commit()

def get_balance(user_id):
    ensure_user(user_id)
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()[0]

def add_balance(user_id, amount):
    ensure_user(user_id)
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id=?",
        (amount, user_id)
    )
    db.commit()

# =========================
# READY EVENT (GUILD SYNC FIX)
# =========================

@bot.event
async def on_ready():
    try:
        bot.tree.copy_global_to(guild=GUILD_ID)
        synced = await bot.tree.sync(guild=GUILD_ID)
        print(f"✅ Synced {len(synced)} guild commands")
    except Exception as e:
        print(f"❌ Sync error: {e}")

    print(f"Logged in as {bot.user}")

# =========================
# /BALANCE
# =========================

@bot.tree.command(name="balance", description="Check your balance", guild=GUILD_ID)
async def balance(interaction: discord.Interaction):
    bal = get_balance(interaction.user.id)
    await interaction.response.send_message(f"💰 Balance: €{bal:,}")

# =========================
# /WORK
# =========================

@bot.tree.command(name="work", description="Earn money", guild=GUILD_ID)
async def work(interaction: discord.Interaction):
    reward = 250
    add_balance(interaction.user.id, reward)
    await interaction.response.send_message(f"💼 You worked and earned €{reward}")

# =========================
# /PAY
# =========================

@bot.tree.command(name="pay", description="Pay a user", guild=GUILD_ID)
@app_commands.describe(member="User", amount="Amount")
async def pay(interaction: discord.Interaction, member: discord.Member, amount: int):

    if amount <= 0:
        return await interaction.response.send_message("❌ Invalid amount", ephemeral=True)

    sender = get_balance(interaction.user.id)

    if sender < amount:
        return await interaction.response.send_message("❌ Not enough money", ephemeral=True)

    add_balance(interaction.user.id, -amount)
    add_balance(member.id, amount)

    await interaction.response.send_message(f"💸 Sent €{amount:,} to {member.mention}")

# =========================
# /LEADERBOARD
# =========================

@bot.tree.command(name="leaderboard", description="Top users", guild=GUILD_ID)
async def leaderboard(interaction: discord.Interaction):

    cursor.execute("""
    SELECT user_id, balance
    FROM users
    ORDER BY balance DESC
    LIMIT 10
    """)

    data = cursor.fetchall()

    text = "🏆 Leaderboard\n\n"

    for i, (uid, bal) in enumerate(data, start=1):
        text += f"{i}. <@{uid}> — €{bal:,}\n"

    await interaction.response.send_message(text)

# =========================
# START EVERYTHING
# =========================

threading.Thread(target=run_web).start()
bot.run(TOKEN)