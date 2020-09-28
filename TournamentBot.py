import asyncio
import traceback

import pandas as pd

from time import strftime, localtime
import discord
import requests
from bs4 import BeautifulSoup
from discord.ext.commands import Bot

SITE = "RETRACTED"  # Site pointing to tournament (Base URL)
TOKEN = "RETRACTED"  # Discord token
INTERVAL = 3600  # How often to check the site for tournaments
AMOUNT_DISPLAY = 10  # How much of the leaderboard to display in the embed
ADMIN = ["SOMENAME#1234"]  # Discord members who's allowed to make announcements


# Helper functions
def updateAnnounceChannels():
    announceChannels.clear()

    # Fetching announce channels
    guilds = bot.guilds
    for channel in bot.get_all_channels():
        if "tournament" in str(channel.name) and channel.permissions_for(channel.guild.me).send_messages:
            announceChannels.append(channel)
            guilds.remove(channel.guild)

    # If someone fails to make a correct channel, just announce to the system channel
    for guild in guilds:
        channel = getDefaultChannel(guild)

        if channel is not None:
            announceChannels.append(channel)


def fetchTournaments(page):
    soup = BeautifulSoup(page.content, 'html.parser')
    return list(soup.findAll('a'))


def fetchLeaderboard(page):
    dfList = pd.read_html(page.text)  # this parses all the tables in webpages to a df list
    leaderboardDF = dfList[0].head(AMOUNT_DISPLAY)
    return leaderboardDF


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

    latestTournaments = list(set(fetchTournaments(requests.get(SITE))) - set(tournaments))

    tournamentDifference = len(latestTournaments)

    if tournamentDifference > 0:
        print(str(tournamentDifference) + " new tournament(s) found, announcing...")
        try:
            for tournament in latestTournaments:
                link = str(SITE + tournament['href'])

                resultPage = requests.get(link)
                leaderboard = fetchLeaderboard(resultPage)
                configuration = fetchConfiguration(resultPage)

                embed = discord.Embed(
                    title=("Tournament (HISTORIC TEST) " + str(tournamentDifference + len(tournaments))),
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
                tournamentDifference -= 1

            # Add tournaments to globally tracked
            tournaments.extend(latestTournaments)

        except:
            print("Error announcing")
            print(traceback.print_exc())


# Global variables
tournaments = fetchTournaments(requests.get(SITE))
announceChannels = []

bot = Bot(command_prefix='@')


@bot.command()
async def commands(ctx):
    await ctx.send("**Tournament bot commands**\n"
                   "> forcepoll - Force a tournament check"
                   )


@bot.command()
async def forcepoll(ctx):
    print("Force polling requested by " + str(ctx.author))
    await ctx.send("Checking site for new tournaments...")
    await pollAnnounce()


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
                                                            name="for tournaments"))

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
