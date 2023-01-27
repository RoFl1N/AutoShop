import disnake
from disnake.ext import commands
from config import token

#В настройках бота на сайте включить все вкладки с INTENTS
intents = disnake.Intents.all()
bot = commands.Bot(command_prefix="s!", intents=intents, activity=disnake.Game(name="/start в ЛС"))

#список когов
cogs = ['shop']

#ивент готовности бота для подгрузок когов
@bot.event
async def on_ready():
    for cog in cogs:
        bot.load_extension(f"cogs.{cog}")
        print('[Log]: Бот запущен!')

#команда рестарт когов (s!reload)
@bot.command()
async def reload(inter):
    for cog in cogs:
        bot.reload_extension(f"cogs.{cog}")
        await inter.send('рестартнул коги')

#запуск бота
bot.run(token)
