import os
import time
from datetime import datetime
from importlib import reload
from random import random
from threading import Thread

from fbchat import Client, Message, log

import utils
# a global, FIFO queue that contains action objects added by utils.py
from config import action_queue, reminders

username = os.environ.get('SLACKIFY_USERNAME')
password = os.environ.get('SLACKIFY_PASSWORD')
secret_key = os.environ.get('SLACKIFY_SECRET_KEY')
reset_message = '!reset ' + secret_key
BASE_WAIT = 0.2 # minimum wait time between actions


# Subclass fbchat.Client and override required methods
class SlackifyBot(Client):
    def onMessage(self, author_id, message_object, thread_id, thread_type, **kwargs):
        self.markAsDelivered(thread_id, message_object.uid)
        self.markAsRead(thread_id)

        log.info("{} from {} in {}".format(message_object, thread_id, thread_type.name))

        if author_id != self.uid:
            if message_object.text:
                if message_object.text == reset_message:
                    log.info("resetting bot... {}".format(datetime.now()))
                    self.send(Message(text="resetting bot... {}".format(datetime.now())), thread_id=thread_id, thread_type=thread_type)
                    reload(utils)
                    while not action_queue.empty():
                        print("Cleaning queue...")
                        _ = action_queue.get()
                else:
                    utils.command_handler(self, author_id, message_object, thread_id, thread_type)
    
    def onPollVoted(self, author_id, poll, thread_id, thread_type, **kwargs):
        log.info("{} voted in poll {} in {} ({})".format(author_id, poll, thread_id, thread_type.name))
        
        utils.vote_handler(self, author_id, poll, thread_id, thread_type)
    
    def onPollCreated(self, author_id, poll, thread_id, thread_type, **kwargs):
        log.info("{} created poll {} in {} ({})".format(author_id, poll, thread_id, thread_type.name))
        
        utils.new_poll_handler(self, author_id, poll, thread_id, thread_type)
    
    def onTitleChange(self, author_id, new_title, thread_id, thread_type, **kwargs):
        log.info("Title change from {} in {} ({}): {}".format(author_id, thread_id, thread_type.name, new_title))
        utils.title_change_handler(self, author_id, new_title, thread_id, thread_type)
    
    def onImageChange(self, author_id, new_image, thread_id, thread_type, **kwargs):
        log.info("{} changed thread image in {}".format(author_id, thread_id))
        utils.image_change_handler(self, author_id, new_image, thread_id, thread_type)
    
    def onNicknameChange(self, author_id, changed_for, new_nickname, thread_id, thread_type, **kwargs):
        log.info(
            "Nickname change from {} in {} ({}) for {}: {}".format(
                author_id, thread_id, thread_type.name, changed_for, new_nickname
            )
        )
        utils.nickname_handler(self, author_id, changed_for, new_nickname, thread_id, thread_type)
    
    def onPeopleAdded(self, added_ids, author_id, thread_id, **kwargs):
        log.info(
            "{} added: {} in {}".format(author_id, ", ".join(added_ids), thread_id)
        )
        utils.person_added_handler(self, added_ids, author_id, thread_id)
    
    def onPersonRemoved(self, removed_id, author_id, thread_id, **kwargs):
        log.info("{} removed: {} in {}".format(author_id, removed_id, thread_id))
        utils.person_removed_handler(self, removed_id, author_id, thread_id)
    
    def onFriendRequest(self, from_id, msg):
        log.info("Friend request from {}".format(from_id))
        utils.fr_handler(self, from_id, msg)
    
    def onReactionAdded(self, mid, reaction, author_id, thread_id, thread_type, **kwargs):
        log.info(
            "{} reacted to message {} with {} in {} ({})".format(
                author_id, mid, reaction.name, thread_id, thread_type.name
            )
        )
        utils.reaction_added_handler(self, mid, reaction, author_id, thread_id, thread_type)
    
    def onReactionRemoved(self, mid, author_id, thread_id, thread_type, ts, msg):
        log.info(
            "{} removed reaction from {} message in {} ({})".format(
                author_id, mid, thread_id, thread_type
            )
        )
        utils.reaction_removed_handler(self, mid, author_id, thread_id, thread_type, ts, msg)
    
    def onChatTimestamp(self, buddylist, msg):
        log.debug("Chat Timestamps received: {}".format(buddylist))
        utils.timestamp_handler(self, buddylist, msg)

def check_reminders():
    global reminders
    global action_queue
    while True:
        curr_time = datetime.now().replace(microsecond=0)
        if curr_time in reminders:
            _ = [action_queue.put(reminders[curr_time][i]) for i in range(len(reminders[curr_time]))]
            del reminders[curr_time]
        time.sleep(1)

def listening_loop():
    """Constantly checks for new activity on client's account."""
    client = SlackifyBot(str(username), str(password))
    try:
        client.listen()
        print("Thread listening....")
    except KeyboardInterrupt:
        # safely log out the client instead of just dropping the connection
        client.logout()

def action_loop():
    """Executes new actions as they become available."""
    global action_queue
    print("Starting actions...")
    while True:
        if not action_queue.empty():
            time.sleep(random() + BASE_WAIT)
            action_queue.get(block=False).run()
            action_queue.task_done()

if __name__ == '__main__':
    listener = Thread(name='listener', target=listening_loop)
    reminder = Thread(name='reminder', target=check_reminders)
    action = Thread(name='action', target=action_loop)
    listener.start()
    reminder.start()
    action.start()
