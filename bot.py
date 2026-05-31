import os
import threading
import sqlite3
import asyncio
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

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# DATABASE
# =========================

db = sqlite3.connect("bank.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    job TEXT DEFAULT 'Unemployed'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS treasury (
    id INTEGER PRIMARY KEY,
    money INTEGER DEFAULT 0
)
""")

cursor.execute("INSERT OR IGNORE INTO treasury (id, money) VALUES (1, 0)")
db.commit()

# =========================
# JOBS
# =========================

JOBS = {
    "Worker": {"salary": 500, "tax": 5},
    "Promoter": {"salary": 800, "tax": 7},
    "Police Officer": {"salary": 1200, "tax": 8},
    "Bank Staff": {"salary": 1500, "tax": 10},
    "Government": {"salary": 2500, "tax": 12},
}

# =========================
# FUNCTIONS
# =========================

def ensure_user(user_id):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO users (user_id, balance, job) VALUES (?, ?, ?)",
            (user_id, 0, "Unemployed")
        )
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

def set_job(user_id, job):
    ensure_user(user_id)
    cursor.execute(
        "UPDATE users SET job=? WHERE user_id=?",
        (job, user_id)
    )
    db.commit()

# =========================
# SALARY LOOP
# =========================

async def salary_loop():
    await bot.wait_until_ready()

    while not bot.is_closed():
        await asyncio.sleep(3600)

        cursor.execute("SELECT user_id, job FROM users")
        users = cursor.fetchall()

        for user_id, job in users:

            if job not in JOBS:
                continue

            salary = JOBS[job]["salary"]
            tax = JOBS[job]["tax"]

            tax_amount = int(salary * tax / 100)
            payout = salary - tax_amount

            add_balance(user_id, payout)

            cursor.execute(
                "UPDATE treasury SET money = money + ? WHERE id=1",
                (tax_amount,)
            )

        db.commit()
        print("Salaries paid")

# =========================
# EVENTS
# =========================

@bot.event
async def setup_hook():
    asyncio.create_task(salary_loop())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Sync error: {e}")

# =========================
# COMMANDS
# =========================

@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"💰 Balance: €{get_balance(interaction.user.id):,}"
    )

@bot.tree.command(name="work", description="Earn money")
async def work(interaction: discord.Interaction):
    add_balance(interaction.user.id, 250)
    await interaction.response.send_message(
        "💼 You worked and earned €250"
    )

@bot.tree.command(name="pay", description="Pay another user")
@app_commands.describe(member="User", amount="Amount")
async def pay(interaction: discord.Interaction, member: discord.Member, amount: int):

    if amount <= 0:
        return await interaction.response.send_message(
            "❌ Invalid amount",
            ephemeral=True
        )

    if get_balance(interaction.user.id) < amount:
        return await interaction.response.send_message(
            "❌ Not enough money",
            ephemeral=True
        )

    add_balance(interaction.user.id, -amount)
    add_balance(member.id, amount)

    await interaction.response.send_message(
        f"💸 Sent €{amount:,} to {member.mention}"
    )

@bot.tree.command(name="leaderboard", description="Richest users")
async def leaderboard(interaction: discord.Interaction):

    cursor.execute("""
    SELECT user_id, balance
    FROM users
    ORDER BY balance DESC
    LIMIT 10
    """)

    rows = cursor.fetchall()

    if not rows:
        return await interaction.response.send_message("No data yet.")

    msg = "🏆 National Euro Bank Leaderboard\n\n"

    for pos, (uid, bal) in enumerate(rows, start=1):
        msg += f"{pos}. <@{uid}> — €{bal:,}\n"

    await interaction.response.send_message(msg)

@bot.tree.command(name="jobs", description="View available jobs")
async def jobs(interaction: discord.Interaction):

    text = ""

    for job, data in JOBS.items():
        text += (
            f"💼 {job}\n"
            f"Salary: €{data['salary']}/hour\n"
            f"Tax: {data['tax']}%\n\n"
        )

    await interaction.response.send_message(text)

@bot.tree.command(name="job", description="Choose a job")
@app_commands.describe(job="Job name")
async def job(interaction: discord.Interaction, job: str):

    if job not in JOBS:
        return await interaction.response.send_message(
            "❌ Invalid job name.",
            ephemeral=True
        )

    set_job(interaction.user.id, job)

    await interaction.response.send_message(
        f"💼 You are now a {job}"
    )

@bot.tree.command(name="treasury", description="View treasury funds")
async def treasury(interaction: discord.Interaction):

    cursor.execute("SELECT money FROM treasury WHERE id=1")
    money = cursor.fetchone()[0]

    await interaction.response.send_message(
        f"🏛️ Treasury Balance: €{money:,}"
    )

# =========================
# START
# =========================

threading.Thread(target=run_web).start()
bot.run(TOKEN)
