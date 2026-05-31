import os
import threading
import sqlite3
from flask import Flask

import discord
from discord.ext import commands
from discord import app_commands

# ---------------- WEB ----------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ---------------- BOT ----------------

TOKEN = os.getenv("TOKEN")
GUILD_ID = 1510218934929068072

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- DB ----------------

db = sqlite3.connect("bank.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")
db.commit()

def ensure_user(uid):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users(user_id,balance) VALUES (?,0)", (uid,))
        db.commit()

def get_balance(uid):
    ensure_user(uid)
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    return cursor.fetchone()[0]

def add_balance(uid, amount):
    ensure_user(uid)
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id=?",
        (amount, uid)
    )
    db.commit()

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        guild = discord.Object(id=1510218934929068072)

        bot.tree.clear_commands(guild=guild)

        synced = await bot.tree.sync(guild=guild)

        print(f"✅ Synced {len(synced)} commands to guild")
    except Exception as e:
        print(f"❌ Sync error: {e}")
# ---------------- COMMANDS ----------------

@bot.tree.command(name="balance", description="Check balance")
async def balance(interaction: discord.Interaction):
    bal = get_balance(interaction.user.id)
    await interaction.response.send_message(f"💰 €{bal}")

@bot.tree.command(name="work", description="Earn money")
async def work(interaction: discord.Interaction):
    add_balance(interaction.user.id, 250)
    await interaction.response.send_message("💼 You earned €250")

@bot.tree.command(name="pay", description="Pay someone")
@app_commands.describe(member="User", amount="Amount")
async def pay(interaction: discord.Interaction, member: discord.Member, amount: int):

    sender = get_balance(interaction.user.id)

    if sender < amount:
        return await interaction.response.send_message("❌ Not enough money", ephemeral=True)

    add_balance(interaction.user.id, -amount)
    add_balance(member.id, amount)

    await interaction.response.send_message(f"💸 Sent €{amount}")

# ---------------- START ----------------

threading.Thread(target=run_web).start()
bot.run(TOKEN)