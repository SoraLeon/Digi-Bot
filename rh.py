import asyncio

import io

from PIL import Image
from PIL import ImageDraw
from discord import Colour
import datetime
import urllib
import urllib.request
import aiohttp
import re
import html
import html2text
from datetime import datetime, date, timedelta
from calendar import timegm
import time

from config import highscores_categories, network_retry_delay
from utils.messages import EMOJI
from .general import log, global_online_list, get_local_timezone

# Constants
ERROR_NETWORK = 0
ERROR_DOESNTEXIST = 1
ERROR_NOTINDATABASE = 2

# http://romhackers.org (PO.B.R.E.) URLs:
url_translate = "http://www.romhacking.net/?page=translations&perpage=20&title={1}&transsearch=Go&startpage={0}"
url_game_list = "http://www.romhacking.net/?page=games&title={1}&perpage=20&gamesearch=Go&startpage={0}"

@asyncio.coroutine
def get_games(game_name, tries=5):    
    """Pega toda a lista de jogos e grava em um arquivo"""    
    gameList = []
    for i in range (0, 150):
        gl = yield from get_games_per_page(url_game_list.format(i+1,game_name), tries)
        if gl == None: 
            return gameList
        for g in gl:
            gameList.append(g)

    return gameList

@asyncio.coroutine
def get_translates(game_name, tries=5):
    """Pega toda a lista de jogos e grava em um arquivo"""    
    gameList = []
    for i in range (0, 150):
        gl = yield from get_games_per_page(url_translate.format(i+1,game_name), tries)
        if gl == None: 
            return gameList
        for g in gl:
            gameList.append(g)

    return gameList    

@asyncio.coroutine
def get_games_per_page(url, tries=5):
    """Retorna lista de jogos de uma página"""    
    # Fetch website
    try:
        page = yield from aiohttp.get(url)
        content = yield from page.text(encoding='utf-8')
    except Exception:
        if tries == 0:
            return ERROR_NETWORK
        else:
            tries -= 1
            yield from asyncio.sleep(network_retry_delay)
            ret = yield from get_games(tries)
            return ret 

    # Trimming content to reduce load
    try:
        start_index = content.index('<div id="main">')
        end_index = content.index('<div id="footer">')
        content = content[start_index:end_index]        
    except ValueError:
        # Website fetch was incomplete, due to a network error
        if tries == 0:
            return ERROR_NETWORK
        else:
            tries -= 1
            yield from asyncio.sleep(network_retry_delay)
            ret = yield from get_games(tries)
            return ret

    # Inicializa lista
    gameList = [] 

    # Name and link to page 
    regex_deaths = r'<td class="col_1 Title">(.*?)</td>'
    pattern = re.compile(regex_deaths, re.MULTILINE + re.S)
    matches = re.findall(pattern, content)    
    for i, m in enumerate(matches):
        # Nome    
        n = re.search(r'>[ ]*([^<]+).*<', m)
        if n:
            gameList.append({'name': html2text.html2text(n.group(1).strip()).replace('&amp;', '&').replace("\n"," ").replace("   ", "\n").rstrip()})

        # Link         
        n = re.search(r'<a href="([^<]+)">', m)
        if n:
            url_game = 'http://www.romhacking.net' + n.group(1).strip()
            #game = yield from get_game_rh(url_game)    
            #gameList[i] = {**gameList[i], **game}
            gameList[i]['link'] = url_game
            if len(matches) == 1:
                gameList[i]['details'] = yield from get_game_rh(url_game)

    # Translate list
    # col_2 Released By
    regex_deaths = r'<td class="col_2 Released By">(.*?)</td>'
    pattern = re.compile(regex_deaths, re.MULTILINE + re.S)
    matches = re.findall(pattern, content) 
    for i, m in enumerate(matches):          
        gameList[i]['autor'] = html2text.html2text(m.strip()).replace("\n"," ").replace("   ", "\n").rstrip() 

    # col_3 Genre
    regex_deaths = r'<td class="col_3 Genre">(.*?)</td>'
    pattern = re.compile(regex_deaths, re.MULTILINE + re.S)
    matches = re.findall(pattern, content) 
    for i, m in enumerate(matches):          
        gameList[i]['genero'] = html2text.html2text(m.strip()).replace("\n"," ").replace("   ", "\n").rstrip() 

    # col_4 Platform
    regex_deaths = r'<td class="col_4 Platform">(.*?)</td>'
    pattern = re.compile(regex_deaths, re.MULTILINE + re.S)
    matches = re.findall(pattern, content) 
    for i, m in enumerate(matches):          
        gameList[i]['sistema'] = html2text.html2text(m.strip()).replace("\n"," ").replace("   ", "\n").rstrip()

    # col_5 Status

    # col_6 Ver

    # col_7 Date

    # col_8 Lang  
    regex_deaths = r'<td class="col_8 Lang">(.*?)</td>'
    pattern = re.compile(regex_deaths, re.MULTILINE + re.S)
    matches = re.findall(pattern, content) 
    for i, m in enumerate(matches):          
        gameList[i]['idioma'] = html2text.html2text(m.strip()).replace("\n"," ").replace("   ", "\n").rstrip()      

    # Game list
    # col_3 Pub 
    regex_deaths = r'<td class="col_3 Pub">(.*?)</td>'
    pattern = re.compile(regex_deaths, re.MULTILINE + re.S)
    matches = re.findall(pattern, content) 
    for i, m in enumerate(matches):          
        gameList[i]['pub'] = html2text.html2text(m.strip()).replace("\n"," ").replace("   ", "\n").rstrip()                

    # col_6 Platform
    regex_deaths = r'<td class="col_6 Platform">(.*?)</td>'
    pattern = re.compile(regex_deaths, re.MULTILINE + re.S)
    matches = re.findall(pattern, content) 
    for i, m in enumerate(matches):          
        gameList[i]['sistema'] = html2text.html2text(m.strip()).replace("\n"," ").replace("   ", "\n").rstrip()    

    # Check if nothing is found
    if (gameList == []):
        gameList = None
    
    return gameList   

@asyncio.coroutine
def get_game_rh(url, tries=5):
    """Retorna os detalhes de um jogo no RH.NET"""    
    # Fetch website
    try:
        page = yield from aiohttp.get(url)
        content = yield from page.text(encoding='utf-8')
    except Exception:
        if tries == 0:
            return ERROR_NETWORK
        else:
            tries -= 1
            yield from asyncio.sleep(network_retry_delay)
            ret = yield from get_games(tries)
            return ret 

    # Trimming content to reduce load
    try:
        start_index = content.index('<div class="transbody">')
        end_index = content.index('<div id="footer">')
        content = content[start_index:end_index]        
    except ValueError:
        # Website fetch was incomplete, due to a network error
        if tries == 0:
            return ERROR_NETWORK
        else:
            tries -= 1
            yield from asyncio.sleep(network_retry_delay)
            ret = yield from get_games(tries)
            return ret

    #Inicializa lista
    game = dict()
    
    # Nome
    m = re.search(r'(?<=Title Screen)[\s\S.]*<div>([^<]+)</div>', content)
    if m:
        game['nome'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n").rstrip()

    # Released By
    m = re.search(r'<th>Released By</th><td>(.*?)</td>', content)
    if m:
        game['autor'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n").rstrip()

    # genre  
    m = re.search(r'<th>Genre</th><td>(.*?)</td>', content)
    if m:
        game['genre'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n").rstrip()

    # Patch Version  
    m = re.search(r'<th>Patch Version</th><td>(.*?)</td>', content)
    if m:
        game['versao'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n").rstrip()

    # status  
    m = re.search(r'<th>Status</th><td>(.*?)</td>', content)
    if m:
        game['progresso'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n").rstrip() 

    # release rh  
    m = re.search(r'<th>Release Date</th><td>(.*?)</td>', content)
    if m:
        game['lancamento'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n").rstrip()

    # language  
    m = re.search(r'<th>Language</th><td>(.*?)</td>', content)
    if m:
        game['language'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n").rstrip()    

    # platform  
    m = re.search(r'<th>Platform</th><td>(.*?)</td>', content)
    if m:
        game['platform'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n").rstrip()
    
    # Game Description  
    m = re.search(r'(?<=Game Description:)<\/h3>[\s]*<div>([\s\S.]*?)<\/div>', content)
    if m:
        game['descricao'] = html2text.html2text(m.group(1).strip()).replace("\n\n","<NEWLINE>").replace("\n", " ").replace("<NEWLINE>", "\n\n")

    # Translation Description 
    m = re.search(r'(?<=Translation Description:)<\/h3>[\s]*<div>([\s\S.]*?)<\/div>', content)
    if m:
        #game['descricao'] = m.group(1).strip()
        game['trans_desc'] = html2text.html2text(m.group(1).strip())

    # ROM / ISO Information 
    m = re.search(r'(?<=ROM \/ ISO Information:)<\/h3>[\s]*<div id="rom_info">([\s\S.]*?)<\/div>', content)
    if m:
        #game['descricao'] = m.group(1).strip()
        game['rom_info'] = html2text.html2text(m.group(1).strip())  

    # Links 
    m = re.search(r'(?<=Links:)<\/h3>[\s]*<ul>([\s\S.]*?)<\/ul>', content)
    if m:
        #game['descricao'] = m.group(1).strip()
        game['links'] = html2text.html2text(m.group(1).strip())              
    
    # imagem capa 
    m = re.search(r'(?<=<img)[\s\S.]*src="([^<]+)" alt[\s\S.]*(?=Title Screen)', content)
    if m:
        imagem = m.group(1).strip() 
        game['imagem_capa'] = []
        game['imagem_capa'].append(urllib.request.urlopen(urllib.parse.quote(imagem, safe='=/:[]()-.!@#$%&*~^´`{}?;><\\|\'')).read())

    # imagens  
    m = re.search(r'<h3>Screenshots:</h3>([\s\S.]*)<h3>Credits:</h3>', content)
    if m:
        matches = re.findall(r'<a href="([^>]+)">((?:.(?!\<\/a\>))*.)<\/a>', m.group(1).strip())
        imagem = m.group(1).strip() 
        if matches:
            game['imagens'] = []
            for match in matches:                
                image_link = urllib.parse.quote(match[0].replace('&amp;', '&'), safe='=/:[]()-.!@#$%&*~^´`{}?;><\\|\'')                
                image = yield from get_game_image(image_link)                
                game['imagens'].append(urllib.request.urlopen(image).read())

    return game   

@asyncio.coroutine
def get_game_image(url, tries=5):
    """Retorna imagem do espaço SCREENSHOTS """    
    # Fetch website
    try:
        page = yield from aiohttp.get(url)
        content = yield from page.text(encoding='utf-8')
    except Exception:
        if tries == 0:
            return ERROR_NETWORK
        else:
            tries -= 1
            yield from asyncio.sleep(network_retry_delay)
            ret = yield from get_games(tries)
            return ret 

    # Trimming content to reduce load
    try:
        start_index = content.index('<div class="transbody">')
        end_index = content.index('<div id="footer">')
        content = content[start_index:end_index]     
    except ValueError:
        # Website fetch was incomplete, due to a network error
        if tries == 0:
            return ERROR_NETWORK
        else:
            tries -= 1
            yield from asyncio.sleep(network_retry_delay)
            ret = yield from get_games(tries)
            return ret

    # Image link
    m = re.search(r'<img.*src="(.*)".*><\/a>', content)
    if m:       
        image = m.group(1).strip()
        return image

    return None