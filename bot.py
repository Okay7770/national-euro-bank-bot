import os
import threading
import sqlite3
from flask import Flask

import discord
from discord.ext import commands
from discord import app_commands

# -------------------------
# WEB SERVER FOR RENDER
# -------------------------

app = Flask(__name__)

@app.route("/")
def home():
    return "National Euro Bank Bot Online"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# -------------------------
# BOT SETUP
# -------------------------

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------------
# DATABASE
# -------------------------

db = sqlite3.connect("bank.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")

db.commit()

def ensure_user(user_id):
    cursor.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user_id,)
    )

    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users(user_id,balance) VALUES (?,?)",
            (user_id,0)
        )
        db.commit()

def get_balance(user_id):
    ensure_user(user_id)

    cursor.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (user_id,)
    )

    return cursor.fetchone()[0]

def add_balance(user_id, amount):
    ensure_user(user_id)

    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id=?",
        (amount,user_id)
    )

    db.commit()

# -------------------------
# READY
# -------------------------

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

# -------------------------
# /BALANCE
# -------------------------

@bot.tree.command(name="balance", description="View your balance")
async def balance(interaction: discord.Interaction):

    bal = get_balance(interaction.user.id)

    await interaction.response.send_message(
        f"💰 Your balance is €{bal:,}"
    )

# -------------------------
# /WORK
# -------------------------

@bot.tree.command(name="work", description="Work for money")
async def work(interaction: discord.Interaction):

    reward = 250

    add_balance(interaction.user.id, reward)

    await interaction.response.send_message(
        f"💼 You worked and earned €{reward}"
    )

# -------------------------
# /PAY
# -------------------------

@bot.tree.command(name="pay", description="Pay another user")
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
            "❌ Amount must be greater than 0.",
            ephemeral=True
        )

    sender_balance = get_balance(interaction.user.id)

    if sender_balance < amount:
        return await interaction.response.send_message(
            "❌ Not enough money.",
            ephemeral=True
        )

    add_balance(interaction.user.id, -amount)
    add_balance(member.id, amount)

    await interaction.response.send_message(
        f"💸 Sent €{amount:,} to {member.mention}"
    )

# -------------------------
# /LEADERBOARD
# -------------------------

@bot.tree.command(
    name="leaderboard",
    description="Top richest users"
)
async def leaderboard(
    interaction: discord.Interaction
):

    cursor.execute("""
    SELECT user_id,balance
    FROM users
    ORDER BY balance DESC
    LIMIT 10
    """)

    users = cursor.fetchall()

    msg = "🏆 Economy Leaderboard\n\n"

    for i, user in enumerate(users, start=1):
        msg += f"{i}. <@{user[0]}> — €{user[1]:,}\n"

    await interaction.response.send_message(msg)

# -------------------------
# START
# -------------------------

threading.Thread(target=run_web).start()

bot.run(TOKEN)