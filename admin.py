import asyncio
import re

import discord
from discord.ext import commands

from config import lite_mode, welcome_pm, ask_channel_name, log_channel_name, owner_ids, mod_ids
from utils import checks
from utils.database import *
from utils.discord import get_channel_by_name, get_member, get_server_by_name, get_user_admin_servers
from utils.general import is_numeric
from utils.messages import EMOJI

class Admin:
    """Commands for server owners and admins"""
    def __init__(self, bot: discord.Client):
        self.bot = bot

    @commands.command(pass_context=True)
    @checks.is_admin()
    @asyncio.coroutine
    def diagnose(self, ctx: discord.ext.commands.Context, *, server_name=None):
        """Diagnose the bots permissions and channels"""
        # This will always have at least one server, otherwise this command wouldn't pass the is_admin check.
        admin_servers = get_user_admin_servers(self.bot, ctx.message.author.id)

        if server_name is None:
            if not ctx.message.channel.is_private:
                if ctx.message.server not in admin_servers:
                    yield from self.bot.say("You don't have permissions to diagnose this server.")
                    return
                server = ctx.message.server
            else:
                if len(admin_servers) == 1:
                    server = admin_servers[0]
                else:
                    server_list = [str(i+1)+": "+admin_servers[i].name for i in range(len(admin_servers))]
                    yield from self.bot.say("Which server do you want to check?\n\t0: *Cancel*\n\t"+"\n\t".join(server_list))
                    answer = yield from self.bot.wait_for_message(timeout=60.0, author=ctx.message.author,
                                                                  channel=ctx.message.channel)
                    if answer is None:
                        yield from self.bot.say("I guess you changed your mind.")
                        return
                    elif is_numeric(answer.content):
                        answer = int(answer.content)
                        if answer == 0:
                            yield from self.bot.say("Changed your mind? Typical human.")
                            return
                        try:
                            server = admin_servers[answer-1]
                        except IndexError:
                            yield from self.bot.say("That wasn't in the choices, you ruined it. "
                                                    "Start from the beginning.")
                            return
                    else:
                        yield from self.bot.say("That's not a valid answer.")
                        return

        else:
            server = get_server_by_name(self.bot, server_name)
            if server is None:
                yield from self.bot.say("I couldn't find a server with that name.")
                return
            if server not in admin_servers:
                yield from self.bot.say("You don't have permissions to diagnose **{0}**.".format(server.name))
                return

        if server is None:
            return
        member = get_member(self.bot, self.bot.user.id, server)
        server_perms = member.server_permissions

        channels = server.channels
        not_read_messages = []
        not_send_messages = []
        not_manage_messages = []
        not_embed_links = []
        not_attach_files = []
        not_mention_everyone = []
        not_add_reactions = []
        not_read_history = []
        count = 0
        for channel in channels:
            if channel.type == discord.ChannelType.voice:
                continue
            count += 1
            channel_permissions = channel.permissions_for(member)
            if not channel_permissions.read_messages:
                not_read_messages.append(channel)
            if not channel_permissions.send_messages:
                not_send_messages.append(channel)
            if not channel_permissions.manage_messages:
                not_manage_messages.append(channel)
            if not channel_permissions.embed_links:
                not_embed_links.append(channel)
            if not channel_permissions.attach_files:
                not_attach_files.append(channel)
            if not channel_permissions.mention_everyone:
                not_mention_everyone.append(channel)
            if not channel_permissions.add_reactions:
                not_add_reactions.append(channel)
            if not channel_permissions.read_message_history:
                not_read_history.append(channel)

        channel_lists_list = [not_read_messages, not_send_messages, not_manage_messages, not_embed_links,
                              not_attach_files, not_mention_everyone, not_add_reactions, not_read_history]
        permission_names_list = ["Read Messages", "Send Messages", "Manage Messages", "Embed Links", "Attach Files",
                                 "Mention Everyone", "Add reactions", "Read Message History"]
        server_wide_list = [server_perms.read_messages, server_perms.send_messages, server_perms.manage_messages,
                            server_perms.embed_links, server_perms.attach_files, server_perms.mention_everyone,
                            server_perms.add_reactions, server_perms.read_message_history]

        answer = "Permissions for {0.name}:\n".format(server)
        i = 0
        while i < len(channel_lists_list):
            answer += "**{0}**\n\t{1} Server wide".format(permission_names_list[i], get_check_emoji(server_wide_list[i]))
            if len(channel_lists_list[i]) == 0:
                answer += "\n\t{0} All channels\n".format(get_check_emoji(True))
            elif len(channel_lists_list[i]) == count:
                answer += "\n\t All channels\n".format(get_check_emoji(False))
            else:
                channel_list = ["#" + x.name for x in channel_lists_list[i]]
                answer += "\n\t{0} Not in: {1}\n".format(get_check_emoji(False), ",".join(channel_list))
            i += 1

        ask_channel = get_channel_by_name(self.bot, ask_channel_name, server)
        answer += "\nAsk channel:\n\t"
        if ask_channel is not None:
            answer += "{0} Enabled: {1.mention}".format(get_check_emoji(True), ask_channel)
        else:
            answer += "{0} Not enabled".format(get_check_emoji(False))

        log_channel = get_channel_by_name(self.bot, log_channel_name, server)
        answer += "\nLog channel:\n\t"
        if log_channel is not None:
            answer += "{0} Enabled: {1.mention}".format(get_check_emoji(True), log_channel)
        else:
            answer += "{0} Not enabled".format(get_check_emoji(False))
        yield from self.bot.say(answer)
        return    

    @commands.command(name="setwelcome", pass_context=True)
    @checks.is_admin()
    @checks.is_not_lite()
    @asyncio.coroutine
    def set_welcome(self, ctx: commands.Context, *, message: str = None):
        """Changes the messages members get pmed when joining

        A part of the message is already fixed and cannot be changed, but the message can be extended

        Say "clear" to clear the current message.

        The following can be used to get dynamically replaced:
        {0.name} - The joining user's name
        {0.server.name} - The name of the server the user joined
        {0.server.owner.name} - The name of the owner of the server the member joined
        {0.server.owner.mention} - A mention to the owner of the server
        {1.user.name} - The name of the bot"""
        admin_servers = get_user_admin_servers(self.bot, ctx.message.author.id)

        if not ctx.message.channel.is_private:
            if ctx.message.server not in admin_servers:
                yield from self.bot.say("You don't have permissions to diagnose this server.")
                return
            server = ctx.message.server
        else:
            if len(admin_servers) == 1:
                server = admin_servers[0]
            else:
                server_list = [str(i + 1) + ": " + admin_servers[i].name for i in range(len(admin_servers))]
                yield from self.bot.say(
                    "For which server do you want to change the welcome message?\n\t0: *Cancel*\n\t" + "\n\t".join(
                        server_list))
                answer = yield from self.bot.wait_for_message(timeout=60.0, author=ctx.message.author,
                                                              channel=ctx.message.channel)
                if answer is None:
                    yield from self.bot.say("I guess you changed your mind.")
                    return
                elif is_numeric(answer.content):
                    answer = int(answer.content)
                    if answer == 0:
                        yield from self.bot.say("Changed your mind? Typical human.")
                        return
                    try:
                        server = admin_servers[answer - 1]
                    except IndexError:
                        yield from self.bot.say("That wasn't in the choices, you ruined it. "
                                                "Start from the beginning.")
                        return
                else:
                    yield from self.bot.say("That's not a valid answer.")
                    return
        server_id = server
        if message is None:
            current_message = welcome_messages.get(server_id, None)
            if current_message is None:
                current_message = welcome_pm.format(ctx.message.author, self.bot)
                yield from self.bot.say("This server has no custom message, joining members get the default message:\n"
                                        "----------\n{0}".format(current_message))
            else:
                current_message = (welcome_pm + "\n" + current_message).format(ctx.message.author, self.bot)
                yield from self.bot.say("This server has the following welcome message:\n"
                                        "----------\n``The first two lines can't be changed``\n{0}"
                                        .format(current_message))
            return
        if message.lower() in ["clear", "none", "delete", "remove"]:
            yield from self.bot.say("Are you sure you want to delete this server's welcome message? `yes/no`\n"
                                    "The default welcome message will still be shown.")
            reply = yield from self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel,
                                                         timeout=50.0)

            if reply is None:
                yield from self.bot.say("I guess you changed your mind...")
                return
            elif reply.content.lower() not in ["yes", "y"]:
                yield from self.bot.say("No changes were made then.")
                return
            c = userDatabase.cursor()
            try:
                c.execute("DELETE FROM server_properties WHERE server_id = ? AND name = 'welcome'", (server_id,))
            finally:
                c.close()
                userDatabase.commit()
            yield from self.bot.say("This server's welcome message was removed.")
            reload_welcome_messages()
            return

        if len(message) > 1200:
            yield from self.bot.say("This message exceeds the character limit! ({0}/{1}".format(len(message), 1200))
            return
        try:
            complete_message = (welcome_pm+"\n"+message).format(ctx.message.author, self.bot)
        except Exception as e:
            yield from self.bot.say("There is something wrong with your message.\n```{0}```".format(e))
            return

        yield from self.bot.say("Are you sure you want this as your private welcome message?\n"
                                "----------\n``The first two lines can't be changed``\n{0}"
                                .format(complete_message))
        reply = yield from self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel,
                                                     timeout=120.0)
        if reply is None:
            yield from self.bot.say("I guess you changed your mind...")
            return
        elif reply.content.lower() not in ["yes", "y"]:
            yield from self.bot.say("No changes were made then.")
            return

        c = userDatabase.cursor()
        try:
            # Safer to just delete old entry and add new one
            c.execute("DELETE FROM server_properties WHERE server_id = ? AND name = 'welcome'", (server_id,))
            c.execute("INSERT INTO server_properties(server_id, name, value) VALUES (?, 'welcome', ?)",
                      (server_id, message,))
            yield from self.bot.say("This server's welcome message has been changed successfully.")
        finally:
            c.close()
            userDatabase.commit()
            reload_welcome_messages()

    @commands.command(name="setchannel", pass_context=True)
    @checks.is_admin()
    @checks.is_not_lite()
    @asyncio.coroutine
    def set_announce_channel(self, ctx: commands.Context, *, name: str = None):
        """Changes the channel used for the bot's announcements

        If no channel is set, the bot will use the server's default channel."""
        admin_servers = get_user_admin_servers(self.bot, ctx.message.author.id)

        if not ctx.message.channel.is_private:
            if ctx.message.server not in admin_servers:
                yield from self.bot.say("You don't have permissions to diagnose this server.")
                return
            server = ctx.message.server
        else:
            if len(admin_servers) == 1:
                server = admin_servers[0]
            else:
                server_list = [str(i + 1) + ": " + admin_servers[i].name for i in range(len(admin_servers))]
                yield from self.bot.say(
                    "For which server do you want to change the announce channel?\n\t0: *Cancel*\n\t" + "\n\t".join(
                        server_list))
                answer = yield from self.bot.wait_for_message(timeout=60.0, author=ctx.message.author,
                                                              channel=ctx.message.channel)
                if answer is None:
                    yield from self.bot.say("I guess you changed your mind.")
                    return
                elif is_numeric(answer.content):
                    answer = int(answer.content)
                    if answer == 0:
                        yield from self.bot.say("Changed your mind? Typical human.")
                        return
                    try:
                        server = admin_servers[answer - 1]
                    except IndexError:
                        yield from self.bot.say("That wasn't in the choices, you ruined it. "
                                                "Start from the beginning.")
                        return
                else:
                    yield from self.bot.say("That's not a valid answer.")
                    return
        server_id = server.id
        if name is None:
            current_channel = announce_channels.get(server_id, None)
            if current_channel is None:
                yield from self.bot.say("This server has no custom channel set, {0} is used."
                                        .format(server.default_channel.mention))
            else:
                channel = get_channel_by_name(self.bot, current_channel, server)
                if channel is not None:
                    permissions = channel.permissions_for(get_member(self.bot, self.bot.user.id, server))
                    if not permissions.read_messages or not permissions.send_messages:
                        yield from self.bot.say("This server's announce channel is set to #**{0}** but I don't have "
                                                "permissions to use it. {1.mention} will be used instead."
                                                .format(current_channel, channel))
                        return
                    yield from self.bot.say("This server's announce channel is {0.mention}".format(channel))
                else:
                    yield from self.bot.say("This server's announce channel is set to #**{0}** but it doesn't exist. "
                                            "{1.mention} will be used instead."
                                            .format(current_channel, server.default_channel))
            return
        if name.lower() in ["clear", "none", "delete", "remove"]:
            yield from self.bot.say("Are you sure you want to delete this server's announce channel? `yes/no`\n"
                                    "The server's default channel ({0.mention}) will still be used."
                                    .format(server.default_channel))
            reply = yield from self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel,
                                                         timeout=50.0)

            if reply is None:
                yield from self.bot.say("I guess you changed your mind...")
                return
            elif reply.content.lower() not in ["yes", "y"]:
                yield from self.bot.say("No changes were made then.")
                return
            c = userDatabase.cursor()
            try:
                c.execute("DELETE FROM server_properties WHERE server_id = ? AND name = 'announce_channel'", (server_id,))
            finally:
                c.close()
                userDatabase.commit()
            yield from self.bot.say("This server's announce channel was removed.")
            reload_welcome_messages()
            return

        channel = get_channel_by_name(self.bot, name, server)
        if channel is None:
            yield from self.bot.say("There is no channel with that name.")
            return

        permissions = channel.permissions_for(get_member(self.bot, self.bot.user.id, server))
        if not permissions.read_messages or not permissions.send_messages:
            yield from self.bot.say("I don't have permission to use {0.mention}.".format(channel))
            return

        yield from self.bot.say("Are you sure you want {0.mention} as the announcement channel? `yes/no`"
                                .format(channel))
        reply = yield from self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel,
                                                     timeout=120.0)
        if reply is None:
            yield from self.bot.say("I guess you changed your mind...")
            return
        elif reply.content.lower() not in ["yes", "y"]:
            yield from self.bot.say("No changes were made then.")
            return

        c = userDatabase.cursor()
        try:
            # Safer to just delete old entry and add new one
            c.execute("DELETE FROM server_properties WHERE server_id = ? AND name = 'announce_channel'", (server_id,))
            c.execute("INSERT INTO server_properties(server_id, name, value) VALUES (?, 'announce_channel', ?)",
                      (server_id, channel.name,))
            yield from self.bot.say("This server's announcement channel was changed successfully.\nRemember that if "
                                    "the channel is renamed, you must set it again using this command.\nIf the channel "
                                    "becomes unavailable for me in any way, {0.mention} will be used."
                                    .format(server.default_channel))
        finally:
            c.close()
            userDatabase.commit()
            reload_announce_channels()

    @commands.command(name="kick", pass_context=True)
    @checks.is_admin()
    @checks.is_not_lite()
    @asyncio.coroutine
    def kick(self, ctx: commands.Context, *, message: str = None):
        """Remove um membro

        Se uma mensagem for passada logo após o @user, esta mensagem será encaminhada para o usuário em conversa privada."""
                
        # Verifica se está em conversa privada ou em um canal no servidor #
        if ctx.message.channel.is_private:
            yield from self.bot.say("Você não pode executar este comando aqui.")
            return                    
               
        # Verifica se tem permissão pra remover usuário #
        permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server)) 
        if not permissions.kick_members: 
            yield from self.bot.say("Não tenho permissão para remover usuários neste servidor.")
            return            

        server = ctx.message.server 
        split = ctx.message.clean_content.split(" ", 1)    
        split.pop(0)                   
        motivo = ''
        for i in split:
            motivo += i + ' '
        
        for member in ctx.message.mentions:
            # Busca maior role do membro
            member_pos = 0
            for role in member.roles:
                if role.position > member_pos:
                    member_pos = role.position

            # Busca mamior role do bot
            bot_pos = 0
            for role in server.get_member(self.bot.user.id).roles:
                if role.position > bot_pos:
                    bot_pos = role.position        

            # Verifica se a role do usuário é menor que a role do bot
            if member_pos > bot_pos:
                yield from self.bot.say("Não tenho permissão para remover o usuário {0} deste servidor.".format(member.name))
            # Verifica se o usuário faz parate dos admins ou mods
            elif member.id in owner_ids or member.id in mod_ids: 
                yield from self.bot.say("Não tenho permissão para remover o usuário {0} deste servidor.".format(member.name))
            elif member.id == self.bot.user.id:
                yield from self.bot.say("Desculpe, mas não irei obedecer. Se você quiser me remover, faça você mesmo.".format(member.name))
            else:
                motivo = motivo.replace('@{0}'.format(member.name), '').replace('  ', '')                    
                formatted_message = '{0} removido.'.format(member.name)
                #if len(motivo)> 0:
                    #formatted_message += ' Motivo: {0}'.format(motivo)
                yield from self.bot.send_message(member, formatted_message)
                yield from self.bot.send_message(server.owner, formatted_message)
                yield from self.bot.send_message(ctx.message.channel, formatted_message)
                yield from self.bot.kick(member)                    
                return

    @commands.command(name="ban", pass_context=True)
    @checks.is_admin()
    @checks.is_not_lite()
    @asyncio.coroutine
    def ban(self, ctx: commands.Context, *, message: str = None):
        """Bane um usuário

        Deve ser passado um (ou mais) @usuario(s) como parâmetro."""
                
        # Verifica se está em conversa privada ou em um canal no servidor #
        if ctx.message.channel.is_private:
            yield from self.bot.say("Você não pode executar este comando aqui.")
            return                    
               
        # Verifica se tem permissão pra remover usuário #
        permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server)) 
        if not permissions.ban_members: 
            yield from self.bot.say("Não tenho permissão para banir usuários neste servidor.")
            return            

        server = ctx.message.server 
        split = ctx.message.clean_content.split(" ", 1)    
        split.pop(0)                   
        motivo = ''
        for i in split:
            motivo += i + ' '
        
        for member in ctx.message.mentions:
            # Busca maior role do membro
            member_pos = 0
            for role in member.roles:
                if role.position > member_pos:
                    member_pos = role.position

            # Busca mamior role do bot
            bot_pos = 0
            for role in server.get_member(self.bot.user.id).roles:
                if role.position > bot_pos:
                    bot_pos = role.position        

            # Verifica se a role do usuário é menor que a role do bot
            if member_pos > bot_pos:
                yield from self.bot.say("Não tenho permissão para banir o usuário {0} deste servidor.".format(member.name))
            # Verifica se o usuário faz parate dos admins ou mods
            elif member.id in owner_ids or member.id in mod_ids: 
                yield from self.bot.say("Não tenho permissão para banir o usuário {0} deste servidor.".format(member.name))
            elif member.id == self.bot.user.id:
                yield from self.bot.say("Desculpe, mas não irei obedecer. Se você quiser me banir, faça você mesmo.".format(member.name))
            else:
                motivo = motivo.replace('@{0}'.format(member.name), '').replace('  ', '')                    
                formatted_message = '{0} banido.'.format(member.name)
                #if len(motivo)> 0:
                    #formatted_message += ' Motivo: {0}'.format(motivo)
                yield from self.bot.send_message(member, formatted_message)
                yield from self.bot.send_message(server.owner, formatted_message)
                yield from self.bot.send_message(ctx.message.channel, formatted_message)
                yield from self.bot.ban(member,0)                    
                return        

    @commands.command(name="unban", pass_context=True)
    @checks.is_admin()
    @checks.is_not_lite()
    @asyncio.coroutine
    def unban(self, ctx: commands.Context, *, message: str = None):
        """Desbane um usuário

        Deve ser verificado os usuários banidos com /getban e depois utilizar /unban [nome] ao invés de @user."""
                
        # Verifica se está em conversa privada ou em um canal no servidor #
        if ctx.message.channel.is_private:
            yield from self.bot.say("Você não pode executar este comando aqui.")
            return                    
               
        # Verifica se tem permissão pra remover usuário #
        permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server)) 
        if not permissions.ban_members: 
            yield from self.bot.say("Não tenho permissão para desbanir usuários neste servidor.")
            return            

        server = ctx.message.server 
        split = ctx.message.clean_content.split(" ", 1)    
        split.pop(0) 
        ban_users = yield from self.bot.get_bans(server)   
        if len(ban_users) == 0:
            yield from self.bot.say("Nenhum usuário banido neste servidor.")
            return             
        usernames = [user.name for user in ban_users] 
        matching_list = [s for s in split if s in usernames]
        formatted_message = '' 
        matching_id = []
        if len(matching_list) == 1:    
            for user in ban_users:                        
                matching = [s for s in split if s in user.name]
                if len(matching) == 1:                               
                    formatted_message = '{0} desbanido do servidor {1}'.format(user.name, server.name)                    
                    yield from self.bot.send_message(server.owner, formatted_message)
                    yield from self.bot.unban(server,user)                    
                    return  
        if len(matching_list) > 1:
            for i, user in ban_users: 
                formatted_message += '0. Sair\n'                       
                matching = [s for s in split if s in user.name]
                if len(matching) == 1:  
                    matching_id.append(i)                             
                    formatted_message += '{0}. {0.name}\n'.format(i+1, user)
            embed = discord.Embed(title='Usuários banidos encontrados', description=formatted_message)  
            yield from self.bot.say(embed)        
            yield from self.bot.say('Digite o número do usuário que você quer desbanir.')
            answer = yield from self.bot.wait_for_message(timeout=60.0, author=ctx.message.author, channel=ctx.message.channel)
            if answer is None:
                yield from self.bot.say("Pelo visto você mudou de ideia.")
                return
            elif is_numeric(answer.content):
                answer = int(answer.content)
                if answer not in matching_id:
                    yield from self.bot.say("Este número não estava nas possíveis escolhas. Tente novamente.")
                    return
                if answer == 0:
                    yield from self.bot.say("Mudou de ideia? Típico.")
                    return
                try:
                    user = ban_users[answer - 1]
                except IndexError:
                    yield from self.bot.say("Este número não estava nas possíveis escolhas. Tente novamente.")
                    return
            else:
                yield from self.bot.say("Resposta inválida.")
                return
            yield from self.bot.unban(server,user)                    
            return          
        if len(matching_list) == 0: 
            yield from self.bot.say("Não encontrei usuários banidos com este critério.")
            return                    

    @commands.command(name="getbans", pass_context=True)
    @checks.is_admin()
    @checks.is_not_lite()
    @asyncio.coroutine
    def getbans(self, ctx: commands.Context, *, message: str = None):
        """Retorna membros banidos do servidor"""
                
        # Verifica se está em conversa privada ou em um canal no servidor #
        if ctx.message.channel.is_private:
            yield from self.bot.say("Você não pode executar este comando aqui.")
            return                    
                     
        server = ctx.message.server 
        ban_users = yield from self.bot.get_bans(server)
        formatted_message = ''
        for user in ban_users:            
            formatted_message += '@{0.name}#{0.discriminator}\n'.format(user)
        if len(ban_users) == 0:
            yield from self.bot.say("Nenhum usuário banido neste servidor.")
        else:
            embed = discord.Embed(title='Usuários banidos', description=formatted_message)  
            yield from self.bot.say(embed=embed)

def get_check_emoji(check: bool) -> str:
    return EMOJI[":white_check_mark:"] if check else EMOJI[":x:"]

def setup(bot):
    bot.add_cog(Admin(bot))
