import sched
import time
from datetime import datetime
import utils

from fbchat import Message, log, Client, ThreadType, MessageReaction, Poll

class Action:
    """
    Object for any command actions initiated in utils.
    """
    
    def __init__(self, client, command_type, thread_id, thread_type, **kwargs):
        self.client = client
        self.command_type = command_type
        self.thread_id = thread_id
        self.thread_type = thread_type
        self.args = kwargs
    
    def run(self):
        action_map = {"message" : self.send_message, 
            'reaction' : self.react_to_message,
            'makeadmin' : self.add_as_admin,
            'makepoll' : self.create_poll,
            'voiceclip' : self.send_voice_clip,
            'image' : self.send_image,
            'removeuser' : self.remove_user,
            'makefriend' : self.add_friend,
            'forward' : self.forward_attachment}
        action_map[self.command_type]()
    
    def send_message(self):
        """
        args: {
            'text': text of message,
            'mentions': list of Mention objects (=None if none)
        }
        """
        if 'mentions' in self.args:
            (self.client).send(Message(text=self.args['text'], mentions=self.args['mentions']), thread_id=self.thread_id, thread_type=self.thread_type)
        else:
            (self.client).send(Message(text=self.args['text'], mentions=None), thread_id=self.thread_id, thread_type=self.thread_type)
    
    def react_to_message(self):
        """
        args: {
            'mid': message ID,
            'reaction': fbchat.MessageReaction enum object of desired reaction
        }
        """
        (self.client).reactToMessage(self.args['mid'], self.args['reaction'])
    
    def add_as_admin(self):
        """
        args: {
            pid: person id to add as group admin
        }
        """
        (self.client).addGroupAdmins(self.args['pid'], thread_id=self.thread_id)
    
    def create_poll(self):
        """
        args: {
            poll: fbchat.Poll instance
        }
        """
        (self.client).createPoll(poll=self.args['poll'], thread_id=self.thread_id)
    
    def send_voice_clip(self):
        """
        args: {
            clipPath: path to audio file
        }
        """
        (self.client).sendLocalVoiceClips(clip_paths=self.args['clipPath'], thread_id=self.thread_id, thread_type=self.thread_type)
    
    def send_image(self):
        """
        args: {
            imagePath: path to image file
        }
        """
        (self.client).sendLocalImage(self.args['imagePath'], thread_id=self.thread_id, thread_type=self.thread_type)
    
    def remove_user(self):
        """
        args: {
            pid: user id to remove
        }
        """
        (self.client).removeUserFromGroup(self.args['pid'], thread_id=self.thread_id)
    
    def add_friend(self):
        """
        args: {
            pid: user id of person to friend
        }
        """
        Client.friendConnect(self.client, self.args['pid'])
    
    def forward_attachment(self):
        """
        args: {
            attachmentID: id of message to forward
        }
        """
        (self.client).forwardAttachment(self.args['attachmentID'], self.thread_id)
