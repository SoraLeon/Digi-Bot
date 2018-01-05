import asyncio
import discord
from discord.ext import commands

from config import lite_mode, mod_ids, owner_ids
from utils.database import userDatabase
from utils.messages import split_message
from utils.general import is_numeric
from utils.discord import get_member, get_member_by_name, get_user_servers, send_log_message, get_user_admin_servers, FIELD_VALUE_LIMIT
from utils import checks


class Mod:
    """Commands for bot/server moderators."""
    def __init__(self, bot: discord.Client):
        self.bot = bot

    # Admin only commands #
    @commands.command(pass_context=True)
    @checks.is_mod()
    @asyncio.coroutine
    def makesay(self, ctx: discord.ext.commands.Context, *, message: str):
        """Makes the bot say a message
        If it's used directly on a text channel, the bot will delete the command's message and repeat it itself

        If it's used on a private message, the bot will ask on which channel he should say the message."""
        if ctx.message.channel.is_private:
            description_list = []
            channel_list = []
            prev_server = None
            num = 1
            for server in self.bot.servers:
                author = get_member(self.bot, ctx.message.author.id, server)
                bot_member = get_member(self.bot, self.bot.user.id, server)
                # Skip servers where the command user is not in
                if author is None:
                    continue
                # Check for every channel
                for channel in server.channels:
                    # Skip voice channels
                    if channel.type != discord.ChannelType.text:
                        continue
                    author_permissions = author.permissions_in(channel)  # type: discord.Permissions
                    bot_permissions = bot_member.permissions_in(channel)  # type: discord.Permissions
                    # Check if both the author and the bot have permissions to send messages and add channel to list
                    if (author_permissions.send_messages and bot_permissions.send_messages) and \
                            (ctx.message.author.id in owner_ids or author_permissions.administrator):
                        separator = ""
                        if prev_server is not server:
                            separator = "---------------\n\t"
                        description_list.append("{2}{3}: **#{0}** in **{1}**".format(channel.name, server.name,
                                                                                     separator, num))
                        channel_list.append(channel)
                        prev_server = server
                        num += 1
            if len(description_list) < 1:
                yield from self.bot.say("We don't have channels in common with permissions.")
                return
            yield from self.bot.say("Choose a channel for me to send your message (number only):" +
                                    "\n\t0: *Cancel*\n\t" +
                                    "\n\t".join(["{0}".format(i) for i in description_list]))
            answer = yield from self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel,
                                                          timeout=30.0)
            if answer is None:
                yield from self.bot.say("... are you there? Fine, nevermind!")
            elif is_numeric(answer.content):
                answer = int(answer.content)
                if answer == 0:
                    yield from self.bot.say("Changed your mind? Typical human.")
                    return
                try:
                    yield from self.bot.send_message(channel_list[answer-1], message)
                    yield from self.bot.say("Message sent on {0} ({1})".format(channel_list[answer-1].mention,
                                                                                channel_list[answer-1].server))
                except IndexError:
                    yield from self.bot.say("That wasn't in the choices, you ruined it. Start from the beginning.")
            else:
                yield from self.bot.say("That's not a valid answer!")

        else:
            yield from self.bot.delete_message(ctx.message)
            yield from self.bot.send_message(ctx.message.channel, message)   

def setup(bot):
    bot.add_cog(Mod(bot))
