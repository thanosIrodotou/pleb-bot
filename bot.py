# -*- coding: utf-8 -*-
import os

import google_auth_oauthlib.flow
import googleapiclient.discovery
import json
import requests
import telebot
import random

from bs4 import BeautifulSoup

import youtube_uploader

scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]
client_secrets_file = "secrets.json"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
api_service_name = "youtube"
api_version = "v3"

DEVELOPER_KEY = os.environ['DEV_KEY']
PLAYLIST_NAME = os.environ['PLAYLIST_NAME']
PLAYLIST_ID = os.environ['PLAYLIST_ID']
PLAYLIST_DESC = os.environ['PLAYLIST_DESC']
CHANNEL_ID = os.environ['CHANNEL_ID']
WELCOME_MSG = os.environ['WELCOME_MSG']
SUCCESS_GIFS = [open('success_gifs/{}'.format(filename), 'rb')
                for filename in os.listdir('success_gifs')]
FAILURE_GIF = open('failure_gifs/failure1.gif', 'rb')
ACHIEVEMENT_GIF = open('achievement_gifs/trophy.gif', 'rb')

token = os.environ['TELEGRAM_TOKEN']
bot = telebot.TeleBot(token)


@bot.message_handler(commands=['listtracks'])
def list_tracks(message):
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=DEVELOPER_KEY)

    request = youtube.playlistItems().list(
        part="id",
        playlistId=PLAYLIST_ID
    )
    response = request.execute()
    totalResults = response['pageInfo']['totalResults']
    if totalResults % (100 - 1) == 0:
        bot.send_document(message.chat.id, ACHIEVEMENT_GIF) 
        bot.reply_to(message, 'Yes DUDES! We reached: {} tracks'.format(totalResults))
    else:
        print('You got {} tracks boyz!'.format(totalResults))


@bot.message_handler(commands=['playlist'])
def create_playlist(message):
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_local_server(
        host='localhost',
        port=8088,
        authorization_prompt_message='Please visit this URL: {url}',
        success_message='The playlist creation auth flow is complete; you may close this window.',
        open_browser=True)
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": PLAYLIST_NAME,
                "description": PLAYLIST_DESC,
                "tags": [
                    "sample playlist",
                    "API call"
                ],
                "defaultLanguage": "en"
            },
            "status": {
                "privacyStatus": "public"
            }
        }
    )
    response = request.execute()
    bot.reply_to(message, 'Yes Bossman! {}'.format(response))
    print(response)


def get_playlist():
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=DEVELOPER_KEY)

    request = youtube.playlists().list(
        part="snippet,contentDetails",
        channelId=CHANNEL_ID,
        maxResults=1
    )
    response = request.execute()
    return {'id': response['items'][0]['id'], 'name': response['items'][0]['snippet']['title']}


def insert_video_to_playlist(playlist_id, video_id):
    print("id", playlist_id)
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_local_server(
        host='localhost',
        port=8088,
        authorization_prompt_message='Please visit this URL: {url}',
        success_message='The auth flow is complete; you may close this window.',
        open_browser=True)
    attrs = vars(credentials)
    print(', '.join("%s: %s" % item for item in attrs.items()))
    with open('token.token', 'w+') as f:
        f.write(credentials.token)
    with open('refresh.token', 'w+') as f:
        f.write(credentials._refresh_token)
    print('Refresh Token:', credentials._refresh_token)
    print('Saved Refresh Token to file: refresh.token')

    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

    request = youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "position": 0,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
    )
    response = request.execute()


def upload_to_playlist(remote_playlist, playlist, message, video_id):
    if remote_playlist['name'] == playlist:
        insert_video_to_playlist(remote_playlist['id'], video_id)
        bot.send_document(message.chat.id, random.choice(SUCCESS_GIFS))
    else:
        bot.reply_to(
            message, 'Could not find playlist: {}'.format(playlist))


@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(message, WELCOME_MSG)


@bot.message_handler(func=lambda message: True)
def echo_message(message):
    if 'open.spotify.com/' in message.text:
        res = requests.get(message.text)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, 'html.parser')
            title = soup.title.get_text().replace('on Spotify', '')
            print(title)
            str_title = title.replace(' ', '+')
            message.content_type = 'video'
            print(json.dumps(str(message.chat.id), indent=4, sort_keys=True))
            bot.reply_to(
                message, 'Youtube Search:\nhttps://www.youtube.com/results?search_query={}'.format(str_title))
    elif '://youtu.be/' in message.text:
        video_id = message.text.split('youtu.be/')[1]
        youtube_uploader.upload(video_id)
        bot.send_document(message.chat.id, random.choice(SUCCESS_GIFS))
    elif 'www.youtube.com/watch?v=' in message.text:
        video_id = message.text.split('watch?v=')[1]
        try:
            youtube_uploader.upload(video_id)
            bot.send_document(message.chat.id, random.choice(SUCCESS_GIFS))
            list_tracks(message)
        except googleapiclient.errors.HttpError as err:
            print('Error when uploading', err)
            bot.send_document(message.chat.id, FAILURE_GIF)


bot.polling()
