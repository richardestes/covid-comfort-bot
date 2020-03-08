import json
import os
from os.path import join
from ibm_watson import ToneAnalyzerV3
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from datetime import date
import praw
import re
import time
import requests
import getpass
import string
import logging
import math
import progressbar
import emoji
from security import encrypt_password, check_encrypted_password


def setup_watson_service():
    # IBM Watson Setup
    ibm_api_key = os.environ['IBM_API_KEY']
    ibm_service_url = os.environ['IBM_SERVICE_URL']
    authenticator = IAMAuthenticator(ibm_api_key)
    service = ToneAnalyzerV3(version='2017-09-21',
                             authenticator=authenticator)
    service.set_service_url(ibm_service_url)
    return service


def reddit_grab_posts(reddit_username, reddit_password, comment_dictionary_reply, comment_dictionary_message):
    hash = encrypt_password(reddit_password)
    print("Checking if password was encrypted successfully...")
    if(check_encrypted_password(reddit_password, hash)):
        print("Password successfully encrypted.")
    else:
        print("Uh oh, password was not encrypted correctly. Exiting...")
        exit(1)

    # Bot Creation
    print("Connecting to Reddit...")
    reddit_client_id = os.environ['REDDIT_CLIENT_ID']
    reddit_client_secret = os.environ['REDDIT_CLIENT_SECRET']
    reddit = praw.Reddit(client_id=reddit_client_id,
                         client_secret=reddit_client_secret,
                         user_agent='<console:covid_comfort_posts:0.0.1 (by /u/covid_comfort)>',
                         username=reddit_username,
                         password=reddit_password
                         )

    # Add Reddit comments from top posts of the hour to our dictionaries
    # This is one request
    for submission in reddit.subreddit('covid19_support').top('week'):
        submission.comments.replace_more(limit=None)
        for comment in submission.comments.list():
            if comment.id:
                comment_dictionary_reply[comment.id] = comment.body
            if comment.author:
                comment_dictionary_message[comment.author.name] = comment.body
    # reply_text = "hello i am a bot!"
    # submission.reply(reply_text)
    # reddit.redditor('dj505Gaming').message('TEST', 'This happened!')
    # print("Replied to post.")

    # Check if dictionary is empty.
    if comment_dictionary_message:
        print('Grabbed comments from Reddit!')
        # print(json.dumps(comment_dictionary_message,
        #                  indent=4, separators=(',', ': ')))
    else:
        print('No comments found. Exiting...')
        exit(1)


def strip_emoji(text):

    new_text = re.sub(emoji.get_emoji_regexp(), r"", text)

    return new_text


def sentiment_analysis_filter(dictionary):
    # count = 0
    for key in dictionary:
        key_tmp = key
        for comment_text in dictionary.values():
            # Send to sentiment analysis API
            formatted_text = strip_emoji(comment_text)
            request_host = os.environ['SENTIMENT_ANALYSIS_HOST']
            request_api_key = os.environ['SENTIMENT_ANALYSIS_API_KEY']

            url = "https://japerk-text-processing.p.rapidapi.com/sentiment/"

            payload = "text=" + formatted_text
            headers = {
                'x-rapidapi-host': request_host,
                'x-rapidapi-key': request_api_key,
                'content-type': "application/x-www-form-urlencoded"
            }
            response = requests.request(
                "POST", url, data=payload.encode('utf-8'), headers=headers)
            json_dictionary = response.json()

            # Filters comments that have a high probability of a negative sentiment
            for item in json_dictionary.items():
                # print(item)
                if(type(item) == 'dict'):
                    dict_item = item
                    for key, value in dict_item.items():
                        print(key, value)
                        # fSet = frozenset(item)
                        # for j in json_dictionary[i].keys():
                        #     print(j)

                        # for key, value in json_dictionary.items():
                        #     negative_value = json_dictionary['probability']['neg']
                        #     label = json_dictionary['label']
                        #     if negative_value >= 0.9 and label == 'neg':
                        #         filtered_dictionary[key] = comment_text
                        #         print('Found!')
                        # # count = count + 1
                        # else:
                        #     # count = count + 1
                        #     continue

                        # print(filtered_dictionary)


def create_filename_for_json():
    now = datetime.now()
    date = now.strftime("%b_%m_%I_%M_%p")
    filename = date + "_comments"
    return filename

# IBM Watson can handle json formats


def dump_dict_to_json(dictionary, json_filename):
    with open(json_filename, 'w') as fp:
        json.dump(dictionary, fp)


def send_to_watson(service, json_file, comment_count):
    if comment_count < 88:
        print('Sending to Watson...')
        json_path = 'resources/' + json_filename
        with open(join(os.getcwd(), json_path)) as tone_json:
            tone = service.tone(json.load(tone_json)[
                'text'], content_type="text/plain").get_result()
            print(json.dumps(tone, indent=2))
            comment_count = comment_count + 1
    else:
        print("We can't send anymore requests to Watson right now. Exiting...")
        exit(1)


reddit_username = "covid_comfort"
reddit_password = getpass.getpass("Enter the bot password: ")
watson_service = setup_watson_service()

comment_dictionary_reply = {}
comment_dictionary_message = {}
sentiment_analysis_dictionary = {}
filtered_dictionary = {}

reddit_grab_posts(reddit_username, reddit_password,
                  comment_dictionary_reply, comment_dictionary_message)
sentiment_analysis_filter(comment_dictionary_message)
# json_filename = create_filename_for_json()
# dump_dict_to_json(filtered_dictionary, json_filename)
# send_to_watson(watson_service, filtered_dictionary)
