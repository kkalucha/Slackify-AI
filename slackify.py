import os

username = os.environ.get('SLACKIFY_USERNAME')
password = os.environ.get('SLACKIFY_PASSWORD')

print(username, password)