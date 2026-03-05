import discord
from discord.ext import commands
import json
import os
import datetime
import asyncio

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
TOKEN = os.environ.get("TOKEN")
PREFIX = "!"
DATA_FILE = "stats_data.json"

# ─────────────────────────────────────────
#  SETUP
# ─────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Stocke les membres en vocal avec leur heure d'arrivée
vocal_actif = {}

# ─────────────────────────────────────────
#  GESTION DES DONNÉES
# ─────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "messages": {},
        "vocal_minutes": {},
        "last_reset": datetime.datetime.utcnow().isoformat()
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def format_time(minutes):
    """Convertit les minutes en format lisible."""
    minutes = int(minutes)
    if minutes < 60:
        return f"{minutes} min"
    heures = minutes // 60
    mins = minutes % 60
    if heures < 24:
        return f"{heures}h {mins}min"
    jours = heures // 24
    h = heures % 24
    return f"{jours}j {h}h {mins}min"

def check_reset(data):
    """Vérifie si on doit reset les stats (chaque semaine)."""
    last = datetime.datetime.fromisoformat(data["last_reset"])
    now = datetime.datetime.utcnow()
    if (now - last).days >= 7:
        data["messages"] = {}
        data["vocal_minutes"] = {}
        data["last_reset"] = now.isoformat()
        save_data(data)
        return True
    return False

# ─────────────────────────────────────────
#  ÉVÉNEMENTS
# ─────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Sayuri Stats connecté : {bot.user}")
    await bot.change_presence(activity=discord.Game(name="📊 !stats | !top"))
    # Lance la vérification du reset hebdomadaire
    bot.loop.create_task(weekly_reset_check())

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    data = load_data()
    check_reset(data)
    user_id = str(message.author.id)
    data["messages"][user_id] = data["messages"].get(user_id, 0) + 1
    save_data(data)
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    user_id = str(member.id)

    # Rejoint un salon vocal
    if before.channel is None and after.channel is not None:
        vocal_actif[user_id] = datetime.datetime.utcnow()

    # Quitte un salon vocal
    elif before.channel is not None and after.channel is None:
        if user_id in vocal_actif:
            debut = vocal_actif.pop(user_id)
            minutes = (datetime.datetime.utcnow() - debut).total_seconds() / 60
            data = load_data()
            data["vocal_minutes"][user_id] = data["vocal_minutes"].get(user_id, 0) + minutes
            save_data(data)

# ─────────────────────────────────────────
#  RESET HEBDOMADAIRE AUTOMATIQUE
# ─────────────────────────────────────────
async def weekly_reset_check():
    await bot.wait_until_ready()
    while not bot.is_closed():
        data = load_data()
        if check_reset(data):
            print("🔄 Reset hebdomadaire effectué !")
            for guild in bot.guilds:
                canal = discord.utils.get(guild.text_channels, name="général")
                if canal:
                    embed = discord.Embed(
                        title="🔄 Reset Hebdomadaire !",
                        description="Les stats de la semaine ont été remises à zéro.\nBonne semaine à tous ! 💪",
                        color=discord.Color.blurple()
                    )
                    await canal.send(embed=embed)
        await asyncio.sleep(3600)  # Vérifie toutes les heures

# ─────────────────────────────────────────
#  COMMANDES
# ─────────────────────────────────────────

@bot.command(name="stats")
async def stats(ctx, membre: discord.Member = None):
    """Affiche les stats d'un membre. Usage : !stats ou !stats @user"""
    membre = membre or ctx.author
    data = load_data()
    user_id = str(membre.id)

    messages = data["messages"].get(user_id, 0)
    vocal = data["vocal_minutes"].get(user_id, 0)

    # Calcule le temps vocal actif en ce moment
    if user_id in vocal_actif:
        debut = vocal_actif[user_id]
        vocal += (datetime.datetime.utcnow() - debut).total_seconds() / 60

    # Classement messages
    classement_msg = sorted(data["messages"].items(), key=lambda x: x[1], reverse=True)
    rang_msg = next((i + 1 for i, (uid, _) in enumerate(classement_msg) if uid == user_id), "N/A")

    # Classement vocal
    classement_voc = sorted(data["vocal_minutes"].items(), key=lambda x: x[1], reverse=True)
    rang_voc = next((i + 1 for i, (uid, _) in enumerate(classement_voc) if uid == user_id), "N/A")

    # Prochain reset
    last_reset = datetime.datetime.fromisoformat(data["last_reset"])
    prochain_reset = last_reset + datetime.timedelta(days=7)
    jours_restants = (prochain_reset - datetime.datetime.utcnow()).days

    embed = discord.Embed(
        title=f"📊 Stats de {membre.display_name}",
        color=membre.color if membre.color != discord.Color.default() else discord.Color.blurple(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_thumbnail(url=membre.display_avatar.url)
    embed.add_field(name="💬 Messages envoyés", value=f"**{messages:,}**", inline=True)
    embed.add_field(name="🎙️ Temps en vocal", value=f"**{format_time(vocal)}**", inline=True)
    embed.add_field(name="​", value="​", inline=True)
    embed.add_field(name="🏅 Rang messages", value=f"**#{rang_msg}**", inline=True)
    embed.add_field(name="🏅 Rang vocal", value=f"**#{rang_voc}**", inline=True)
    embed.add_field(name="​", value="​", inline=True)
    embed.set_footer(text=f"🔄 Reset dans {jours_restants} jour(s)")
    await ctx.send(embed=embed)


@bot.command(name="top")
async def top(ctx):
    """Affiche le classement messages + vocal."""
    data = load_data()

    # Ajoute le temps vocal en cours
    vocal_data = dict(data["vocal_minutes"])
    for user_id, debut in vocal_actif.items():
        minutes = (datetime.datetime.utcnow() - debut).total_seconds() / 60
        vocal_data[user_id] = vocal_data.get(user_id, 0) + minutes

    top_msg = sorted(data["messages"].items(), key=lambda x: x[1], reverse=True)[:3]
    top_voc = sorted(vocal_data.items(), key=lambda x: x[1], reverse=True)[:3]

    medailles = ["🥇", "🥈", "🥉"]

    # ── TOP MESSAGES ──
    if top_msg:
        # Photo de profil du 1er
        premier_msg = ctx.guild.get_member(int(top_msg[0][0]))
        embed_msg = discord.Embed(
            title="💬 Classement — Messages",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        if premier_msg:
            embed_msg.set_thumbnail(url=premier_msg.display_avatar.url)

        desc_msg = ""
        for i, (uid, count) in enumerate(top_msg):
            membre = ctx.guild.get_member(int(uid))
            nom = membre.display_name if membre else "Inconnu"
            if i == 0:
                desc_msg += f"{medailles[i]} **{nom}** — `{count:,}` messages 👑\n"
            elif i == 1:
                desc_msg += f"{medailles[i]} **{nom}** — `{count:,}` messages ✨\n"
            else:
                desc_msg += f"{medailles[i]} **{nom}** — `{count:,}` messages 🔥\n"

        embed_msg.description = desc_msg
        await ctx.send(embed=embed_msg)
    else:
        await ctx.send("📭 Aucun message enregistré pour l'instant !")

    # ── TOP VOCAL ──
    if top_voc:
        # Photo de profil du 1er
        premier_voc = ctx.guild.get_member(int(top_voc[0][0]))
        embed_voc = discord.Embed(
            title="🎙️ Classement — Temps Vocal",
            color=discord.Color.purple(),
            timestamp=datetime.datetime.utcnow()
        )
        if premier_voc:
            embed_voc.set_thumbnail(url=premier_voc.display_avatar.url)

        desc_voc = ""
        for i, (uid, minutes) in enumerate(top_voc):
            membre = ctx.guild.get_member(int(uid))
            nom = membre.display_name if membre else "Inconnu"
            if i == 0:
                desc_voc += f"{medailles[i]} **{nom}** — `{format_time(minutes)}` 👑\n"
            elif i == 1:
                desc_voc += f"{medailles[i]} **{nom}** — `{format_time(minutes)}` ✨\n"
            else:
                desc_voc += f"{medailles[i]} **{nom}** — `{format_time(minutes)}` 🔥\n"

        embed_voc.description = desc_voc
        await ctx.send(embed=embed_voc)
    else:
        await ctx.send("📭 Aucun temps vocal enregistré pour l'instant !")


@bot.command(name="resetstats")
@commands.has_permissions(administrator=True)
async def resetstats(ctx):
    """Reset manuel des stats (admin uniquement)."""
    data = load_data()
    data["messages"] = {}
    data["vocal_minutes"] = {}
    data["last_reset"] = datetime.datetime.utcnow().isoformat()
    save_data(data)
    embed = discord.Embed(
        title="🔄 Stats remises à zéro !",
        description="Toutes les stats ont été reset par un admin.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)


@bot.command(name="statsaide")
async def statsaide(ctx):
    """Affiche l'aide du bot stats."""
    embed = discord.Embed(title="📖 Aide — Sayuri Stats", color=discord.Color.blurple())
    embed.add_field(name="📊 !stats", value="Voir tes propres stats", inline=False)
    embed.add_field(name="📊 !stats @user", value="Voir les stats d'un membre", inline=False)
    embed.add_field(name="🏆 !top", value="Classement messages + vocal", inline=False)
    embed.add_field(name="🔄 !resetstats", value="Reset les stats *(admin)*", inline=False)
    embed.set_footer(text="🔄 Reset automatique chaque semaine")
    await ctx.send(embed=embed)


# ─────────────────────────────────────────
#  LANCEMENT
# ─────────────────────────────────────────
bot.run(TOKEN)
