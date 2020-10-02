import asyncio
import traceback

import pandas as pd

from time import strftime, localtime
import discord
import requests
from bs4 import BeautifulSoup
from discord.ext.commands import Bot

SITE = "RETRACTED"  # Site pointing to tournament (Base URL with /)
TOKEN = "RETRACTED"  # Discord token
INTERVAL = 3600  # How often to check the site for tournaments
AMOUNT_DISPLAY = 10  # How much of the leaderboard to display in the embed
ADMIN = ["SOMENAME#1234"]  # Discord members who's allowed to make announcements
CHECK_DIRS = ["SUBDIR"]


# Helper functions
def updateAnnounceChannels():
    announceChannels.clear()

    # Fetching announce channels
    guilds = bot.guilds
    for channel in bot.get_all_channels():
        if "tournament" == str(channel.name) and channel.permissions_for(channel.guild.me).send_messages:
            announceChannels.append(channel)
            guilds.remove(channel.guild)

    # If someone fails to make a correct channel, just announce to the system channel
    for guild in guilds:
        channel = getDefaultChannel(guild)

        if channel is not None:
            announceChannels.append(channel)


def fetchTournaments(page):
    soup = BeautifulSoup(page.content, 'html.parser')
    aList = list(soup.findAll('a'))
    return list(filter(lambda x: ("result" in str(x.string).lower()), aList))


def fetchAllTournaments():
    allTournaments = []
    for dire in CHECK_DIRS:
        dirTournaments = fetchTournaments(requests.get(SITE + dire + "/"))

        for dirTournament in dirTournaments:
            allTournaments.append((str(dirTournament.string).strip(), dire))

    return allTournaments


def fetchLeaderboard(page):
    return pd.read_html(page.text)[0]


def fetchConfiguration(page):
    soup = BeautifulSoup(page.content, 'html.parser')
    return list(soup.findAll('h2'))  # TODO don't hardcode this


def getDefaultChannel(guild):
    systemChannel = guild.system_channel
    if systemChannel is not None and systemChannel.permissions_for(guild.me):
        return systemChannel
    return None


async def pollAnnounce():
    # Bypass (for testing) prints latest one
    # tournaments.pop()

    latestTournaments = list(set(fetchAllTournaments()) - set(tournaments))

    tournamentDifference = len(latestTournaments)

    if tournamentDifference > 0:
        print(str(tournamentDifference) + " new tournament(s) found, announcing...")
        try:
            for tournament in latestTournaments:
                link = str(SITE + tournament[1] + "/" + tournament[0] + "/results.html")

                resultPage = requests.get(link)
                leaderboard = fetchLeaderboard(resultPage).head(AMOUNT_DISPLAY)
                configuration = fetchConfiguration(resultPage)

                embed = discord.Embed(
                    title=("Tournament (" + tournament[1] + ")"),
                    type="rich",
                    url=link,
                    description=("**"
                                 + configuration[2].text
                                 + "**\n```"
                                 + leaderboard.iloc[:, [0, 1, 2]].to_string(index=False)
                                 + "```\n"
                                 + str(configuration[1].contents[0]))
                )

                # Send message
                for announceChannel in announceChannels:
                    try:
                        await announceChannel.send(embed=embed)
                    except:
                        print("Error announcing to a channel")
                        print(traceback.print_exc())

            # Add tournaments to globally tracked
            tournaments.extend(latestTournaments)

        except:
            print("Error announcing")
            print(traceback.print_exc())


# Global variables
tournaments = fetchAllTournaments()
announceChannels = []

bot = Bot(command_prefix='?')


@bot.command()
async def forcepoll(ctx):
    print("Force polling requested by " + str(ctx.author))
    await ctx.send("Checking site for new tournaments...")
    await pollAnnounce()


@bot.command()
async def tracked(ctx):
    print("Command tracked, requested by " + str(ctx.author))
    await ctx.send("Currently holding  " + str(len(tournaments)) + " tournament(s) in memory")


@bot.command()
async def position(ctx, arg):
    print("position request from " + str(ctx.author))
    if len(tournaments) == 0:
        await ctx.send("No tournament found")
        return

    latestTournament = tournaments[-1]  # Will be funky if we restart bot TODO
    link = str(SITE + latestTournament[1] + "/" + latestTournament[0] + "/results.html")

    resultPage = requests.get(link)

    teamName = arg.lower()
    leaderboard = fetchLeaderboard(resultPage)
    tournamentInfo = latestTournament[1] + " (" + latestTournament[0] + ")"

    ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])

    teamPosition = None
    nearestStaffBelow = "Not above any staff teams :sad:"

    for index, row in leaderboard.iterrows():
        if teamName in str(row["Team"]).lower():
            teamPosition = row["Position"]
        else:
            if teamPosition is not None:
                if "staff_team" in str(row["Team"]).lower():
                    nearestStaffBelow = row["Team"]
                    break

    if teamPosition is not None:
        await ctx.send(str(teamName) + " is placed "
                       + "**" + str(ordinal(teamPosition)) + "**"
                       + " in "
                       + tournamentInfo
                       + ("\n[**Ranked above:** " + nearestStaffBelow + "]"))
    else:
        await ctx.send("Could not find the team specified in " + tournamentInfo)


@bot.command()
async def change(ctx, arg):
    print("position change request from " + str(ctx.author))
    if len(tournaments) <= 1:
        await ctx.send("Not enough tournament found for comparison")
        return

    latestTournament = tournaments[-1]  # Will be funky if we restart bot TODO
    previousTournament = tournaments[-2]

    linkLatest = str(SITE + latestTournament[1] + "/" + latestTournament[0] + "/results.html")
    linkPrevious = str(SITE + latestTournament[1] + "/" + previousTournament[0] + "/results.html")

    resultLatestPage = requests.get(linkLatest)
    resultPreviousPage = requests.get(linkPrevious)

    teamName = arg.lower()
    leaderboardLatest = fetchLeaderboard(resultLatestPage)
    leaderboardPrevious = fetchLeaderboard(resultPreviousPage)

    positionLatest = None
    positionPrevious = None

    for index, row in leaderboardLatest.iterrows():
        if teamName in str(row["Team"]).lower():
            positionLatest = int(row["Position"])

    for index, row in leaderboardPrevious.iterrows():
        if teamName in str(row["Team"]).lower():
            positionPrevious = int(row["Position"])

    if positionLatest is None or positionPrevious is None:
        await ctx.send("Could not find the team in both tournaments")

    ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])

    positionChange = positionPrevious - positionLatest

    await ctx.send(teamName + " was " + str(ordinal(positionPrevious)) + ", currently " + str(
        ordinal(positionLatest)) + " | Change: " + ("+" if positionChange > 0 else "") + str(positionChange))


@bot.command()
async def announce(ctx, *, arg):
    if str(ctx.author) not in ADMIN:
        await ctx.send("You are not permitted to make announcements")
        print("Unauthorised announce by " + str(ctx.author) + " with contents [" + str(arg) + "]")
        return
    print("Announcing [" + str(arg) + "] to all, requested by " + str(ctx.author))
    await ctx.send("Announced")

    # Announce it
    for channel in announceChannels:
        await channel.send(str(arg))


async def backgroundTask():
    while True:
        await bot.wait_until_ready()
        counter = 0

        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                            name="site (?help)"))

        updateAnnounceChannels()

        print('Connected with {0.user}'.format(bot))

        while not bot.is_closed():
            counter += 1

            # Check for tournament update
            print("Executing cycle(" + str(counter) + ") at [" + strftime("%d-%m-%Y- %H:%M %p", localtime()) + "] - "
                  + str(len(bot.guilds)) + " guilds and " + str(len(announceChannels)) + " channels")

            await pollAnnounce()

            print("Finished cycle(" + str(counter) + ")")
            await asyncio.sleep(INTERVAL)

        print("Client lost connection")


@bot.event
async def on_guild_join(guild):
    updateAnnounceChannels()


@bot.event
async def on_guild_remove(guild):
    updateAnnounceChannels()


@bot.event
async def on_guild_channel_update(before, after):
    updateAnnounceChannels()


@bot.event
async def on_guild_channel_delete(channel):
    updateAnnounceChannels()


@bot.event
async def on_guild_channel_create(channel):
    updateAnnounceChannels()


@bot.event
async def on_guild_role_update(before, after):
    updateAnnounceChannels()


# Loops
bot.loop.create_task(backgroundTask())

# Start
bot.run(TOKEN)
