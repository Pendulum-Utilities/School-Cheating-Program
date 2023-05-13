# MIT License

# Copyright (c) 2023 Pendulum-Utilities

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
print("Importing main libraries...")
import discord
from Bard import Chatbot
import asyncio
import pyttsx3
import speech_recognition as sr
from tinytag import TinyTag
import json
print("Done!")

settings = json.loads(open("settings.json", "r").read())
token = settings["BardKey"]
client = discord.Client(intents=None)
print("Logging into bard...")
chatbot = Chatbot(token)
print("Logged in!")
key = settings["DiscordBotKey"]
engine = pyttsx3.init()
engine.setProperty('rate',200)
# Bard commonly repeats this statement and its literally inside all of its responses. I swear to fucking god all these AI bot are just google but it sounds like english.
BardWarning = "I am a large language model, also known as a conversational AI or chatbot trained to be informative and comprehensive. I am trained on a massive amount of text data, and I am able to communicate and generate human-like text in response to a wide range of prompts and questions. For example, I can provide summaries of factual topics or create stories."

def GenerateResponse(Message):
    response = chatbot.ask("Dont show steps to math problems and only give the answer. Also, make sure your responses are as short as you possibly can make them. If the users asks about something, don't provide long summaries unless asked to. Just tell them something super duper short. The users prompt is here, make sure to follow all these directives at all times: " + Message)["content"].replace(BardWarning, "").replace(".", ",")   
    print(response)
    return response

def get_audio_duration(file_path):
    tag = TinyTag.get(file_path)
    return tag.duration

voice_clients = {}
queues = {}
ffmpeg_options = {'options': "-vn"}
listener = sr.Recognizer()

async def save_speech_to_file(response, file_name):
    await asyncio.to_thread(engine.save_to_file, response, file_name)
    await asyncio.to_thread(engine.runAndWait)

async def play_next_in_queue(voiceclient, guild_id):
    if guild_id not in queues or len(queues[guild_id]) == 0:
        return

    audio_source = queues[guild_id].pop(0)
    player = discord.FFmpegPCMAudio(source=audio_source, **ffmpeg_options, executable="ffmpeg.exe")
    voice_clients[guild_id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_in_queue(voiceclient, guild_id), client.loop))

async def process_voice(voiceclient, guild_id):
    while True:
        await asyncio.sleep(0.1)
        if voice_clients[guild_id].is_playing():
            continue
        try:
            with sr.Microphone() as source:
                audio = await asyncio.to_thread(listener.listen, source, 5)
            print("Transcribing...")
            text = await asyncio.to_thread(listener.recognize_google, audio)
            print("You said: ", text)
            print("Typing please wait...")
            response = GenerateResponse(text)
            await save_speech_to_file(response, 'GeneratedText.mp3')
            if guild_id not in queues:
                queues[guild_id] = []
            queues[guild_id].append("GeneratedText.mp3")
            if not voice_clients[guild_id].is_playing():
                await play_next_in_queue(voiceclient, guild_id)
            await asyncio.sleep(get_audio_duration("GeneratedText.mp3"))

        except (sr.UnknownValueError, sr.WaitTimeoutError):
            print('Listening...')
            continue

@client.event
async def on_message(msg):
    if msg.author == client.user:
        return

    if not msg.author.voice or not msg.author.voice.channel:
        return

    print("Message detected, joining user's voice channel")
    voiceclient = await msg.author.voice.channel.connect()
    voice_clients[voiceclient.guild.id] = voiceclient
    print("Joined voice channel")

    # Create a new task for voice processing
    asyncio.create_task(process_voice(voiceclient, voiceclient.guild.id))

client.run(key)
