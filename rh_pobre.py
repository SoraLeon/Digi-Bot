import discord
from discord.ext import commands
from PIL import Image
import os
import random
import requests
import io
import urllib

from config import *
from utils import checks

from utils.general import is_numeric, get_time_diff, join_list, get_brasilia_time_zone, log
from utils.messages import EMOJI, split_message
from utils.discord import get_member_by_name, get_user_color, get_member, get_channel_by_name, get_user_servers, FIELD_VALUE_LIMIT
from utils.paginator import Paginator, CannotPaginate
from utils.pobre import *
from utils.rh import *
from urllib import parse

# Commands
class Pobre:
    """Pobre related commands."""
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.parsing_count = 0    

    @commands.command(pass_context=True, aliases=['game'])
    @asyncio.coroutine
    def jogo(self, ctx, *, name: str=None):
        """Pesquisa jogos no romhacking.net"""

        ask_channel = get_channel_by_name(self.bot, ask_channel_name, ctx.message.server)
        destination = ctx.message.channel if ctx.message.channel.name == ask_channel_name else ctx.message.author
        permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
        if not permissions.embed_links:
            yield from self.bot.say("Foi mal, eu preciso de permissões de `Embed Links` para executar este comando.")
            return

        if name is None:
            yield from self.bot.say("Diga-me o nome do jogo que desejas pesquisar.")
            return
        game = yield from get_games(parse.quote(name.replace(' ', '+').encode('iso-8859-1'), safe='+'))        
        if game is None or len(game) == 0:
            yield from self.bot.say("Não encontrei nenhum jogo.")
            return
        long = ctx.message.channel.is_private or ctx.message.channel.name == ask_channel_name
        embed = self.get_game_rh_embed(ctx, game, long)
        if len(game) > 1:  
            start = 0
            answer = '+'
            bot_message = yield from self.bot.say("Escolha uma das opções abaixo (0: Cancelar):", embed=embed)
            while answer == '+' or answer == '-':                                      
                answer = yield from self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel,timeout=30.0)
                if answer is None:
                    yield from self.bot.say("... opa, esqueceu de mim? Beleza, então!")
                    return
                elif is_numeric(answer.content):
                    answer = int(answer.content)
                    if answer == 0:
                        yield from self.bot.say("Mudou de ideia? Típico.")
                        return
                    try:    
                        choice = game[answer-1]
                        game = []             
                        details = yield from get_game_rh(choice["link"],)
                        game.append({'name' : choice["name"], 'link' : choice["link"], 'details': details})
                        embed = self.get_game_rh_embed(ctx, game, long) 
                    except IndexError:
                        yield from self.bot.say("Nossa, pra que fazer isso, você nem escolheu algo válido. Agora comece de novo.")
                elif isinstance(answer.content, str) and (answer.content == '-' or answer.content == '+'):
                    if not ctx.message.channel.is_private and ctx.message.channel != ask_channel:
                        yield from self.bot.delete_message(answer)
                    answer = str(answer.content)
                    if  answer == '-' and start - 10 >= 0:
                        start -= 10
                        embed = self.get_game_rh_embed(ctx, game, long, start) 
                    elif answer == '+' and start + 10 < len(game):
                        start += 10
                        embed = self.get_game_rh_embed(ctx, game, long, start)
                    yield from self.bot.edit_message(bot_message, "Escolha uma das opções abaixo (0: Cancelar):", embed=embed)     
                else:
                    yield from self.bot.say("Essa não é uma resposta válida!")
        if len(game) == 1:
            if destination != ask_channel:
                yield from self.bot.say("Estou te enviando as informações solicitadas via mensagem privada.")

            # Attach folder image if there is
            permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
            trad = game[0]
            if "details" in trad:
                if "imagem_capa" in trad["details"]:
                    for image in trad["details"]["imagem_capa"]:
                        if permissions.attach_files and image != 0:                                                                                  
                            filename = 'temp.png'                            
                            while os.path.isfile(filename):
                                filename = "_" + filename
                            with open(filename, "w+b") as f:
                                f.write(image)
                                f.close()

                            with open(filename, "r+b") as f:
                                yield from self.bot.send_file(destination, f)
                                f.close()
                            os.remove(filename)

            yield from self.bot.send_message(destination, embed=embed)
            
            # Attach item's image only if the bot has permissions
            permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
            trad = game[0]
            if "details" in trad:
                if "imagens" in trad["details"]:
                    for image in trad["details"]["imagens"]:
                        if permissions.attach_files and image != 0:                                                                                  
                            filename = 'temp.png'                            
                            while os.path.isfile(filename):
                                filename = "_" + filename
                            with open(filename, "w+b") as f:
                                f.write(image)
                                f.close()

                            with open(filename, "r+b") as f:
                                yield from self.bot.send_file(destination, f)
                                f.close()
                            os.remove(filename)
    
    @commands.command(pass_context=True, aliases=['translate_rh','patch_rh'])
    @asyncio.coroutine
    def traducao_rh(self, ctx, *, name: str=None):
        """Pesquisa traduções no romhacking.net"""

        ask_channel = get_channel_by_name(self.bot, ask_channel_name, ctx.message.server)
        destination = ctx.message.channel if ctx.message.channel.name == ask_channel_name else ctx.message.author
        permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
        if not permissions.embed_links:
            yield from self.bot.say("Foi mal, eu preciso de permissões de `Embed Links` para executar este comando.")
            return

        if name is None:
            yield from self.bot.say("Diga-me o nome da tradução que desejas pesquisar.")
            return
        traducao = yield from get_translates(parse.quote(name.replace(' ', '+').encode('iso-8859-1'), safe='+'))        
        if traducao is None or len(traducao) == 0:
            yield from self.bot.say("Não encontrei nenhuma tradução.")
            return
        long = ctx.message.channel.is_private or ctx.message.channel.name == ask_channel_name
        embed = self.get_traducao_rh_embed(ctx, traducao, long)
        if len(traducao) > 1:  
            start = 0
            answer = '+'
            bot_message = yield from self.bot.say("Escolha uma das opções abaixo (0: Cancelar):", embed=embed)
            while answer == '+' or answer == '-':                                      
                answer = yield from self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel,timeout=30.0)
                if answer is None:
                    yield from self.bot.say("... opa, esqueceu de mim? Beleza, então!")
                    return
                elif is_numeric(answer.content):
                    answer = int(answer.content)
                    if answer == 0:
                        yield from self.bot.say("Mudou de ideia? Típico.")
                        return
                    try:    
                        choice = traducao[answer-1]
                        traducao = []             
                        details = yield from get_game_rh(choice["link"],)
                        traducao.append({'name' : choice["name"], 'link' : choice["link"], 'details': details})
                        embed = self.get_traducao_rh_embed(ctx, traducao, long) 
                    except IndexError:
                        yield from self.bot.say("Nossa, pra que fazer isso, você nem escolheu algo válido. Agora comece de novo.")
                elif isinstance(answer.content, str) and (answer.content == '-' or answer.content == '+'):
                    if not ctx.message.channel.is_private and ctx.message.channel != ask_channel:
                        yield from self.bot.delete_message(answer)
                    answer = str(answer.content)
                    if  answer == '-' and start - 10 >= 0:
                        start -= 10
                        embed = self.get_traducao_rh_embed(ctx, traducao, long, start) 
                    elif answer == '+' and start + 10 < len(traducao):
                        start += 10
                        embed = self.get_traducao_rh_embed(ctx, traducao, long, start)
                    yield from self.bot.edit_message(bot_message, "Escolha uma das opções abaixo (0: Cancelar):", embed=embed)     
                else:
                    yield from self.bot.say("Essa não é uma resposta válida!")
        if len(traducao) == 1:
            if destination != ask_channel:
                yield from self.bot.say("Estou te enviando as informações solicitadas via mensagem privada.")

            # Attach folder image if there is
            permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
            trad = traducao[0]
            if "details" in trad:
                if "imagem_capa" in trad["details"]:
                    for image in trad["details"]["imagem_capa"]:
                        if permissions.attach_files and image != 0:                                                                                  
                            filename = 'temp.png'                            
                            while os.path.isfile(filename):
                                filename = "_" + filename
                            with open(filename, "w+b") as f:
                                f.write(image)
                                f.close()

                            with open(filename, "r+b") as f:
                                yield from self.bot.send_file(destination, f)
                                f.close()
                            os.remove(filename)

            yield from self.bot.send_message(destination, embed=embed)
            
            # Attach item's image only if the bot has permissions
            permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
            trad = traducao[0]
            if "details" in trad:
                if "imagens" in trad["details"]:
                    for image in trad["details"]["imagens"]:
                        if permissions.attach_files and image != 0:                                                                                  
                            filename = 'temp.png'                            
                            while os.path.isfile(filename):
                                filename = "_" + filename
                            with open(filename, "w+b") as f:
                                f.write(image)
                                f.close()

                            with open(filename, "r+b") as f:
                                yield from self.bot.send_file(destination, f)
                                f.close()
                            os.remove(filename)
    
    @commands.command(pass_context=True, aliases=['tool', 'ferramenta'])
    @asyncio.coroutine
    def utilitario(self, ctx, *, name: str=None):
        """Pesquisa utilitários no PO.B.R.E."""

        ask_channel = get_channel_by_name(self.bot, ask_channel_name, ctx.message.server)
        destination = ctx.message.channel if ctx.message.channel.name == ask_channel_name else ctx.message.author
        permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
        if not permissions.embed_links:
            yield from self.bot.say("Foi mal, eu preciso de permissões de `Embed Links` para executar este comando.")
            return

        if name is None:
            yield from self.bot.say("Diga-me o nome do utilitário que desejas pesquisar.")
            return
        tool = yield from get_search(parse.quote(name.replace(' ', '+').encode('iso-8859-1'), safe='+'), "26", '0')
        if tool is None or len(tool) == 0:
            yield from self.bot.say("Não encontrei nada com este nome.")
            return
        long = ctx.message.channel.is_private or ctx.message.channel.name == ask_channel_name
        embed = self.get_tool_embed(ctx, tool, long)
        if len(tool) > 1: 
            start = 0
            answer = '+'
            bot_message = yield from self.bot.say("Escolha uma das opções abaixo (0: Cancelar):", embed=embed)
            while answer == '+' or answer == '-':                
                answer = yield from self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel,timeout=30.0)
                if answer is None:
                    yield from self.bot.say("... opa, esqueceu de mim? Beleza, então!")
                    return                    
                elif is_numeric(answer.content):
                    answer = int(answer.content)
                    if answer == 0:
                        yield from self.bot.say("Mudou de ideia? Típico.")
                        return                                      
                    try:    
                        choice = tool[answer-1]
                        tool = []             
                        details = yield from get_details(choice["link"], "26", '0')
                        tool.append({'name' : choice["name"], 'link' : choice["link"], 'details': details})
                        embed = self.get_tool_embed(ctx, tool, long) 
                    except IndexError:
                        yield from self.bot.say("Nossa, pra que fazer isso, você nem escolheu algo válido. Agora comece de novo.")
                elif isinstance(answer.content, str) and (answer.content == '-' or answer.content == '+'):
                    if not ctx.message.channel.is_private and ctx.message.channel != ask_channel:
                        yield from self.bot.delete_message(answer)
                    answer = str(answer.content)
                    if  answer == '-' and start - 10 >= 0:
                        start -= 10
                        embed = self.get_tool_embed(ctx, tool, long, start) 
                    elif answer == '+' and start + 10 < len(tool):
                        start += 10
                        embed = self.get_tool_embed(ctx, tool, long, start)                        
                    yield from self.bot.edit_message(bot_message, "Escolha uma das opções abaixo (0: Cancelar):", embed=embed)     
                else:
                    yield from self.bot.say("Essa não é uma resposta válida!")
        if len(tool) == 1:
            if destination != ask_channel:
                yield from self.bot.say("Estou te enviando as informações solicitadas via mensagem privada.")

            yield from self.bot.send_message(destination, embed=embed)

            # Attach item's image only if the bot has permissions
            permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
            trad = tool[0]
            item = dict()
            if "details" in trad:
                if "imagens" in trad["details"]:
                    for image in trad["details"]["imagens"]:
                        if permissions.attach_files and image != 0:                                                                                  
                            filename = 'temp.png'
                            while os.path.isfile(filename):
                                filename = "_" + filename
                            with open(filename, "w+b") as f:
                                f.write(image)
                                f.close()

                            with open(filename, "r+b") as f:
                                yield from self.bot.send_file(destination, f)
                                f.close()
                            os.remove(filename)

    @commands.command(pass_context=True, aliases=['translate', 'patch'])
    @asyncio.coroutine
    def traducao(self, ctx, *, name: str=None):
        """Pesquisa traduções no PO.B.R.E."""

        ask_channel = get_channel_by_name(self.bot, ask_channel_name, ctx.message.server)
        destination = ctx.message.channel if ctx.message.channel.name == ask_channel_name else ctx.message.author
        permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
        if not permissions.embed_links:
            yield from self.bot.say("Foi mal, eu preciso de permissões de `Embed Links` para executar este comando.")
            return

        if name is None:
            yield from self.bot.say("Diga-me o nome da tradução que desejas pesquisar.")
            return
        traducao = yield from get_search(parse.quote(name.replace(' ', '+').encode('iso-8859-1'), safe='+'), "23", '0')        
        if traducao is None or len(traducao) == 0:
            yield from self.bot.say("Não encontrei nenhuma tradução.")
            return
        long = ctx.message.channel.is_private or ctx.message.channel.name == ask_channel_name
        embed = self.get_traducao_embed(ctx, traducao, long)
        if len(traducao) > 1:  
            start = 0
            answer = '+'
            bot_message = yield from self.bot.say("Escolha uma das opções abaixo (0: Cancelar):", embed=embed)
            while answer == '+' or answer == '-':                                      
                answer = yield from self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel,timeout=30.0)
                if answer is None:
                    yield from self.bot.say("... opa, esqueceu de mim? Beleza, então!")
                    return
                elif is_numeric(answer.content):
                    answer = int(answer.content)
                    if answer == 0:
                        yield from self.bot.say("Mudou de ideia? Típico.")
                        return
                    try:    
                        choice = traducao[answer-1]
                        traducao = []             
                        details = yield from get_details(choice["link"], "23", '0')
                        traducao.append({'name' : choice["name"], 'link' : choice["link"], 'details': details})
                        embed = self.get_traducao_embed(ctx, traducao, long) 
                    except IndexError:
                        yield from self.bot.say("Nossa, pra que fazer isso, você nem escolheu algo válido. Agora comece de novo.")
                elif isinstance(answer.content, str) and (answer.content == '-' or answer.content == '+'):
                    if not ctx.message.channel.is_private and ctx.message.channel != ask_channel:
                        yield from self.bot.delete_message(answer)
                    answer = str(answer.content)
                    if  answer == '-' and start - 10 >= 0:
                        start -= 10
                        embed = self.get_traducao_embed(ctx, traducao, long, start) 
                    elif answer == '+' and start + 10 < len(traducao):
                        start += 10
                        embed = self.get_traducao_embed(ctx, traducao, long, start)
                    yield from self.bot.edit_message(bot_message, "Escolha uma das opções abaixo (0: Cancelar):", embed=embed)     
                else:
                    yield from self.bot.say("Essa não é uma resposta válida!")
        if len(traducao) == 1:
            if destination != ask_channel:
                yield from self.bot.say("Estou te enviando as informações solicitadas via mensagem privada.")

            yield from self.bot.send_message(destination, embed=embed)

            # Attach item's image only if the bot has permissions
            permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
            trad = traducao[0]
            item = dict()
            if "details" in trad:
                if "imagens" in trad["details"]:
                    for image in trad["details"]["imagens"]:
                        if permissions.attach_files and image != 0:                                                                                  
                            filename = 'temp.png'                            
                            while os.path.isfile(filename):
                                filename = "_" + filename
                            with open(filename, "w+b") as f:
                                f.write(image)
                                f.close()

                            with open(filename, "r+b") as f:
                                yield from self.bot.send_file(destination, f)
                                f.close()
                            os.remove(filename)
            

    @commands.command(pass_context=True, aliases=['documento'])
    @asyncio.coroutine
    def tutorial(self, ctx, *, name: str=None):
        """Pesquisa tutoriais no PO.B.R.E."""

        ask_channel = get_channel_by_name(self.bot, ask_channel_name, ctx.message.server)
        destination = ctx.message.channel if ctx.message.channel.name == ask_channel_name else ctx.message.author
        permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
        if not permissions.embed_links:
            yield from self.bot.say("Foi mal, eu preciso de permissões de `Embed Links` para executar este comando.")
            return

        if name is None:
            yield from self.bot.say("Diga-me o nome do tutorial que desejas pesquisar.")
            return
        tutorial = yield from get_search(parse.quote(name.replace(' ', '+').encode('iso-8859-1'), safe='+'), "19", '0')
        if tutorial is None or len(tutorial) == 0:
            yield from self.bot.say("Não encontrei nenhum tutorial.")
            return
        long = ctx.message.channel.is_private or ctx.message.channel.name == ask_channel_name
        embed = self.get_tutorial_embed(ctx, tutorial, long)
        if len(tutorial) > 1:  
            start = 0
            answer = '+'
            bot_message = yield from self.bot.say("Escolha uma das opções abaixo (0: Cancelar):", embed=embed)
            while answer == '+' or answer == '-':                                       
                answer = yield from self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel,timeout=30.0)
                if answer is None:
                    yield from self.bot.say("... opa, esqueceu de mim? Beleza, então!")
                    return
                elif is_numeric(answer.content):
                    answer = int(answer.content)
                    if answer == 0:
                        yield from self.bot.say("Mudou de ideia? Típico.")
                        return
                    try:    
                        choice = tutorial[answer-1]
                        tutorial = []             
                        details = yield from get_details(choice["link"], "19", '0')
                        tutorial.append({'name' : choice["name"], 'link' : choice["link"], 'details': details})
                        embed = self.get_tutorial_embed(ctx, tutorial, long) 
                    except IndexError:
                        yield from self.bot.say("Nossa, pra que fazer isso, você nem escolheu algo válido. Agora comece de novo.")
                elif isinstance(answer.content, str) and (answer.content == '-' or answer.content == '+'):
                    if not ctx.message.channel.is_private and ctx.message.channel != ask_channel:
                        yield from self.bot.delete_message(answer)
                    answer = str(answer.content)
                    if  answer == '-' and start - 10 >= 0:
                        start -= 10
                        embed = self.get_tutorial_embed(ctx, tutorial, long, start) 
                    elif answer == '+' and start + 10 < len(tutorial):
                        start += 10
                        embed = self.get_tutorial_embed(ctx, tutorial, long, start)
                    yield from self.bot.edit_message(bot_message, "Escolha uma das opções abaixo (0: Cancelar):", embed=embed)     
                else:
                    yield from self.bot.say("Essa não é uma resposta válida!")
        if len(tutorial) == 1:
            if destination != ask_channel:
                yield from self.bot.say("Estou te enviando as informações solicitadas via mensagem privada.")

            yield from self.bot.send_message(destination, embed=embed)

            # Attach item's image only if the bot has permissions
            permissions = ctx.message.channel.permissions_for(get_member(self.bot, self.bot.user.id, ctx.message.server))
            trad = tutorial[0]
            item = dict()
            if "details" in trad:
                if "imagens" in trad["details"]:
                    for image in trad["details"]["imagens"]:
                        if permissions.attach_files and image != 0:                                                                                  
                            filename = 'temp.png'                            
                            while os.path.isfile(filename):
                                filename = "_" + filename
                            with open(filename, "w+b") as f:
                                f.write(image)
                                f.close()

                            with open(filename, "r+b") as f:
                                yield from self.bot.send_file(destination, f)
                                f.close()
                            os.remove(filename)      

    @staticmethod
    def get_tool_embed(ctx, tool, long, start=0):
        """Gets the tool embed to show in /utilitario command"""
        title = "Ferramentas"

        desc = ""
        index = start
        for i in tool[start:start+10]:
            # Se for apenas um resultado, já trás todos os dados            
            if "details" in i and len(i["details"]) > 0:
                if "name" in i:
                    desc += "**Nome:** [{0}]({1})\n".format(i["name"], i["link"])
                if "autor" in i["details"]:
                    desc += "**Autor:** {0}\n".format(i["details"]["autor"])
                if "sistema" in i["details"]:    
                    desc += "**Sistema:** {0}\n".format(i["details"]["sistema"])
                if "versao" in i["details"]:
                    desc += "**Versão:** {0}\n".format(i["details"]["versao"])
                if "lancamento" in i["details"]:
                    desc += "**Lançamento:** {0}\n".format(i["details"]["lancamento"])
                if "download" in i["details"]:
                    desc += "**Download:** [Link]({0})\n".format(i["details"]["download"])
                if "descricao" in i["details"]:
                    desc += "**Descrição:** {0}\n".format(i["details"]["descricao"])              
                title = "Detalhes da ferramenta"          
            # Senão retorna a lista contendo o link para cada um e um número     
            else:
                desc += "{2}: [{0}]({1})\n".format(i["name"], i["link"], index+1)
            # Lista informações de próxima página já que o embed contém um limite máximo de caracteres
            index += 1    
            if index == start+10 and start >= 10:
                desc += "*-: Página anterior*\t"
            if index == start+10 and len(tool) > start+10:                
                desc += "*+: Próxima página*\n"
        
        embed = discord.Embed(title=title, description=desc)      
        return embed            

    @staticmethod
    def get_traducao_embed(ctx, traducao, long, start=0):
        """Gets the tool embed to show in /traducao command"""
        title = "Traduções"

        desc = ""
        index = start
        for i in traducao[start:start+10]:
            # Se for apenas um resultado, já trás todos os dados 
            if "details" in i and len(i["details"]) > 0:
                if "name" in i:
                    desc += "**Nome:** [{0}]({1})\n".format(i["name"], i["link"])
                if "sistema" in i["details"]:    
                    desc += "**Sistema:** {0}\n".format(i["details"]["sistema"])
                if "autor" in i["details"]:
                    desc += "**Autor:** {0}\n".format(i["details"]["autor"])
                if "grupo" in i["details"]:
                    desc += "**Grupo:** {0}\n".format(i["details"]["grupo"])                    
                if "versao" in i["details"]:
                    desc += "**Versão:** {0}\n".format(i["details"]["versao"])
                if "lancamento" in i["details"]:
                    desc += "**Lançamento:** {0}\n".format(i["details"]["lancamento"])
                if "distribuicao" in i["details"]:
                    desc += "**Distribuição:** {0}\n".format(i["details"]["distribuicao"])
                if "progresso" in i["details"]:
                    desc += "**Progresso:** {0}\n".format(i["details"]["progresso"])          
                if "download" in i["details"]:
                    desc += "**Download:** [Link]({0})\n".format(i["details"]["download"])
                if "descricao" in i["details"]:
                    desc += "**Descrição:** {0}\n".format(i["details"]["descricao"])  
                if "consideracoes" in i["details"]:
                    desc += "**Considerações:** {0}\n".format(i["details"]["consideracoes"])                  
                title = "Detalhes da tradução"
            # Senão retorna a lista contendo o link para cada um e um número       
            else:     
                desc += "{2}: [{0}]({1})\n".format(i["name"], i["link"], index+1)
            # Lista informações de próxima página já que o embed contém um limite máximo de caracteres    
            index += 1
            if index == start+10 and start >= 10:
                desc += "*-: Página anterior*\t"
            if index == start+10 and len(traducao) > start+10:                
                desc += "*+: Próxima página*\n"

        embed = discord.Embed(title=title, description=desc)      
        return embed   

    @staticmethod
    def get_tutorial_embed(ctx, tutorial, long, start=0):
        """Gets the tool embed to show in /tutorial command"""
        title = "Tutoriais"

        desc = ""
        index = start
        for i in tutorial[start:start+10]:     
            # Se for apenas um resultado, já trás todos os dados         
            if "details" in i and len(i["details"]) > 0:
                if "name" in i:
                    desc += "**Nome:** [{0}]({1})\n".format(i["name"], i["link"])
                if "sistema" in i["details"]:    
                    desc += "**Sistema:** {0}\n".format(i["details"]["sistema"])
                if "autor" in i["details"]:
                    desc += "**Autor:** {0}\n".format(i["details"]["autor"])
                if "grupo" in i["details"]:
                    desc += "**Grupo:** {0}\n".format(i["details"]["grupo"])                    
                if "versao" in i["details"]:
                    desc += "**Versão:** {0}\n".format(i["details"]["versao"])
                if "lancamento" in i["details"]:
                    desc += "**Lançamento:** {0}\n".format(i["details"]["lancamento"])
                if "distribuicao" in i["details"]:
                    desc += "**Distribuição:** {0}\n".format(i["details"]["distribuicao"])
                if "progresso" in i["details"]:
                    desc += "**Progresso:** {0}\n".format(i["details"]["progresso"])          
                if "download" in i["details"]:
                    desc += "**Download:** [Link]({0})\n".format(i["details"]["download"])
                if "descricao" in i["details"]:
                    desc += "**Descrição:** {0}\n".format(i["details"]["descricao"])  
                if "consideracoes" in i["details"]:
                    desc += "**Considerações:** {0}\n".format(i["details"]["consideracoes"])                  
                title = "Detalhes do documento" 
            # Senão retorna a lista contendo o link para cada um e um número      
            else:
                desc += "{2}: [{0}]({1})\n".format(i["name"], i["link"], index+1)  
            # Lista informações de próxima página já que o embed contém um limite máximo de caracteres        
            index += 1
            if index == start+10 and start >= 10:
                desc += "*-: Página anterior*\t"
            if index == start+10 and len(tutorial) > start+10:                
                desc += "*+: Próxima página*\n"
        
        embed = discord.Embed(title=title, description=desc)      
        return embed     

    @staticmethod
    def get_traducao_rh_embed(ctx, traducao, long, start=0):
        """Gets the tool embed to show in /traducao command"""
        title = "Traduções"

        desc = ""
        index = start
        for i in traducao[start:start+10]:
            # Se for apenas um resultado, já trás todos os dados 
            if "details" in i and len(i["details"]) > 0:
                if "name" in i:
                    desc += "**Nome:** [{0}]({1})\n".format(i["name"], i["link"])
                if "platform" in i["details"]:    
                    desc += "**Sistema:** {0}\n".format(i["details"]["platform"])
                if "autor" in i["details"]:
                    desc += "**Autor:** {0}\n".format(i["details"]["autor"])
                if "grupo" in i["details"]:
                    desc += "**Grupo:** {0}\n".format(i["details"]["grupo"])                    
                if "versao" in i["details"]:
                    desc += "**Versão:** {0}\n".format(i["details"]["versao"])
                if "lancamento" in i["details"]:
                    desc += "**Lançamento:** {0}\n".format(i["details"]["lancamento"])
                if "distribuicao" in i["details"]:
                    desc += "**Distribuição:** {0}\n".format(i["details"]["distribuicao"])
                if "progresso" in i["details"]:
                    desc += "**Progresso:** {0}\n".format(i["details"]["progresso"]) 
                if "language" in i["details"]:
                    desc += "**Idioma:** {0}\n".format(i["details"]["language"])             
                if "download" in i["details"]:
                    desc += "**Download:** [Link]({0})\n".format(i["details"]["download"])
                #if "descricao" in i["details"]:
                    #desc += "**Descrição:** {0}\n".format(i["details"]["descricao"])  
                if "consideracoes" in i["details"]:
                    desc += "**Considerações:** {0}\n".format(i["details"]["consideracoes"])  
                if "trans_desc" in i["details"]:
                    desc += "**Descrição da Tradução:** \n{0}".format(i["details"]["trans_desc"]) 
                if "rom_info" in i["details"]:
                    desc += "**Informações de ROM / ISO:** \n{0}".format(i["details"]["rom_info"])    
                if "links" in i["details"]:
                    desc += "**Links:** \n{0}".format(i["details"]["links"])                          
                title = "Detalhes da tradução"
            # Senão retorna a lista contendo o link para cada um e um número       
            else:     
                desc += "{2}: [({5}) {0}]({1}) ({3}) [{4}]\n".format(i["name"], i["link"], index+1, i["autor"], i["idioma"], i["sistema"])
            # Lista informações de próxima página já que o embed contém um limite máximo de caracteres    
            index += 1
            if index == start+10 and start >= 10:
                desc += "*-: Página anterior*\t"
            if index == start+10 and len(traducao) > start+10:                
                desc += "*+: Próxima página*\n"

        embed = discord.Embed(title=title, description=desc)      
        return embed  

    @staticmethod
    def get_game_rh_embed(ctx, game, long, start=0):
        """Gets the tool embed to show in /game command"""
        title = "Jogos"

        desc = ""
        index = start
        for i in game[start:start+10]:
            # Se for apenas um resultado, já trás todos os dados 
            if "details" in i and len(i["details"]) > 0:
                if "name" in i:
                    desc += "**Nome:** [{0}]({1})\n".format(i["name"], i["link"])
                if "platform" in i["details"]:    
                    desc += "**Sistema:** {0}\n".format(i["details"]["platform"])
                if "autor" in i["details"]:
                    desc += "**Autor:** {0}\n".format(i["details"]["autor"])
                if "grupo" in i["details"]:
                    desc += "**Grupo:** {0}\n".format(i["details"]["grupo"])                    
                if "versao" in i["details"]:
                    desc += "**Versão:** {0}\n".format(i["details"]["versao"])
                if "lancamento" in i["details"]:
                    desc += "**Lançamento:** {0}\n".format(i["details"]["lancamento"])
                if "genre" in i["details"]:
                    desc += "**Gênero:** {0}\n".format(i["details"]["genre"])    
                if "distribuicao" in i["details"]:
                    desc += "**Distribuição:** {0}\n".format(i["details"]["distribuicao"])
                if "progresso" in i["details"]:
                    desc += "**Progresso:** {0}\n".format(i["details"]["progresso"]) 
                if "language" in i["details"]:
                    desc += "**Idioma:** {0}\n".format(i["details"]["language"])             
                if "download" in i["details"]:
                    desc += "**Download:** [Link]({0})\n".format(i["details"]["download"])
                if "descricao" in i["details"]:
                    desc += "**Descrição:** {0}\n".format(i["details"]["descricao"])  
                if "consideracoes" in i["details"]:
                    desc += "**Considerações:** {0}\n".format(i["details"]["consideracoes"])  
                if "trans_desc" in i["details"]:
                    desc += "**Descrição da Tradução:** \n{0}".format(i["details"]["trans_desc"]) 
                if "rom_info" in i["details"]:
                    desc += "**Informações de ROM / ISO:** \n{0}".format(i["details"]["rom_info"])    
                if "links" in i["details"]:
                    desc += "**Links:** \n{0}".format(i["details"]["links"])                          
                title = "Detalhes do jogo"
            # Senão retorna a lista contendo o link para cada um e um número       
            else:     
                desc += "{2}: [({3}) {0}]({1})\n".format(i["name"], i["link"], index+1, i["sistema"])
            # Lista informações de próxima página já que o embed contém um limite máximo de caracteres    
            index += 1
            if index == start+10 and start >= 10:
                desc += "*-: Página anterior*\t"
            if index == start+10 and len(game) > start+10:                
                desc += "*+: Próxima página*\n"

        embed = discord.Embed(title=title, description=desc)      
        return embed                  

def setup(bot):
    bot.add_cog(Pobre(bot))

if __name__ == "__main__":
    input("To run Monkey Slave, run rh.py")
