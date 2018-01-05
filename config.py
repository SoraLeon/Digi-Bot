# Lite mode:
# If lite is enabled, all user database related functions are disabled.
# /stalk, /im, /whois /levels are disabled
# /whois, /deaths have limited functionality
# Level up and deaths announcements are disabled
lite_mode = False

# Special bot channels
# ask_channel is a channel where the bot will give longer replies to some commands (like on pms)
#   If ask_channel_delete is True, any message that is not a command will be deleted, to keep the channel for
#   commands only
# server_log_channel is where the bot will log certain actions such as member joining and registering characters.
ask_channel_name = "ask-monkey"
ask_channel_delete = True
log_channel_name = "server-log"

# main_server is the ID of the server NabBot is originally made for, meaning there may be
# some exclusive features and/or commands on this server only.
main_server = "290226178571108355"

# The welcome message that is sent to members when they join a discord server with NabBot in it
# 0 is the member object, examples:
#       0.name - The joined member's name
#       0.server.name - The name of the server the member joined
#       0.server.owner.name - The name of the owner of the server the member joined
#       0.server.owner.mention - A mention to the owner of the server the member joined
# 1 is the bot's object, examples:
#       1.user.name - The bot's name
regras_pm =  "• **Não é permitido** conteúdo NSFW, ECHI, HENTAI e derivados, sendo punível à kick ou ban por tempo indeterminado.\n" \
             "• Para casos extremos, o que inclui **conteúdo homofóbico, racista, pornografia infantil, cenas de estupro, cenas de mortes, escatolagia e etc.**, o usuário será **banido sem aviso e para sempre**.\n" \
             "• Conteúdos NSFW que não se encaixam nas categorias acima **devem ser avisados previamente**.\n" \
             "• Não é permitido cobranças, apenas visamos o aprendizado." 

welcome_pm = "Seja bem vindo a **{0.server.name}**! Eu sou **{1.user.name}**, para aprender mais sobre meus comandos, digite `/help`\n" \
             "Abaixo a lista com as regras:\n" \
             + regras_pm                        

# It's possible to fetch the database contents on a website to show more entries than what the bot can display
# If enabled, certain commands will link to the website
site_enabled = True
baseUrl = "http://galarzaa.no-ip.org:7005/ReddAlliance/"
charactersPage = "characters.php"
deathsPage = "deaths.php"
levelsPage = "levels.php"

# Owners can use mods commands and more sensible commands like /shutdown and restart
# Mods can register chars and users and use makesay
owner_ids = ["145348710287540224"]
mod_ids = ["145348710287540224"]
# Enable of disable specific timezones for /time
display_brasilia_time = True
display_sonora_time = True

# Which highscores to track (can be empty)
highscores_categories = ["sword", "axe", "club", "distance", "shielding", "fist", "fishing", "magic",
                         "magic_ek", "magic_rp", "loyalty", "achievements"]

# Max amount of simultaneous images /loot can try to parse
loot_max = 6

# Level threshold for announces (level < announceLevel)
announce_threshold = 30

# Minimum days to show last login in /check command.
last_login_days = 7

# Delay inbreed server checks
online_scan_interval = 25

# Delay in between player death checks in seconds
death_scan_interval = 15

# Delay between each tracked world's highscore check and delay between pages scan
highscores_delay = 45
highscores_page_delay = 5

# Delay between retries when there's a network error in seconds
network_retry_delay = 0.5

if __name__ == "__main__":
    input("Para rodar Monkey Slave, rode monkeyslave.py")
