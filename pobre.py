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
url_pobre = "http://romhackers.org/search.php?query={0}&mid={1}&action=showall&andor=AND&start={2}" 

@asyncio.coroutine
def get_search(name,mid,pagenum,tries=5):
    """Returns a dictionary containing search results, if exact match was found, it returns details of the search item."""

    url = url_pobre.format(name,mid,pagenum)
    # Fetch website
    try:
        page = yield from aiohttp.get(url)
        content = yield from page.text(encoding='ISO-8859-1')
    except Exception:
        if tries == 0:
            log.error("get_search: Couldn't fetch {0}, page {1}, network error.".format(name,pagenum))
            return ERROR_NETWORK
        else:
            tries -= 1
            yield from asyncio.sleep(network_retry_delay)
            ret = yield from get_search(name,mid,pagenum,tries)
            return ret 

    # Trimming content to reduce load
    try:
        start_index = content.index('<body>')
        end_index = content.index('</body>')
        content = content[start_index:end_index]
    except ValueError:
        # Website fetch was incomplete, due to a network error
        if tries == 0:
            log.error("get_search: Couldn't fetch {0}, page {1}, network error.".format(name,pagenum))
            return ERROR_NETWORK
        else:
            tries -= 1
            yield from asyncio.sleep(network_retry_delay)
            ret = yield from get_search(name,mid,pagenum,tries)
            return ret
    
    regex_deaths = r"<a href='([^<]+)'>([^<]+)</a></b><br />[^<]+<small>[^<]+<a href='([^<]+)'>([^<]+)</a>([^<]+)</small><br />"
    pattern = re.compile(regex_deaths, re.MULTILINE + re.S)
    matches = re.findall(pattern, content)
    searchList = []
    for m in matches:
        details = []
        if len(matches) == 1:
            details = yield from get_details('http://romhackers.org/' + m[0],mid)

        searchList.append({'link': 'http://romhackers.org/' + m[0], 'name': html.unescape(m[1]), 'user_link': m[2], 'user': m[3], 'date': m[4].replace('\n', '').replace(')','').replace('(',''), 'details': details})                                    
    if (searchList == []):
        searchList = None

    return searchList     

@asyncio.coroutine
def get_details(url,mid,tries=5):
    # Fetch website
    try:
        page = yield from aiohttp.get(url)
        content = yield from page.text(encoding='ISO-8859-1')
    except Exception:
        if tries == 0:
            log.error("get_details: Couldn't fetch the url {0} network error.".format(url))
            return ERROR_NETWORK
        else:
            tries -= 1
            yield from asyncio.sleep(network_retry_delay)
            ret = yield from get_details(name,mid,tries)
            return ret 

    # Trimming content to reduce load
    try:
        start_index = content.index('<div id="content">')
        end_index = content.index('<div style="text-align: center; padding: 3px; margin:3px;">')
        content = content[start_index:end_index]
    except ValueError:
        # Website fetch was incomplete, due to a network error
        if tries == 0:
            log.error("get_details: Couldn't fetch the url {0} network error.".format(url))
            return ERROR_NETWORK
        else:
            tries -= 1
            yield from asyncio.sleep(network_retry_delay)
            ret = yield from get_details(name,mid,tries)
            return ret
    
    details = dict()

    if mid == "26" or mid == "23": # 26 - detalhes de um utilitário / 23 - detalhes de tradução
        # Verifica se existe
        if "<b>Nome" not in content:
            return ERROR_DOESNTEXIST
        
        # Nome
        m = re.search(r'Nome</b>:[ ]*([^<]+).*', content)
        if m:
            details['nome'] = m.group(1).strip()

        # Autor
        m = re.search(r'Autor</b>:[ ]*([^<]+).*', content)
        if m:
            details['autor'] = m.group(1).strip()

        # Grupo
        m = re.search(r'Grupo</b>:[ ]*([^<]+).*', content)
        if m:
            details['grupo'] = m.group(1).strip()

        # Site
        m = re.search(r'Site</b>:[^<]+<a href="([^<]+)" target="_blank">', content)
        if m:
            details['site'] = m.group(1).strip()

        # Categoria
        m = re.search(r'Categoria</b>:[ ]*([^<]+).*', content)
        if m:
            details['categoria'] = m.group(1).strip()

        # Sistema
        m = re.search(r'Sistema</b>:[ ]*([^<]+).*', content)
        if m:
            details['sistema'] = m.group(1).strip()

        # Jogadores
        m = re.search(r'Jogadores</b>:[ ]*([^<]+).*', content)
        if m:
            details['jogadores'] = m.group(1).strip()    

        # Versão
        m = re.search(r'Versão</b>:[ ]*([^<]+).*', content)
        if m:
            details['versao'] = m.group(1).strip()

        # Lançamento
        m = re.search(r'Lançamento</b>:[ ]*([^<]+).*', content)
        if m:
            details['lancamento'] = m.group(1).strip()

        # Idioma
        m = re.search(r'Idioma</b>:[ ]*([^<]+).*', content)
        if m:
            details['idioma'] = m.group(1).strip()

        # Mídia de distribuição
        m = re.search(r'distribuição</b>:[ ]*([^<]+).*', content)
        if m:
            details['distribuicao'] = m.group(1).strip()  

        # Progresso
        m = re.search(r'Progresso</b>:[ ]*([^<]+).*', content)
        if m:
            details['progresso'] = m.group(1).strip()       

        # Plataforma
        m = re.search(r'Plataforma</b>:[ ]*([^<]+).*', content)
        if m:
            details['plataforma'] = m.group(1).strip()

        # Descrição
        m = re.search(r'[\s\S.]*<b>DESCRIÇÃO:[\s\S.]*?(?=<div class="even">?)<div[^<]+>(.+).*(?=</div>)', content)
        if m:
            details['descricao'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n")

        # Considerações
        m = re.search(r'[\s\S.]*<b>CONSIDERAÇÕES:[\s\S.]*?(?=<div class="even">?)<div[^<]+>(.+).*(?=</div>)', content)
        if m:
            details['consideracoes'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n")            

        # Imagem capa
        # TODO: ainda verificar REGEX
        m = re.search(r'[\s\S.]*<b>CONDIDERAÇÕES:[\s\S.]*(?=<div class="even">)<div[^<]+>(.+).*(?=</div>)', content)
        if m:
            details['consideracoes'] = html2text.html2text(m.group(1).strip()).replace("\n"," ").replace("   ", "\n")                        

        # Imagens
        m = re.search(r'(?<=<b>IMAGENS:)([\s\S.]*)</div></div><br/>', content)
        if m:          
            matches = re.findall(r'[^"]*src="([^"]+)"', m.group(1).strip())
            if matches:
                details['imagens'] = []
                for match in matches:
                    details['imagens'].append(urllib.request.urlopen(urllib.parse.quote(match, safe='=/:[]()-.!@#$%&*~^´`{}?;><\\|\'')).read())

        # Download
        m = re.search(r'<a href="([^"]+)(?=.*DOWNLOAD)', content)
        if m:
            details['download'] = 'http://romhackers.org/modules/PDdownloads2/' + m.group(1).strip()

    return details