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
import pprint
import emoji
from security import encrypt_password, check_encrypted_password
from dotenv import load_dotenv

load_dotenv()
# Variable Setup
reddit_username = "covid_comfort"
reddit_password = getpass.getpass("Enter the bot password: ")

comment_dictionary_reply = {}
comment_dictionary_message = {}
sentiment_analysis_list = []
filtered_dictionary = {}
filtered_dictionary_watson = {}
filtered_list = []
comments_amount = 0

ibm_api_key = os.environ['IBM_API_KEY']
ibm_service_url = os.environ['IBM_SERVICE_URL']
reddit_client_id = os.environ['REDDIT_COVID_CLIENT_ID']
reddit_client_secret = os.environ['REDDIT_COVID_CLIENT_SECRET']
request_host = os.environ['SENTIMENT_ANALYSIS_HOST']
request_api_key = os.environ['SENTIMENT_ANALYSIS_API_KEY']

pretty_printer = pprint.PrettyPrinter(compact=True)


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
    reddit = praw.Reddit(client_id=reddit_client_id,
                         client_secret=reddit_client_secret,
                         user_agent='<console:covid_comfort_posts:0.0.1 (by /u/covid_comfort)>',
                         username=reddit_username,
                         password=reddit_password
                         )
    print('Connected! Fetching comments...')

    try:
        posts = top_posts_from_subreddit(reddit, 'covid19_support')
    except praw.exceptions.ServerError:
        print('Something went wrong on the Reddit server side. Trying again in 30 seconds.')
        sleep(30)

    for post in posts:
        get_best_comments(post, 3)

    comments_amount = len(comment_dictionary_message)

    # Check if dictionary is empty.
    if comment_dictionary_message:
        print('Grabbed ' + str(comments_amount) + ' comments from Reddit!')
        send_to_sentiment_analysis(
            comment_dictionary_message, comments_amount)
    else:
        print('No comments found. Exiting...')
        exit(1)


# Source: https://www.reddit.com/r/redditdev/comments/9ijv1q/how_can_i_print_just_the_first_5_top_comments_of/
def get_best_comments(submission, limit):
    # Set comment sort to best before retrieving comments
    submission.comment_sort = 'best'
    # Limit top level comments
    submission.comment_limit = limit
    # Fetch the comments and print each comment body
    for top_level_comment in submission.comments:
        if isinstance(top_level_comment, praw.models.MoreComments):
            continue
        if top_level_comment.id:
            comment_dictionary_reply[top_level_comment.id] = top_level_comment.body
        if top_level_comment.author:
            comment_dictionary_message[top_level_comment.author.name] = top_level_comment.body


# Source: https://www.reddit.com/r/redditdev/comments/9ijv1q/how_can_i_print_just_the_first_5_top_comments_of/
def top_posts_from_subreddit(reddit, sub_name):
    subreddit = reddit.subreddit(sub_name)
    top_posts = []
    # The default for the 'top' function is "top of all time".
    for post in subreddit.top('day'):
        top_posts.append(post)
    # up to, but no more than, 1000 submissions returned.
    return top_posts


def remove_newline_characters(text):
    new_text = text.replace("\n", "")
    return new_text


def strip_emoji(text):
    new_text = re.sub(emoji.get_emoji_regexp(), r"", text)
    return new_text


def send_to_sentiment_analysis(dictionary, comments_amount):
    count = 0
    # progress = 0
    interval_float = comments_amount / 100
    interval = math.ceil(interval_float)
    # Send to sentiment analysis API
    print('Sending ' + str(comments_amount) + ' to sentiment analysis...')
    progress_bar = create_progress_bar(comments_amount)

    for key, value in dictionary.items():
        text_no_emojis = strip_emoji(value)
        formatted_text = remove_newline_characters(text_no_emojis)
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
                if y >= 0.7:
                    filtered_dictionary[key] = value
        else:
            continue

        time.sleep(0.1)
        progress = int(count)
        progress_bar.update(progress)
    print("\n")
    print('Done!')


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
    count = 0
    if watson_count < 88 and watson_count > 0:
        print('Sending to Watson...')
        progress_bar = create_progress_bar(watson_count)
        for key, value in filtered_dictionary.items():
            comment_text = value
            tone = service.tone({'text': comment_text},
                                content_type='application/json'
                                ).get_result()
            count = count + 1
            progress = int(count)
            progress_bar.update(progress)
            tmp = tone['document_tone']['tones']
            for x in tmp:
                tone_name = x['tone_name']
                score = x['score']
                if tone_name == 'Sadness':
                    filtered_dictionary_watson[value] = tone_name
                # print(tone_name)
                # print(score)
        # print(json.dumps(tone, indent=2))

    else:
        print("We can't send a file that big...this is awkward...")
        exit(1)


# Main
watson_service = setup_watson_service()
reddit_grab_posts(reddit_username, reddit_password, comment_dictionary_reply,
                  comment_dictionary_message)
json_filename = create_filename_for_json()
file_path = '../resources/' + json_filename
dump_dict_to_json(filtered_dictionary, json_filename)
watson_count = len(filtered_dictionary)
send_to_watson(watson_service)
pretty_printer.pprint(filtered_dictionary_watson)
