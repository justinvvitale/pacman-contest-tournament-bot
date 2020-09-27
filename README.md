# pacman-contest-tournament-bot

A discord bot which will announce tournaments whenever they're published, in a clean and elegant fashion. 

(Designed for RMIT'S variation of the UC Berkeley contest)


## The "I DON'T WANT TO SET UP A BOT, GIMME"

There should be a post on piazza for an instance of the bot I am hosting (With instructions) 

## Configuration

Variables inside the script will have to be set, these include the 
* Discord bot token
* Site address (Pointing to the base URL)
* Checking interval (Don't abuse this, keep it reasonable)

## Usage

Create a channel named "tournament" and add the bot to your server. It (should) will announce any new tournaments.

## Libraries required
* Pandas
* bs4 (beautiful soup 4)
* discord.py
* asyncio
* lxml
* html5lib
* requests


## FYI

This will probably break at the first glimpse of any change, I am open to pull requests.
