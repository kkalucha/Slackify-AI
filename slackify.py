import os
import time
from datetime import datetime
from fbchat import log, Client, Message, Mention

username = os.environ.get('SLACKIFY_USERNAME')
password = os.environ.get('SLACKIFY_PASSWORD')

# Subclass fbchat.Client and override required methods
class EchoBot(Client):

    def tag_all(self, author_id, message_object, thread_id, thread_type, **kwargs):
        gc_thread = Client.fetchThreadInfo(self, thread_id)[thread_id]
        mention_list = []
        message_text = '@all'
        for person in Client.fetchAllUsersFromThreads(self=self, threads=[gc_thread]):
            mention_list.append(Mention(thread_id=person.uid, offset=0, length=1))
        self.send(Message(text=message_text, mentions=mention_list), thread_id=thread_id, thread_type=thread_type)

    def hear_meet(self, author_id, message_object, thread_id, thread_type, **kwargs):
        gc_thread = Client.fetchThreadInfo(self, thread_id)[thread_id]
        date = datetime.strptime(message_object.text.split(' ')[1], '%m/%d/%y')

        message_text = 'Meeting at' + strfrtime(date, '%A, %m/%d/%y') +'. Who\'s in?'
        self.send(Message(text=message_text), thread_id=thread_id, thread_type=thread_type)

    def onMessage(self, author_id, message_object, thread_id, thread_type, **kwargs):
        self.markAsDelivered(thread_id, message_object.uid)
        self.markAsRead(thread_id)

        log.info("{} from {} in {}".format(message_object, thread_id, thread_type.name))

        function_lib = {"all" : self.tag_all, "meet" : self.hear_meet}
        # If you're not the author, echo
        if author_id != self.uid:
            if message_object.text and message_object.text.split(' ')[0][0] == '!':
                function_called = function_lib.get(message_object.text.split(' ')[0][1:])
                if function_called is not None:
                    function_called(author_id, message_object, thread_id, thread_type)
            #self.send(message_object, thread_id=thread_id, thread_type=thread_type)

        

client = EchoBot(str(username), str(password))
client.listen()
