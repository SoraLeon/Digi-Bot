import asyncio
import random
import re
import sys
import time
import traceback
from datetime import timedelta, datetime

import discord
import psutil
from discord.ext import commands

from config import *
from utils import checks
from utils.database import init_database, userDatabase, reload_welcome_messages, welcome_messages, reload_announce_channels
from utils.discord import get_member, send_log_message, get_region_string, get_channel_by_name, get_user_servers, clean_string, get_role_list, get_member_by_name
", get_announce_channel, get_user_worlds"
from utils.general import command_list, join_list, get_uptime, TimeString, single_line, is_numeric, getLogin, start_time, global_online_list
from utils.general import log
from utils.help_format import NabHelpFormat
from utils.messages import decode_emoji, deathmessages_player, deathmessages_monster, EMOJI, levelmessages, weighedChoice, formatMessage

description = '''Missão: Destruir o macaco mijão'''
bot = commands.Bot(command_prefix=["/"], description=description, pm_help=True, formatter=NabHelpFormat())
# We remove the default help command so we can override it
bot.remove_command("help")   

@bot.event
async def on_ready():
    bot.load_extension("rh_pobre")
    bot.load_extension("mod")
    bot.load_extension("owner")
    bot.load_extension("admin")
    print('Logado como')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

    # Populate command_list
    for command_name, command in bot.commands.items():
        command_list.append(command_name)

    # Background tasks
    bot.loop.create_task(check_members())
    bot.loop.create_task(check_ghosts())     

@bot.event
@asyncio.coroutine
def on_command(command, ctx):
    """Chamado toda vez que um comando é utilizado. Usado para armazenar logs dos comandos em um arquivo."""
    if ctx.message.channel.is_private:
        destination = 'PM'
    else:
        destination = '#{0.channel.name} ({0.server.name})'.format(ctx.message)
    message_decoded = decode_emoji(ctx.message.content)
    log.info('Command by {0} in {1}: {2}'.format(ctx.message.author.display_name, destination, message_decoded))


@bot.event
@asyncio.coroutine
def on_command_error(error, ctx):
    if isinstance(error, commands.errors.CommandNotFound):
        return
    elif isinstance(error, commands.NoPrivateMessage):
        yield from bot.send_message(ctx.message.author, "Este comando não pode ser usado em mensagens privadas.")
    elif isinstance(error, commands.CommandInvokeError):
        print('In {0.command.qualified_name}:'.format(ctx), file=sys.stderr)
        traceback.print_tb(error.original.__traceback__)
        print('{0.__class__.__name__}: {0}'.format(error.original), file=sys.stderr)
        # Bot returns error message on discord if an owner called the command
        if ctx.message.author.id in owner_ids:
            yield from bot.send_message(ctx.message.channel, '```Py\n{0.__class__.__name__}: {0}```'.format(error.original))


@bot.event
@asyncio.coroutine
def on_message(message):
    """Chamado toda vez que uma mensagem é enviada para um canal visível.

    É usado para tornar os comandos case insensitive."""    
    # Ignore if message is from any bot
    if message.author.bot:
        return

    split = message.content.split(" ", 1)
    if split[0][:1] == "/" and split[0].lower()[1:] in command_list:
        if len(split) > 1:
            message.content = split[0].lower()+" "+split[1]
        else:
            message.content = message.content.lower()
    if len(split) == 2:
        if message.author.id != bot.user.id and (not split[0].lower()[1:] in command_list or not split[0][:1] == "/")\
                and not message.channel.is_private and message.channel.name == ask_channel_name:
            yield from bot.delete_message(message)
            return
    elif ask_channel_delete:
        # Delete messages in askchannel
        if message.author.id != bot.user.id \
                and (not message.content.lower()[1:] in command_list or not message.content[:1] == "/") \
                and not message.channel.is_private \
                and message.channel.name == ask_channel_name:
            yield from bot.delete_message(message)
            return
    yield from bot.process_commands(message)

    # Salva no banco a data da ultima mensagem deste usuario quando enviada de um canal no servidor
    if not message.channel.is_private:
        update_ghost(message.author)


@bot.event
@asyncio.coroutine
def on_server_join(server: discord.Server):
    log.info("Monkey Slave added to server: {0.name} (ID: {0.id})".format(server))
    message = "Opa! Estou agora em **{0.name}**. Para ver meus comandos disponíveis, digite \help\n" \
              "Eu responderei à comandos de qualquer canal que eu puder ver, mas se você criar um canal chamado *{1}*, eu poderei " \
              "dar respostas mais longas e mais informações lá.\n" \
              "Se você quiser um canal com os logs, crie um canal chamado *{2}* e eu colocarei os logs lá. Acredito " \
              "que você irá querer tornar este canal privado, é claro."
    formatted_message = message.format(server, ask_channel_name, log_channel_name)
    yield from bot.send_message(server.owner, formatted_message)


@bot.event
@asyncio.coroutine
def on_member_join(member: discord.Member):
    """Chamado toda vez que um membro entra em um servidor visível ao bot."""
    log.info("{0.display_name} (ID: {0.id}) joined {0.server.name}".format(member))
    if lite_mode:
        return
    server_id = member.server.id
    server_welcome = welcome_messages.get(server_id, "")
    pm = (welcome_pm+"\n"+server_welcome).format(member, bot)
    log_message = "{0.mention} joined.".format(member)

    # Atualiza o status de ghost do membro
    update_ghost(member)  

    # Coloca o membro na role "visitantes"
    roleName = 'visitante'
    for role in get_role_list(member.server):
        if role.name.lower() == roleName:
            yield from bot.add_roles(member, role)
            log.info("{0.display_name} (ID: {0.id}) added to role {1.name}".format(member, role))

    yield from send_log_message(bot, member.server, log_message)
    yield from bot.send_message(member, pm)
    yield from bot.send_message(member.server, "Ei, {0.mention}, bem vindo. E nada de cobranças aqui!".format(member))


@bot.event
@asyncio.coroutine
def on_member_remove(member: discord.Member):
    """Chamado sempre que um membro deixa o servidor ou é kickado do mesmo."""
    log.info("{0.display_name} (ID:{0.id}) left or was kicked from {0.server.name}".format(member))
    yield from send_log_message(bot, member.server, "**{0.name}#{0.discriminator}** left or was kicked.".format(member))


@bot.event
@asyncio.coroutine
def on_member_ban(member: discord.Member):
    """Chamado sempre que um membro é banido de um servidor."""
    log.warning("{0.display_name} (ID:{0.id}) was banned from {0.server.name}".format(member))
    yield from send_log_message(bot, member.server, "**{0.name}#{0.discriminator}** was banned.".format(member))


@bot.event
@asyncio.coroutine
def on_member_unban(server: discord.Server, user: discord.User):
    """Chamado sempre que um membro é desbanido de um servidor."""
    log.warning("{1.name} (ID:{1.id}) was unbanned from {0.name}".format(server, user))
    yield from send_log_message(bot, server, "**{0.name}#{0.discriminator}** was unbanned.".format(user))


@bot.event
@asyncio.coroutine
def on_message_delete(message: discord.Message):
    """Chamado sempre que uma mensagem for deletada."""
    if message.channel.name == ask_channel_name:
        return

    message_decoded = decode_emoji(message.clean_content)
    attachment = ""
    if message.attachments:
        attachment = "\n\tAttached file: "+message.attachments[0]['filename']
    log.info("A message by @{0} was deleted in #{2} ({3}):\n\t'{1}'{4}".format(message.author.display_name,
                                                                               message_decoded, message.channel.name,
                                                                               message.server.name, attachment))


@bot.event
@asyncio.coroutine
def on_message_edit(before: discord.Message, after: discord.Message):
    """Chamado sempre que uma mensagem é editada."""
    if before.channel.is_private:
        return
    if before.author.id == bot.user.id:
        return
    if before.content == after.content:
        return
    before_decoded = decode_emoji(before.clean_content)
    after_decoded = decode_emoji(after.clean_content)

    log.info("@{0} edited a message in #{3} ({4}):\n\t'{1}'\n\t'{2}'".format(before.author.name, before_decoded,
                                                                                 after_decoded, before.channel,
                                                                                 before.server))

@bot.event
@asyncio.coroutine
def on_member_update(before: discord.Member, after: discord.Member):
    """Chamado sempre que o membro é alterado."""
    if before.nick != after.nick:
        reply = "{1.mention}: Nickname changed from **{0.nick}** to **{1.nick}**".format(before, after)
        yield from send_log_message(bot, after.server, reply)
    elif before.name != after.name:
        reply = "{1.mention}: Name changed from **{0.name}** to **{1.name}**".format(before, after)
        yield from send_log_message(bot, after.server, reply)
    return

@bot.event
@asyncio.coroutine
def on_server_update(before: discord.Server, after: discord.Server):
    """Chamado sempre que o servidor é alterado"""
    if before.name != after.name:
        reply = "Server name changed from **{0.name}** to **{1.name}**".format(before, after)
        yield from send_log_message(bot, after, reply)
    elif before.region != after.region:
        reply = "Server region changed from {0} to {1}".format(get_region_string(before.region),
                                                               get_region_string(after.region))
        yield from send_log_message(bot, after, reply)    

# Bot commands
@bot.command(pass_context=True, aliases=["commands"])
@asyncio.coroutine
def help(ctx, *commands: str):
    """Mostra esta mensagem."""
    _mentions_transforms = {
        '@everyone': '@\u200beveryone',
        '@here': '@\u200bhere'
    }
    _mention_pattern = re.compile('|'.join(_mentions_transforms.keys()))

    bot = ctx.bot
    destination = ctx.message.channel if ctx.message.channel.name == ask_channel_name else ctx.message.author

    def repl(obj):
        return _mentions_transforms.get(obj.group(0), '')

    # help by itself just lists our own commands.
    if len(commands) == 0:
        pages = bot.formatter.format_help_for(ctx, bot)
    elif len(commands) == 1:
        # try to see if it is a cog name
        name = _mention_pattern.sub(repl, commands[0])
        command = None
        if name in bot.cogs:
            command = bot.cogs[name]
        else:
            command = bot.commands.get(name)
            if command is None:
                yield from bot.send_message(destination, bot.command_not_found.format(name))
                return
            destination = ctx.message.channel if command.no_pm else destination

        pages = bot.formatter.format_help_for(ctx, command)
    else:
        name = _mention_pattern.sub(repl, commands[0])
        command = bot.commands.get(name)
        if command is None:
            yield from bot.send_message(destination, bot.command_not_found.format(name))
            return

        for key in commands[1:]:
            try:
                key = _mention_pattern.sub(repl, key)
                command = command.commands.get(key)
                if command is None:
                    yield from bot.send_message(destination, bot.command_not_found.format(key))
                    return
            except AttributeError:
                yield from bot.send_message(destination, bot.command_has_no_subcommands.format(command, key))
                return

        pages = bot.formatter.format_help_for(ctx, command)

    for page in pages:
        yield from bot.send_message(destination, page)

@bot.command()
@asyncio.coroutine
def regras():
    """Mostra as regras do servidor"""
    embed = discord.Embed(title="Regras", description=regras_pm)
    yield from bot.say(embed=embed) 

@bot.command()
@asyncio.coroutine
def uptime():
    """Mostra a quanto tempo o bot está rodando"""
    yield from bot.say("Estou rodando por {0}.".format(get_uptime(True)))

@bot.command(pass_context=True)
@asyncio.coroutine
def about(ctx):
    """Mostra informações do bot"""
    permissions = ctx.message.channel.permissions_for(get_member(bot, bot.user.id, ctx.message.server))
    if not permissions.embed_links:
        yield from bot.say("Foi mal, eu preciso de permissões de `Embed Links` para executar este comando.")
        return

    embed = discord.Embed(description="*SCRIPTS SCRIPTS SCRIPTS*. Eu vou cobrar todo mundo!")
    embed.set_author(name="Monkey Slave", url="https://github.com/rodrigokiller/MonkeyBot",
                     icon_url="https://assets-cdn.github.com/favicon.ico")
    embed.add_field(name="Autor", value="@Killer#9093")
    embed.add_field(name="Plataforma", value="Python " + EMOJI[":snake:"])
    embed.add_field(name="Criado", value="July 01th 2017")
    embed.add_field(name="Servidores", value="{0:,}".format(len(bot.servers)))
    embed.add_field(name="Membros", value="{0:,}".format(len(set(bot.get_all_members()))))
    embed.add_field(name="Tempo", value=get_uptime())
    memory_usage = psutil.Process().memory_full_info().uss / 1024 ** 2
    embed.add_field(name='Uso de Memória', value='{:.2f} MiB'.format(memory_usage))
    yield from bot.say(embed=embed)        


@bot.command(pass_context=True, description='Para quando você precisa de um empurrãozinho pra decidir algo')
@asyncio.coroutine
def choose(ctx, *choices: str):
    """Realiza uma escolha entre múltiplas opções."""
    if choices is None:
        return
    user = ctx.message.author
    yield from bot.say('Elementar, caro **@{0}**, eu escolho: "{1}"'.format(user.display_name, random.choice(choices)))   

@bot.command(pass_context=True, description='Pra quando você precisa se comunciar com o famoso Sliter')
@asyncio.coroutine
def sliter(ctx, *mensagem: str):
    """Traduz para a linguagem Sliter."""
    if mensagem is None:
        return
    user = ctx.message.author
    phrase = ''
    for word in mensagem:   
        wordl = list(word) 
        for i in range(1, len(word), 2):
            if random.randint(0, 1):
                wordl[i-1], wordl[i] = wordl[i], wordl[i-1]
        phrase += ''.join(wordl) + ' '
    yield from bot.say(phrase)       

@bot.command(pass_context=True, no_pm=True, name="server", aliases=["serverinfo", "server_info"])
@asyncio.coroutine
def info_server(ctx):
    """Mostra informações do servidor."""
    permissions = ctx.message.channel.permissions_for(get_member(bot, bot.user.id, ctx.message.server))
    if not permissions.embed_links:
        yield from bot.say("Sorry, I need `Embed Links` permission for this command.")
        return
    embed = discord.Embed()
    _server = ctx.message.server  # type: discord.Server
    embed.set_thumbnail(url=_server.icon_url)
    embed.description = _server.name
    # Check if owner has a nickname
    if _server.owner.name == _server.owner.display_name:
        owner = "{0.name}#{0.discriminator}".format(_server.owner)
    else:
        owner = "{0.display_name}\n({0.name}#{0.discriminator})".format(_server.owner)
    embed.add_field(name="Dono", value=owner)
    embed.add_field(name="Criado", value=_server.created_at.strftime("%d/%m/%y"))
    embed.add_field(name="Região do Servidor", value=get_region_string(_server.region))

    # Channels
    text_channels = 0
    for channel in _server.channels:
        if channel.type == discord.ChannelType.text:
            text_channels += 1
    voice_channels = len(_server.channels) - text_channels
    embed.add_field(name="Canais de texto", value=text_channels)
    embed.add_field(name="Canais de voz", value=voice_channels)
    embed.add_field(name="Membros", value=_server.member_count)
    embed.add_field(name="Cargos", value=len(_server.roles))
    embed.add_field(name="Emojis", value=len(_server.emojis))
    embed.add_field(name="Bot entrou", value=_server.me.joined_at.strftime("%d/%m/%y"))
    yield from bot.say(embed=embed)


@bot.command(pass_context=True, no_pm=True)
@asyncio.coroutine
def roles(ctx, *userName:str):
    """Mostra uma lista de cargos ou os cargos de um usuário"""
    userName = " ".join(userName).strip()
    msg = "Estes são os cargos ativos para "

    if not userName:
        msg += "este servidor:\r\n"

        for role in get_role_list(ctx.message.server):
            msg += role.name + "\r\n"
    else:
        user = get_member_by_name(bot, userName)

        if user is None:
            msg = "Não consigo enxergar nenhum usuário chamado **" + userName + "**. \r\n"
            msg += "Eu só consigo verificar cargos de um usuário registrado neste servidor."
        else:
            msg += "**" + user.display_name + "**:\r\n"
            roles = []

            # Ignoring "default" roles
            for role in user.roles:
                if role.name not in ["@everyone", "Monkey Slave"]:
                    roles.append(role.name)

            # There shouldn't be anyone without active roles, but since people can check for NabBot,
            # might as well show a specific message.
            if roles:
                for roleName in roles:
                    msg += roleName + "\r\n"
            else:
                msg = "Não há nenhum cargo ativo para **" + user.display_name + "**."

    yield from bot.say(msg)
    return


@bot.command(pass_context=True, no_pm=True)
@asyncio.coroutine
def role(ctx, *roleName: str):
    """Mostra a lista de membros dentro do cargo especificado"""
    roleName = " ".join(roleName).strip()
    lowerRoleName = roleName.lower()
    roleDict = {}

    # Need to get all roles and check all members because there's
    # no API call like role.getMembers
    for role in get_role_list(ctx.message.server):
        if role.name.lower() == lowerRoleName:
            roleDict[role] = []

    if len(roleDict) > 0:
        # Check every member and add to dict for each role he is in
        # In this case, the dict will only have the specific role searched
        for member in ctx.message.server.members:
            for role in member.roles:
                if role in roleDict:
                    roleDict[role].append(member.display_name)
                    # Getting the name directly from server to respect case
                    roleName = role.name

        # Create return message
        msg = "Estes são os membros do cargo **" + roleName + "**:\r\n"

        for key, value in roleDict.items():
            if len(value) < 1:
                msg = "Não há membros neste cargo ainda."
            else:
                for memberName in roleDict[key]:
                    msg += "\t" + memberName + "\r\n"

        yield from bot.say(msg)
    else:
        yield from bot.say("Não pude encontrar um cargo com este nome.")

    return    

@asyncio.coroutine
def check_members():           
    game_list = ["Scripts", "DKC2", "Super OX World", "Need Ox Speed", "Mega Man OX 3", "Secret of Ox"]
    yield from bot.wait_until_ready()
    while not bot.is_closed:
        yield from bot.change_presence(game=discord.Game(name=random.choice(game_list)))
        yield from asyncio.sleep(60*20)  # Change game every 20 minutes    

def update_ghost(member):
    c = userDatabase.cursor()
    now = datetime.utcnow()
    try:
        c.execute("SELECT * FROM user_servers WHERE id = ? AND server = ?", (member.id, member.server.id,))
        result = c.fetchone()
        if result is not None:
            c.execute("""UPDATE user_servers SET last_message = ?, name = ? WHERE id = ? AND server = ?;""", (now, member.id, member.server.id, member.name))
        else:
            c.execute("""INSERT INTO user_servers (id, server, last_message, name) values (?, ?, ?, ?);""", (member.id, member.server.id, now, member.name))
    finally:        
        c.close()    
        userDatabase.commit()   

@asyncio.coroutine
def check_ghosts():           
    yield from bot.wait_until_ready()
    while not bot.is_closed:
        for server in bot.servers:
            for member in server.members:
                c = userDatabase.cursor()
                now = datetime.utcnow()
                try:
                    c.execute("SELECT * FROM user_servers WHERE id = ? AND server = ?", (member.id, member.server.id,))
                    result = c.fetchone()
                    if result is not None:
                        last_message = datetime.strptime(result["last_message"], "%Y-%m-%d %H:%M:%S.%f")                       
                        name = result["name"]                                                
                        diff = (now - last_message).total_seconds() / 60.0
                        if (diff/(24*60) > 7.0):
                            #yield from bot.send_message(member.server, "Simulando remoção de usuários: Usuário {0} será removido pois ficou {1} dia(s) sem escrever nada.".format(name, int(diff/(24*60))))                            
                            #yield from bot.send_message(member, "Você foi kickado do servidor {0} por ficar {1} dia(s) sem escrever nada. Saí daqui seu ghost!".format(member.server.name, int(diff/(24*60))))
                            for owners in owner_ids:
                                yield from bot.send_message(member.server.get_member(owners), "O usuário {0} foi kickado (simulação apenas) do servidor {1} por ficar {2} dia(s) sem escrever nada.".format(member.name, member.server.name, int(diff/(24*60))))
                            #yield from bot.kick(member)
                    else: # Não há registro deste usuário escrever algo mas ele está no servidor                        
                        c.execute("""INSERT INTO user_servers (id, server, last_message, name) values (?, ?, ?, ?);""", (member.id, member.server.id, now, member.name))
                finally:        
                    c.close()    
                    userDatabase.commit()   
        
        yield from asyncio.sleep(60*60)  # Verifica a cada uma hora (60 minutos)

if __name__ == "__main__":
    init_database()    
    reload_welcome_messages()
    reload_announce_channels()

    print("Tentativa de login...")

    login = getLogin()
    try:
        token = login.token
    except NameError:
        token = ""

    try:
        email = login.email
        password = login.password
    except NameError:
        email = ""
        password = ""
    try:
        if token:
            bot.run(token)
        elif email and password:
            bot.run(login.email, login.password)
        else:
            print("Dados de login não encontrados. Edite ou delete o arquivo login.py e reinicie.")
            input("\nAperte qualquer tecla para continuar...")
            quit()
    except discord.errors.LoginFailure:
        print("Dados de login incorretos. Edite ou delete login.py e reinicie.")
        input("\nAperte qualquer tecla para continuar...")
        quit()
    finally:
        bot.session.close()

    log.error("Monkey Slave crashed")                 