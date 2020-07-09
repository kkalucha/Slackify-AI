import os
from fbchat import log, Client, Message
from importlib import reload
import utils
from datetime import datetime

username = os.environ.get('SLACKIFY_USERNAME')
password = os.environ.get('SLACKIFY_PASSWORD')
secret_key = os.environ.get('SLACKIFY_SECRET_KEY')
reset_message = '!reset ' + secret_key

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
                else:
                    utils.command_handler(self, author_id, message_object, thread_id, thread_type)

client = SlackifyBot(str(username), str(password))
client.listen()
