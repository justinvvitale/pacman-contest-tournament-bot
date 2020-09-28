import asyncio
import traceback

import pandas as pd

from time import strftime, localtime
import discord
import requests
from bs4 import BeautifulSoup

SITE = "RETRACTED"  # Site pointing to tournament (Base URL)
TOKEN = "RETRACTED"  # Discord token
INTERVAL = 3600  # How often to check the site for tournaments
AMOUNT_DISPLAY = 10  # How much of the leaderboard to display in the embed


# Helper functions
def updateAnnounceChannels():
    announceChannels.clear()

    # Fetching announce channels
    for channel in client.get_all_channels():
        if "tournament" in str(channel.name) and channel.permissions_for(channel.guild.me).send_messages:
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


# Global variables
tournaments = fetchTournaments(requests.get(SITE))
announceChannels = []

client = discord.Client()


async def backgroundTask():
    while True:
        await client.wait_until_ready()
        counter = 0

        updateAnnounceChannels()

        print('Connected with {0.user}'.format(client))

        while not client.is_closed():
            counter += 1

            # Check for tournament update
            print("Executing cycle(" + str(counter) + ") at [" + strftime("%d-%m-%Y- %H:%M %p", localtime()) + "] - "
                  + str(len(client.guilds)) + " guilds and " + str(len(announceChannels)) + " channels")

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

            print("Finished cycle(" + str(counter) + ")")
            await asyncio.sleep(INTERVAL)

        print("Client lost connection")


@client.event
async def on_guild_join(guild):
    updateAnnounceChannels()


@client.event
async def on_guild_remove(guild):
    updateAnnounceChannels()


@client.event
async def on_guild_channel_update(before, after):
    updateAnnounceChannels()


@client.event
async def on_guild_channel_delete(channel):
    updateAnnounceChannels()


@client.event
async def on_guild_channel_create(channel):
    updateAnnounceChannels()


@client.event
async def on_guild_role_update(before, after):
    updateAnnounceChannels()


client.loop.create_task(backgroundTask())
client.run(TOKEN)
