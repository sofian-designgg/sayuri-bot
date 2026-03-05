import discord
from discord.ext import commands
import json
import os
import datetime

# ─────────────────────────────────────────
#  CONFIG — remplace par ton token
# ─────────────────────────────────────────
TOKEN = os.environ.get("TOKEN")
PREFIX = "!"
VOTE_EMOJI = "⭐"
EMOJI_1 = "🔴"
EMOJI_2 = "🔵"
DATA_FILE = "fame_data.json"

# ─────────────────────────────────────────
#  SETUP
# ─────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ─────────────────────────────────────────
#  GESTION DES DONNÉES
# ─────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"votes": {}, "voters": {}, "vote_message_id": None, "duels": {}, "duel_voters": {}}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─────────────────────────────────────────
#  ÉVÉNEMENTS
# ─────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot Fame connecté : {bot.user}")
    await bot.change_presence(activity=discord.Game(name="⚔️ !duel @user1 @user2"))

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    data = load_data()
    message_id = str(reaction.message.id)

    # ── Système duel ──
    if message_id in data.get("duels", {}):
        duel = data["duels"][message_id]
        voter_id = str(user.id)
        emoji = str(reaction.emoji)

        if emoji not in [EMOJI_1, EMOJI_2]:
            await reaction.remove(user)
            return

        # Déjà voté ?
        if voter_id in data.get("duel_voters", {}).get(message_id, {}):
            await reaction.remove(user)
            try:
                await user.send("❌ Tu as déjà voté dans ce duel !")
            except:
                pass
            return

        # Pas voter pour soi-même
        target_id = duel["user1_id"] if emoji == EMOJI_1 else duel["user2_id"]
        if voter_id == target_id:
            await reaction.remove(user)
            try:
                await user.send("❌ Tu ne peux pas voter pour toi-même !")
            except:
                pass
            return

        # Enregistre le vote
        if message_id not in data["duel_voters"]:
            data["duel_voters"][message_id] = {}
        data["duel_voters"][message_id][voter_id] = emoji

        if emoji == EMOJI_1:
            data["duels"][message_id]["votes1"] = data["duels"][message_id].get("votes1", 0) + 1
        else:
            data["duels"][message_id]["votes2"] = data["duels"][message_id].get("votes2", 0) + 1

        save_data(data)
        return

    # ── Système fame classique ──
    if str(reaction.message.id) != str(data.get("vote_message_id")):
        return
    if str(reaction.emoji) != VOTE_EMOJI:
        return

    voter_id = str(user.id)
    if voter_id in data["voters"]:
        await reaction.remove(user)
        try:
            await user.send("❌ Tu as déjà voté ! Un seul vote par personne.")
        except:
            pass
        return

    message = reaction.message
    target_id = None
    for embed in message.embeds:
        if embed.footer and embed.footer.text:
            target_id = embed.footer.text.replace("user_id:", "").strip()

    if not target_id:
        return

    if voter_id == target_id:
        await reaction.remove(user)
        try:
            await user.send("❌ Tu ne peux pas voter pour toi-même !")
        except:
            pass
        return

    data["voters"][voter_id] = target_id
    data["votes"][target_id] = data["votes"].get(target_id, 0) + 1
    save_data(data)

    try:
        await user.send("✅ Ton vote a bien été enregistré !")
    except:
        pass

# ─────────────────────────────────────────
#  COMMANDE DUEL
# ─────────────────────────────────────────

@bot.command(name="duel")
async def duel(ctx, membre1: discord.Member, membre2: discord.Member):
    """Lance un duel de fame entre 2 membres. Usage : !duel @user1 @user2"""

    if membre1.bot or membre2.bot:
        await ctx.send("❌ On ne peut pas faire dueller un bot !")
        return

    if membre1.id == membre2.id:
        await ctx.send("❌ Tu ne peux pas faire dueller quelqu'un contre lui-même !")
        return

    # ── Profil membre 1 ──
    roles1 = [r.mention for r in membre1.roles if r.name != "@everyone"]
    joined1 = membre1.joined_at.strftime("%d/%m/%Y") if membre1.joined_at else "Inconnu"
    created1 = membre1.created_at.strftime("%d/%m/%Y")
    color1 = membre1.color if membre1.color != discord.Color.default() else discord.Color.red()

    embed1 = discord.Embed(title=f"🔴 {membre1.display_name}", color=color1)
    embed1.set_thumbnail(url=membre1.display_avatar.url)
    embed1.add_field(name="📛 Pseudo", value=str(membre1), inline=True)
    embed1.add_field(name="📅 Sur le serv depuis", value=joined1, inline=True)
    embed1.add_field(name="🎂 Compte créé le", value=created1, inline=True)
    embed1.add_field(name=f"🎭 Rôles ({len(roles1)})", value=", ".join(roles1) if roles1 else "Aucun", inline=False)

    # ── Profil membre 2 ──
    roles2 = [r.mention for r in membre2.roles if r.name != "@everyone"]
    joined2 = membre2.joined_at.strftime("%d/%m/%Y") if membre2.joined_at else "Inconnu"
    created2 = membre2.created_at.strftime("%d/%m/%Y")
    color2 = membre2.color if membre2.color != discord.Color.default() else discord.Color.blue()

    embed2 = discord.Embed(title=f"🔵 {membre2.display_name}", color=color2)
    embed2.set_thumbnail(url=membre2.display_avatar.url)
    embed2.add_field(name="📛 Pseudo", value=str(membre2), inline=True)
    embed2.add_field(name="📅 Sur le serv depuis", value=joined2, inline=True)
    embed2.add_field(name="🎂 Compte créé le", value=created2, inline=True)
    embed2.add_field(name=f"🎭 Rôles ({len(roles2)})", value=", ".join(roles2) if roles2 else "Aucun", inline=False)

    # ── Message de vote ──
    embed_vote = discord.Embed(
        title="⚔️ DUEL DE FAME",
        description=(
            f"**{membre1.display_name}** {EMOJI_1} VS {EMOJI_2} **{membre2.display_name}**\n\n"
            f"Réagis avec {EMOJI_1} pour **{membre1.display_name}**\n"
            f"Réagis avec {EMOJI_2} pour **{membre2.display_name}**\n\n"
            f"🔒 **1 vote par personne** — impossible de voter pour soi-même."
        ),
        color=discord.Color.gold()
    )

    await ctx.send(embed=embed_vote)
    await ctx.send(embed=embed1)
    msg = await ctx.send(embed=embed2)

    await msg.add_reaction(EMOJI_1)
    await msg.add_reaction(EMOJI_2)

    # Sauvegarde le duel
    data = load_data()
    data["duels"][str(msg.id)] = {
        "user1_id": str(membre1.id),
        "user2_id": str(membre2.id),
        "votes1": 0,
        "votes2": 0
    }
    save_data(data)


@bot.command(name="resultat")
async def resultat(ctx, membre1: discord.Member, membre2: discord.Member):
    """Affiche le résultat d'un duel. Usage : !resultat @user1 @user2"""
    data = load_data()

    duel_trouve = None
    for msg_id, duel in data.get("duels", {}).items():
        if (duel["user1_id"] == str(membre1.id) and duel["user2_id"] == str(membre2.id)) or \
           (duel["user1_id"] == str(membre2.id) and duel["user2_id"] == str(membre1.id)):
            duel_trouve = duel
            break

    if not duel_trouve:
        await ctx.send("❌ Aucun duel trouvé entre ces deux membres !")
        return

    votes1 = duel_trouve.get("votes1", 0)
    votes2 = duel_trouve.get("votes2", 0)

    if votes1 > votes2:
        gagnant, perdant = membre1, membre2
        v_gagnant, v_perdant = votes1, votes2
    elif votes2 > votes1:
        gagnant, perdant = membre2, membre1
        v_gagnant, v_perdant = votes2, votes1
    else:
        await ctx.send(f"🤝 Égalité ! Les deux ont **{votes1}** vote(s) !")
        return

    embed = discord.Embed(
        title="🏆 Résultat du Duel",
        description=f"🏆 **{gagnant.display_name}** remporte le duel !",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=gagnant.display_avatar.url)
    embed.add_field(name=f"🏆 {gagnant.display_name}", value=f"{v_gagnant} vote(s)", inline=True)
    embed.add_field(name=f"💀 {perdant.display_name}", value=f"{v_perdant} vote(s)", inline=True)
    await ctx.send(embed=embed)


# ─────────────────────────────────────────
#  COMMANDES FAME CLASSIQUES
# ─────────────────────────────────────────

@bot.command(name="nomine")
@commands.has_permissions(manage_messages=True)
async def nomine(ctx, membre: discord.Member):
    """Crée un message de vote pour un membre. Usage : !nomine @user"""
    if membre.bot:
        await ctx.send("❌ On ne peut pas nominer un bot !")
        return

    data = load_data()
    embed = discord.Embed(
        title=f"⭐ Vote de Fame — {membre.display_name}",
        description=(
            f"Réagis avec {VOTE_EMOJI} pour donner ta **fame** à {membre.mention} !\n\n"
            f"🔒 **1 vote par personne** — tu ne peux pas voter pour toi-même."
        ),
        color=discord.Color.gold(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.set_thumbnail(url=membre.display_avatar.url)
    embed.set_footer(text=f"user_id:{membre.id}")

    msg = await ctx.send(embed=embed)
    await msg.add_reaction(VOTE_EMOJI)
    data["vote_message_id"] = str(msg.id)
    save_data(data)
    await ctx.message.delete()


@bot.command(name="top")
async def top(ctx):
    """Affiche le top 10 des membres les plus fameux."""
    data = load_data()

    if not data["votes"]:
        await ctx.send("📭 Aucun vote pour l'instant !")
        return

    classement = sorted(data["votes"].items(), key=lambda x: x[1], reverse=True)[:10]
    medailles = ["🥇", "🥈", "🥉"] + ["🔹"] * 7

    embed = discord.Embed(title="🏆 Top 10 — Hall of Fame", color=discord.Color.gold())
    description = ""
    for i, (user_id, votes) in enumerate(classement):
        membre = ctx.guild.get_member(int(user_id))
        nom = membre.display_name if membre else "Membre inconnu"
        description += f"{medailles[i]} **{nom}** — `{votes}` vote{'s' if votes > 1 else ''}\n"

    embed.description = description
    await ctx.send(embed=embed)


@bot.command(name="mafame")
async def mafame(ctx):
    """Affiche ton score de fame personnel."""
    data = load_data()
    user_id = str(ctx.author.id)
    votes = data["votes"].get(user_id, 0)
    a_vote = user_id in data["voters"]

    embed = discord.Embed(title=f"⭐ Fame de {ctx.author.display_name}", color=discord.Color.gold())
    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.add_field(name="⭐ Votes reçus", value=str(votes), inline=True)
    embed.add_field(name="🗳️ A voté ?", value="Oui" if a_vote else "Non", inline=True)
    await ctx.send(embed=embed)


@bot.command(name="resetfame")
@commands.has_permissions(administrator=True)
async def resetfame(ctx):
    data = {"votes": {}, "voters": {}, "vote_message_id": None, "duels": {}, "duel_voters": {}}
    save_data(data)
    await ctx.send("🔄 Les votes ont été remis à zéro !")


@bot.command(name="fameaide")
async def fameaide(ctx):
    embed = discord.Embed(title="📖 Aide — Bot Fame & Duel", color=discord.Color.blurple())
    embed.add_field(name="⚔️ !duel @user1 @user2", value="Lance un duel entre 2 membres", inline=False)
    embed.add_field(name="🏆 !resultat @user1 @user2", value="Affiche le résultat d'un duel", inline=False)
    embed.add_field(name="⭐ !nomine @user", value="Crée un vote de fame *(modo)*", inline=False)
    embed.add_field(name="📊 !top", value="Top 10 Hall of Fame", inline=False)
    embed.add_field(name="👤 !mafame", value="Ton score de fame", inline=False)
    embed.add_field(name="🔄 !resetfame", value="Remet les votes à 0 *(admin)*", inline=False)
    await ctx.send(embed=embed)


# ─────────────────────────────────────────
#  LANCEMENT
# ─────────────────────────────────────────
bot.run(TOKEN)
