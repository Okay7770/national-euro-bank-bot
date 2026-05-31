import os
import threading
import sqlite3
from flask import Flask

import discord
from discord.ext import commands
from discord import app_commands

# =========================
# WEB SERVER FOR RENDER
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

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

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

# =========================
# DATABASE FUNCTIONS
# =========================

def ensure_user(user_id):
    cursor.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user_id,)
    )

    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (user_id, balance) VALUES (?, ?)",
            (user_id, 0)
        )
        db.commit()

def get_balance(user_id):
    ensure_user(user_id)

    cursor.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    )

    result = cursor.fetchone()

    return result[0]

def add_balance(user_id, amount):
    ensure_user(user_id)

    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id=?",
        (amount, user_id)
    )

    db.commit()

# =========================
# READY EVENT
# =========================

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Sync error: {e}")

# =========================
# /BALANCE
# =========================

@bot.tree.command(
    name="balance",
    description="Check your balance"
)
async def balance(interaction: discord.Interaction):

    bal = get_balance(interaction.user.id)

    await interaction.response.send_message(
        f"💰 Balance: €{bal:,}"
    )

# =========================
# /WORK
# =========================

@bot.tree.command(
    name="work",
    description="Earn money"
)
async def work(interaction: discord.Interaction):

    reward = 250

    add_balance(interaction.user.id, reward)

    await interaction.response.send_message(
        f"💼 You worked and earned €{reward:,}"
    )

# =========================
# /PAY
# =========================

@bot.tree.command(
    name="pay",
    description="Pay another user"
)
@app_commands.describe(
    member="User to pay",
    amount="Amount of money"
)
async def pay(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int
):

    if amount <= 0:
        return await interaction.response.send_message(
            "❌ Amount must be positive.",
            ephemeral=True
        )

    sender_balance = get_balance(interaction.user.id)

    if sender_balance < amount:
        return await interaction.response.send_message(
            "❌ You don't have enough money.",
            ephemeral=True
        )

    add_balance(interaction.user.id, -amount)
    add_balance(member.id, amount)

    await interaction.response.send_message(
        f"💸 Sent €{amount:,} to {member.mention}"
    )

# =========================
# /LEADERBOARD
# =========================

@bot.tree.command(
    name="leaderboard",
    description="View the richest users"
)
async def leaderboard(interaction: discord.Interaction):

    cursor.execute("""
    SELECT user_id, balance
    FROM users
    ORDER BY balance DESC
    LIMIT 10
    """)

    users = cursor.fetchall()

    if not users:
        return await interaction.response.send_message(
            "Nobody has money yet."
        )

    message = "🏆 **National Euro Bank Leaderboard**\n\n"

    for position, (user_id, balance) in enumerate(users, start=1):
        message += (
            f"{position}. <@{user_id}> — €{balance:,}\n"
        )

    await interaction.response.send_message(message)

# =========================
# START BOT
# =========================

threading.Thread(target=run_web).start()

bot.run(TOKEN)