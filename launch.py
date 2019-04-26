#!/usr/bin/env python

import os
import pathlib
import subprocess
import time
import argparse
from apiclient import discovery, errors
from oauth2client import client, file
from httplib2 import ServerNotFoundError

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--prefix', default='\uf0e0')
parser.add_argument('-c', '--color', default='#e06c75')
parser.add_argument('-ns', '--nosound', action='store_true')
parser.add_argument('-t', '--title', action='store_true',
    help='When provided, subject of newest email is also displayed')
parser.add_argument('--title-format', default=': %s',
    help='When title is enabled, this option specifies its format')
parser.add_argument('-e', '--tenant', default='default',
    help='Identifier of credential file that should be used')
args = parser.parse_args()

DIR = os.path.dirname(os.path.realpath(__file__))
CREDENTIALS_PATH = os.path.join(DIR, 'credentials-{}.json'.format(args.tenant))

unread_prefix = '%{F' + args.color + '}' + args.prefix + ' %{F-}'
error_prefix = '%{F' + args.color + '}\uf06a %{F-}'
count_was = 0

def get_subject(message):
    headers = message['payload']['headers']
    return next(h for h in headers if h["name"] == "Subject")["value"]

def format_count(count, is_odd=False):
    tilde = '~' if is_odd else ''
    output = ''
    if count > 0:
        output = unread_prefix + tilde + str(count)
    else:
        output = (args.prefix + ' ' + tilde).strip()
    return output

def update_count(count_was):
    gmail = discovery.build('gmail', 'v1', credentials=file.Storage(CREDENTIALS_PATH).get())

    messagesQuery = gmail.users().messages().list(userId='me', q="is:unread").execute()
    count = messagesQuery["resultSizeEstimate"]

    out = format_count(count)

    if count > 0 and args.title:
        messages = messagesQuery["messages"]
        message = gmail.users().messages().get(
                userId='me',
                id=messages[0]['id'],
                format='metadata',
                metadataHeaders=['Subject']).execute()
        out += args.title_format % get_subject(message)

    if not args.nosound and count_was < count and count > 0:
        subprocess.run(['canberra-gtk-play', '-i', 'message'])

    print(out, flush=True)
    return count

def print_prev():
    print(format_count(count_was), flush=True)


print_prev()

while True:
    try:
        if pathlib.Path(CREDENTIALS_PATH).is_file():
            count_was = update_count(count_was)
            time.sleep(10)
        else:
            print(error_prefix + 'credentials not found', flush=True)
            time.sleep(2)
    except (errors.HttpError, ServerNotFoundError, OSError) as error:
        print_prev()
        time.sleep(5)
    except client.AccessTokenRefreshError:
        print(error_prefix + 'revoked/expired credentials', flush=True)
        time.sleep(5)
