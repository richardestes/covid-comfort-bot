import json
import os
from os.path import join
from ibm_watson import ToneAnalyzerV3
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from datetime import date
import praw
import re
import time
import datetime
import requests
import getpass
import string
import logging
import math
import progressbar
import emoji
from security import encrypt_password, check_encrypted_password

# Variable Setup
reddit_username = "covid_comfort"
reddit_password = getpass.getpass("Enter the bot password: ")

comment_dictionary_reply = {}
comment_dictionary_message = {}
sentiment_analysis_list = []
filtered_dictionary = {}
filtered_list = []
comments_amount = 0


def sleep(secs):
    # 900 = 15 mins
    # 1800 = 30 mins
    # 3600 = 1 hour
    # 7200 = 2 hours
    # 43200 = 12 hours
    # 86400 = 24 hours
    bar = progressbar.ProgressBar(max_value=100)
    for i in range(secs):
        time.sleep(1)
        tmp = i / secs * 100
        if ((tmp % 1) == 0):
            tmpInt = int(tmp)
            bar.update(tmpInt)


def create_progress_bar(limit):
    bar = progressbar.ProgressBar(max_value=limit)
    return bar


def setup_watson_service():
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
    print('Connected! Fetching comments...')

    posts = top_posts_from_subreddit(reddit, 'covid19_support')
    for post in posts:
        get_best_comments(post, 1)

    comments_amount = len(comment_dictionary_message)

    # Check if dictionary is empty.
    if comment_dictionary_message:
        print('Grabbed ' + str(comments_amount) + ' comments from Reddit!')
        send_to_sentiment_analysis(
            comment_dictionary_message, comments_amount)
        # print(json.dumps(comment_dictionary_message,
        #                  indent=4, separators=(',', ': ')))
    else:
        print('No comments found. Exiting...')
        exit(1)


def get_best_comments(submission, limit):
    # Set comment sort to best before retrieving comments
    submission.comment_sort = 'best'
    # Limit to, at most, 5 top level comments
    submission.comment_limit = limit
    # Fetch the comments and print each comment body
    # This must be done _after_ the above lines or they won't take affect.
    for top_level_comment in submission.comments:
        if isinstance(top_level_comment, praw.models.MoreComments):
            continue
        # Here you can fetch data off the comment.
        # For the sake of example, we're just printing the comment body.
        # print(top_level_comment.body)
        if top_level_comment.id:
            comment_dictionary_reply[top_level_comment.id] = top_level_comment.body
        if top_level_comment.author:
            comment_dictionary_message[top_level_comment.author.name] = top_level_comment.body


def top_posts_from_subreddit(reddit, sub_name):
    # This assumes you have a global "reddit" object.
    # You may prefer to pass the "reddit" object in as a
    # parameter to this function.
    subreddit = reddit.subreddit(sub_name)
    top_posts = []
    # The default for the 'top' function is "top of all time".
    for post in subreddit.top():
        top_posts.append(post)
    # You'll have _up to_, but no more than, 1000 submissions by now.
    return top_posts


def strip_emoji(text):

    new_text = re.sub(emoji.get_emoji_regexp(), r"", text)

    return new_text


def send_to_sentiment_analysis(dictionary, comments_amount):
    count = 0
    # progress = 0
    interval_float = comments_amount / 100
    interval = math.ceil(interval_float)
    # Send to sentiment analysis API
    request_host = os.environ['SENTIMENT_ANALYSIS_HOST']
    request_api_key = os.environ['SENTIMENT_ANALYSIS_API_KEY']
    print('Sending ' + str(comments_amount) + ' to sentiment analysis...')
    progress_bar = create_progress_bar(comments_amount)

    for key, value in dictionary.items():
        formatted_text = strip_emoji(value)

        url = "https://japerk-text-processing.p.rapidapi.com/sentiment/"
        payload = "text=" + formatted_text
        headers = {
            'x-rapidapi-host': request_host,
            'x-rapidapi-key': request_api_key,
            'content-type': "application/x-www-form-urlencoded"
        }
        response = requests.request(
            "POST", url, data=payload.encode('utf-8'), headers=headers)
        count = count + 1

        # Check if response is in json format
        if 'json' in response.headers.get('Content-Type'):
            json_dictionary = response.json()
            label = json_dictionary['label']
            if label == 'neg':
                y = json_dictionary['probability']['neg']
                if y >= 0.9:
                    filtered_dictionary[key] = value
        else:
            continue

        time.sleep(0.1)
        progress = int(count)
        progress_bar.update(progress)


def create_filename_for_json():
    now = datetime.datetime.now()
    date = now.strftime("%b_%m_%I_%M_%p")
    filename = date + "_comments"
    return filename

# IBM Watson can handle json formats


def dump_dict_to_json(dictionary, json_filename):
    print('Dumping to json...')
    file_path = '../resources/' + json_filename
    with open(file_path, 'w') as json_file:
        json.dump(dictionary, json_file)


def send_to_watson(service):
    if len(filtered_dictionary) < 88:
        print('Sending to Watson...')
        for key, value in filtered_dictionary.items():
            comment_text = value
            tone = service.tone({'text': comment_text},
                                content_type='application/json'
                                ).get_result()
        # print(json.dumps(tone, indent=2))
        tmp = tone['document_tone']['tones']
        for x in tmp:
            tone_name = x['tone_name']
            score = x['score']
            print(tone_name)
            print(score)
    else:
        print("We can't send a file that big...this is awkward...")
        exit(1)


# Main
watson_service = setup_watson_service()
reddit_grab_posts(reddit_username, reddit_password,
                  comment_dictionary_reply, comment_dictionary_message)
json_filename = create_filename_for_json()
file_path = '../resources/' + json_filename
dump_dict_to_json(filtered_dictionary, json_filename)
watson_count = len(filtered_dictionary)
send_to_watson(watson_service)
