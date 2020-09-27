import time

import pandas as pd

import discord
import requests
from bs4 import BeautifulSoup

SITE = "RETRACTED"  # Site pointing to tournament (Base URL)
TOKEN = "RETRACTED"  # Discord token
INTERVAL = 3600  # How often to check the site for tournaments
AMOUNT_DISPLAY = 10  # How much of the leaderboard to display in the embed


# Helper functions
def updateAnnounceChannels():
    # Fetching announce channels
    for channel in client.get_all_channels():
        if "tournament" in str(channel.name) and channel.permissions_for(channel.guild.me).send_messages:
            announceChannels.append(channel)


def fetchTournaments(page):
    soup = BeautifulSoup(page.content, 'html.parser')
    return soup.findAll('a')


def fetchLeaderboard(page):
    dfList = pd.read_html(page.text)  # this parses all the tables in webpages to a df list
    leaderboardDF = dfList[0].head(AMOUNT_DISPLAY)
    return leaderboardDF


def fetchConfiguration(page):
    soup = BeautifulSoup(page.content, 'html.parser')
    return soup.findAll('h2')  # TODO don't hardcode this


# Global variables
tournaments = fetchTournaments(requests.get(SITE))
announceChannels = []

client = discord.Client()


@client.event
async def on_ready():
    updateAnnounceChannels()

    # Check for tournament update
    while True:

        print("Executing check")

        latestTournaments = list(set(tournaments) - set(fetchTournaments(requests.get(SITE))))

        latestTournaments = [tournaments[0]]
        tournamentDifference = len(latestTournaments)

        if tournamentDifference > 0:
            print(str(len(latestTournaments)) + " new tournament(s) found")

            # Print notice
            print("Announcing to " + str(len(client.guilds)) + " guilds")

            link = str(SITE + tournaments[10]['href'])

            resultPage = requests.get(link)
            leaderboard = fetchLeaderboard(resultPage)
            configuration = fetchConfiguration(resultPage)

            for tournament in latestTournaments:
                embed = discord.Embed(
                    title=("Tournament " + str(tournamentDifference + len(tournament))),
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
                    await announceChannel.send(embed=embed)

        # Add tournaments to globally tracked
        tournaments.append(latestTournaments)

        # Rest easy
        time.sleep(INTERVAL)


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
async def on_guild_role_update(before, after):
    updateAnnounceChannels()


client.run(TOKEN)
