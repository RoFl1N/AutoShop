import disnake
from disnake.ext import commands
from disnake import TextInputStyle
from config import qiwi_token, admins_ids, logid, roleid, guildid, iconurl, supporturl
import sqlite3
import random
from pyqiwip2p import QiwiP2P
import asyncio

#подключение бд
db = sqlite3.connect("db")
cursor = db.cursor()

#создание нужных таблиц если ещё не созданы
cursor.execute("CREATE TABLE IF NOT EXISTS shop (id INT, name TEXT, price INT, tovar TEXT, status INT)")
cursor.execute("CREATE TABLE IF NOT EXISTS users (id BIGINT, shopping INT, balance INT)")
cursor.execute("CREATE TABLE IF NOT EXISTS checks (userid BIGINT, checkid VARCHAR, money INT)")
cursor.execute("CREATE TABLE IF NOT EXISTS promocode (pc TEXT, value INT, count INT, userid BIGINT)")

#подключение платёжной системы
p2p = QiwiP2P(auth_key=qiwi_token)

class ShopSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    #/start
    @commands.slash_command(description='Меню взаимодействий')
    async def start(self, inter):
        embed = disnake.Embed(title='Основное меню', description='Выберите категорию', color=disnake.Color.from_rgb(47,49,54))
        embed.set_thumbnail(url=iconurl) #Тут картинку поставить
        await inter.response.send_message(embed=embed, components=[
            disnake.ui.Button(label="Магазин", style=disnake.ButtonStyle.success, custom_id="bshop", emoji='🛍️'),
            disnake.ui.Button(label="Профиль", style=disnake.ButtonStyle.blurple, custom_id="bprofile", emoji='👥'),
            [disnake.ui.Button(label="Поддержка", style=disnake.ButtonStyle.primary, emoji='💤', url=supporturl)]
        ])

    #/ashop
    @commands.command()
    async def ashop(self, inter):
        if inter.author.id in admins_ids:
            prods = cursor.execute("SELECT id, name, price FROM shop WHERE status = 0").fetchall()
            embed = disnake.Embed(title='Управление Магазином', description='Товары: ', color=disnake.Color.from_rgb(47,49,54))
            for prod in prods:
                embed.add_field(name=prod[1], value=f'Цена: {prod[2]}₽ | ID: {prod[0]}', inline=False)
            await inter.send(embed=embed, components=[
                disnake.ui.Button(label="Добавить товар", style=disnake.ButtonStyle.success, custom_id="sadd"),
                disnake.ui.Button(label="Удалить товар", style=disnake.ButtonStyle.danger, custom_id="sremove"),
                [disnake.ui.Button(label="Добавить промокод", style=disnake.ButtonStyle.success, custom_id="baddpc"), 
                disnake.ui.Button(label="Выдать баланс", style=disnake.ButtonStyle.secondary, custom_id="setbal")]])
        else:
            await inter.send("Ух, ну я думаю тебе это использовать не стоит! \n Хочешь купить бота? - RoFliN#0939")

    #остлеживание ивентов выпадающего списка
    @commands.Cog.listener()
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        tovar = cursor.execute(f"SELECT id, price, tovar FROM shop WHERE name = '{inter.values[0]}' AND status = 0").fetchone()
        if tovar:
            user = cursor.execute(f"SELECT balance, shopping FROM users WHERE id = {inter.author.id}").fetchone()
            if user:
                if user[0] >= tovar[1]:
                    embed = disnake.Embed(title='Вы точно хотите купить?', description=f'{inter.values[0]} за {tovar[1]}₽ \n У вас есть 1 минута на решение!', color=disnake.Color.from_rgb(47,49,54))
                    embed.set_footer(text='Проигнорируйте это сообщение если передумали')
                    await inter.response.send_message(embed=embed, components=[
                        disnake.ui.Button(label='Подтвердить', style=disnake.ButtonStyle.success, custom_id='accept', emoji='✅')
                    ], ephemeral=True)
                    try:
                        cursor.execute(f"UPDATE shop SET status = 1 WHERE id = {tovar[0]}")
                        db.commit()
                        interb = await self.bot.wait_for('button_click', timeout=60)
                        balance = user[0] - tovar[1]
                        shopi = user[1] + 1
                        cursor.execute(f"UPDATE users SET balance = {balance}, shopping = {shopi} WHERE id = {inter.author.id}")
                        cursor.execute(f"DELETE FROM shop WHERE id = {tovar[0]}")
                        db.commit()
                        await interb.send(tovar[2], ephemeral=True)
                        log_channel = await self.bot.fetch_channel(logid)
                        embed = disnake.Embed(title="Новая покупка", description=f"Покупатель: <@{inter.author.id}> \nТовар: {inter.values[0]}", color=disnake.Color.from_rgb(47,49,54))
                        await log_channel.send(embed=embed)
                        guild = await self.bot.fetch_guild(guildid)
                        role = guild.get_role(roleid)
                        print(role, guild)
                        await inter.author.add_roles(role)
                    except:
                        cursor.execute(f"UPDATE shop SET status = 0 WHERE id = {tovar[0]}")
                        db.commit()
                        return
                else:
                    await inter.response.send_message('Вам нехватает денег, пополните счёт! | /start > профиль > пополнить', ephemeral=True) 
            else:
                cursor.execute(f"INSERT INTO users (id, shopping, balance) VALUES ({inter.author.id}, 0, 0)")
                db.commit()
                await inter.response.send_message('Вам нехватает денег, пополните счёт! | /start > профиль > пополнить', ephemeral=True) 
        else:
            await inter.response.send_message('Товар уже продан.', ephemeral=True)

    #остлеживание ивентов кнопок
    @commands.Cog.listener("on_button_click")
    async def menu_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "bshop":
            try:
                prods = cursor.execute("SELECT id, name, price FROM shop WHERE status = 0").fetchall()
                embed = disnake.Embed(title='Магазин', description='Доступные товары', color=disnake.Color.from_rgb(47,49,54))
                names = []
                for prod in prods:
                    names.append(prod[1])
                dev = []
                options = []
                for prod in prods:
                    if names.count(f"{prod[1]}") > 1:
                        embed.add_field(name=prod[1], value=f'Цена: {prod[2]}₽ | Кол-во: {names.count(f"{prod[1]}")}', inline=False)
                        options.append(disnake.SelectOption(
                            label=prod[1], description=f"Цена: {prod[2]}₽ | Кол-во: {names.count(f'{prod[1]}')}", emoji='🛒'))
                        for i in range(names.count(f"{prod[1]}")):
                            names.remove(prod[1])
                        dev.append(prod[1])
                    else:
                        if prod[1] in dev:
                            pass
                        else:
                            embed.add_field(name=prod[1], value=f'Цена: {prod[2]}₽ | Кол-во: 1', inline=False)
                            options.append(disnake.SelectOption(
                            label=prod[1], description=f"Цена: {prod[2]}₽ | Кол-во: 1", emoji='🛒'))
                await inter.response.send_message(embed=embed, ephemeral=True, components=[disnake.ui.Select(placeholder='Выберите товар', min_values=1, max_values=1, options=options)])
            except:
              await inter.response.send_message(embed=embed, ephemeral=True)

        if inter.component.custom_id == 'baddpc':
            await inter.response.send_modal(title='Добавить промокод', custom_id='addpc', components=[
                disnake.ui.TextInput(
                    label="Промокод",
                    placeholder="PROMOCODE",
                    custom_id="pc",
                    style=TextInputStyle.short
                ),
                disnake.ui.TextInput(
                    label="Проценты",
                    placeholder="000",
                    custom_id="pcval",
                    style=TextInputStyle.short
                ),
                disnake.ui.TextInput(
                    label="Кол-во использований",
                    placeholder="10",
                    custom_id="pcount",
                    style=TextInputStyle.short
                )
            ])

        if inter.component.custom_id == 'bprofile':
            user = cursor.execute(f"SELECT shopping, balance FROM users WHERE id = {inter.author.id}").fetchone()
            if not user:
                cursor.execute(f"INSERT INTO users (id, shopping, balance) VALUES ({inter.author.id}, 0, 0)")
                db.commit()
                user = cursor.execute(f"SELECT shopping, balance FROM users WHERE id = {inter.author.id}").fetchone()
            embed = disnake.Embed(title=f'Профиль - {inter.author}', description=f'\n **Баланс: {user[1]}₽** \n**Куплено товаров: {user[0]}**', color=disnake.Color.from_rgb(47,49,54))
            embed.set_thumbnail(url=inter.author.avatar.url)
            await inter.response.send_message(embed=embed, ephemeral=True, components=[
                disnake.ui.Button(label="Пополнить баланс", style=disnake.ButtonStyle.success, custom_id="addbal")
            ])

        if inter.component.custom_id == 'addbal':
            await inter.response.send_modal(title='Пополнить баланс', custom_id='gencheck', components=[
                disnake.ui.TextInput(
                    label="Сумма",
                    placeholder="Только целые числа!",
                    required=True,
                    custom_id="summa",
                    style=TextInputStyle.short
                ),
                disnake.ui.TextInput(
                    label="Промокод",
                    placeholder="Необязательно",
                    custom_id="promocode",
                    required=False,
                    style=TextInputStyle.short
                )
            ])
        if inter.component.custom_id == "sadd":
            await inter.response.send_modal(title='Добавить Товар', custom_id='addprod', components = [
                disnake.ui.TextInput(
                    label="Название",
                    placeholder="Название товара",
                    custom_id="name",
                    style=TextInputStyle.short,
                ),
                disnake.ui.TextInput(
                    label="Содержимое",
                    placeholder="Содержимое товара",
                    custom_id="tovar",
                    style=TextInputStyle.paragraph,
                ),
                disnake.ui.TextInput(
                    label="Цена",
                    placeholder="Цена товара",
                    custom_id="price",
                    style=TextInputStyle.short,
                ),
            ])
        if inter.component.custom_id == "sremove":
            await inter.response.send_modal(title='Удалить товар', custom_id='removeprod', components = [
                disnake.ui.TextInput(
                    label="ID",
                    placeholder="ID Товара",
                    custom_id="id",
                    style=TextInputStyle.short,
                )
            ])
        if inter.component.custom_id == "setbal":
            await inter.response.send_modal(title="Выдать баланс", custom_id="msetbal", components=[
                disnake.ui.TextInput(
                    label="Айди участника",
                    placeholder="000000000000000",
                    custom_id="userid",
                    style=TextInputStyle.short,
                ),
                                disnake.ui.TextInput(
                    label="Количество денег",
                    placeholder="00000",
                    custom_id="amount",
                    style=TextInputStyle.short,
                )
            ])

    #отслеживание ивентов модальных окон
    @commands.Cog.listener()
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        if inter.custom_id == "addpc":
            cursor.execute(f"INSERT INTO promocode (pc, value, count, userid) VALUES ('{inter.text_values['pc']}', {inter.text_values['pcval']}, {inter.text_values['pcount']}, {inter.author.id})")
            db.commit()
            await inter.response.send_message(f"Добавлен промокод: {inter.text_values['pc']}")

        if inter.custom_id == "addprod":
            cursor.execute(f"INSERT INTO shop (id, name, price, tovar, status) VALUES ({random.randint(0, 999999)}, '{inter.text_values['name']}', {inter.text_values['price']}, '{inter.text_values['tovar']}', 0)")
            db.commit()
            await inter.response.send_message(f"Добавлен новый товар: {inter.text_values['name']}", ephemeral=True)
        if inter.custom_id == "removeprod":
            cursor.execute(f"DELETE FROM shop WHERE id = {inter.text_values['id']}")
            db.commit()
            await inter.response.send_message("Удалено", ephemeral=True)

        if inter.custom_id == "msetbal":
            try:
                bal = cursor.execute(f"SELECT balance FROM users WHERE id = {int(inter.text_values['userid'])}").fetchone()
                fullbal = int(bal[0]) + int(inter.text_values['amount'])
                cursor.execute(f"UPDATE users SET balance = {fullbal} WHERE id = {inter.text_values['userid']}")
                await inter.response.send_message(f"Выдал юзеру <@{inter.text_values['userid']}> {inter.text_values['amount']}Р")
                log_channel = await self.bot.fetch_channel(logid)
                embed = disnake.Embed(title="Выдан баланс", description=f"Пользователь: <@{inter.text_values['userid']}> \nСумма: {inter.text_values['amount']}₽ \n Админ: {inter.author.mention}", color=disnake.Color.from_rgb(47,49,54))
                await log_channel.send(embed=embed)
            except:
                await inter.response.send_message(f"Похоже юзера нету в бд и он ещё не использовал бота")
        
        if inter.custom_id == "gencheck":
            try:
                summa = int(inter.text_values['summa'])
                summaop = int(inter.text_values['summa'])
                if inter.text_values['promocode'] != '':
                    pc = cursor.execute(f"SELECT value, count FROM promocode WHERE pc = '{inter.text_values['promocode']}'").fetchone()
                    if pc and pc[1] >= 1:
                        bonus = summa * pc[0] / 100
                        summa = int(round(summa + bonus))
                        pcount = pc[1] - 1
                        if pcount <= 0:
                            cursor.execute(f"DELETE FROM promocode WHERE pc = '{inter.text_values['promocode']}'")
                            db.commit()
                        else:
                            cursor.execute(f"UPDATE promocode SET count = {pcount} WHERE pc = '{inter.text_values['promocode']}'")
                            db.commit()
                    else:
                        pass

                comment = f'{inter.author.id}_{random.randint(10000, 99999)}'
                bill = p2p.bill(amount=summaop, lifetime=2, comment=comment)
                cursor.execute(f"INSERT INTO checks (userid, checkid, money) VALUES ({inter.author.id}, '{bill.bill_id}', {summa})")
                db.commit()
                embed = disnake.Embed(title='Оплата счёта', description=f'**Оплатите:** {summaop}₽ \n **Получите:** {summa}₽', color=disnake.Color.from_rgb(47,49,54))
                await inter.response.send_message(embed=embed, ephemeral=True, components=[
                    disnake.ui.Button(label='Оплатить', style=disnake.ButtonStyle.success, url=bill.pay_url)
                ])
            except:
                await inter.response.send_message("Ишак тупой вводи только целые числа в сумму! >:(")

#проверка платежей каждую минуту
async def checkoplata(bot):
    while True:
        await asyncio.sleep(30)
        oplats = cursor.execute("SELECT userid, checkid, money FROM checks").fetchall()
        for oplata in oplats:
            if str(p2p.check(bill_id=oplata[1]).status) == "PAID":
                user = cursor.execute(f"SELECT balance FROM users WHERE id = {oplata[0]}").fetchone()
                newbal = int(user[0]) + int(oplata[2])
                cursor.execute(f"UPDATE users SET balance = {newbal} WHERE id = {oplata[0]}")
                cursor.execute(f"DELETE FROM checks WHERE checkid = '{oplata[1]}'")
                db.commit()
                log_channel = await bot.fetch_channel(logid)
                member = await bot.fetch_user(int(oplata[0]))
                await member.send(f"Ваш баланс пополнен на {oplata[2]} Рублей!")
                embed = disnake.Embed(title="Пополнен баланс", description=f"Пользователь: <@{oplata[0]}> \nСумма: {oplata[2]}", color=disnake.Color.from_rgb(47,49,54))
                await log_channel.send(embed=embed)
            elif str(p2p.check(bill_id=oplata[1]).status) == "EXPIRED":
                cursor.execute(f"DELETE FROM checks WHERE checkid = '{oplata[1]}'")
                db.commit()
 
def setup(bot: commands.Bot):
    bot.add_cog(ShopSystem(bot))
    bot.loop.create_task(checkoplata(bot))
