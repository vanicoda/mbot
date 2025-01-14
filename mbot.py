import discord, yt_dlp, asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f'로그인됨 : [\033[92m{bot.user}\033[0m]')

# YTDL, FFmpeg 설정
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'auto'
}
ffmpeg_options = {
    'executable': './ffmpeg.exe',
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# 노래 재생 프로세스 
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# 분:초 변환 함수
def sec_to_min(secs):
    return f"{secs // 60}:{secs % 60:02d}"

# 대기열
queue = []  

# 노래 재생 함수
async def play_next_song(guild, channel):
    voice_client = discord.utils.get(bot.voice_clients, guild=guild)
    if queue:  # 대기열에 노래가 있으면 재생
        url = queue.pop(0)  
        player = await YTDLSource.from_url(url, loop=bot.loop)
        voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(guild, channel), bot.loop))
        await channel.send(f'**재생중: {player.title} - [{sec_to_min(player.duration)}]**')
    else:   # 대기열이 없으면 음성채널 나감
        await voice_client.disconnect()  

# 채팅으로 노래봇 호출
@bot.event
async def on_message(message):

    if message.author == bot.user: 
        return

    if message.content.startswith('노래재생 '):
        url = message.content[len('노래재생 '):]
        voice_channel = message.author.voice.channel if message.author.voice else None

        if not voice_channel:
            await message.channel.send("먼저 음성채널에 입장해주세요.")
            return

        voice_client = discord.utils.get(bot.voice_clients, guild=message.guild)
        queue.append(url)
        
        if not voice_client or not voice_client.is_playing(): # 재생
            if voice_client is None:
                voice_client = await voice_channel.connect()
            await play_next_song(message.guild, message.channel)
        else: # 이미 재생중일때 대기열에 추가
            player = await YTDLSource.from_url(url, loop=bot.loop)
            await message.channel.send(f'**대기열에 추가됨: {player.title} - [{sec_to_min(player.duration)}]**')

        print(f"[\033[92m{message.author.display_name}\033[0m]이 [\033[94m{url}\033[0m] 재생 요청함")


# 봇 실행
f = open('token.txt', 'r')
token = f.readline()
bot.run(token)