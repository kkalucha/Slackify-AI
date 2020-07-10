import time
import random
from datetime import datetime
from fbchat import log, Client, Message, Mention, ShareAttachment

def tag_all(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    mention_list = []
    message_text = '@all'
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        mention_list.append(Mention(thread_id=person.uid, offset=0, length=1))
    client.send(Message(text=message_text, mentions=mention_list), thread_id=thread_id, thread_type=thread_type)

def random_mention(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_list = []
    for person in Client.fetchAllUsersFromThreads(self= client, threads = [gc_thread]):
        person_list.append(person)
    chosen_number = random.randrange(0,len(person_list),1)
    chosen_person = person_list[chosen_number]
    person_name = chosen_person.first_name
    rand_mention = Mention(thread_id = chosen_person.uid, offset=0, length= len(person_name)+1)
    client.send(Message(text = "@" + person_name + " you have been chosen", mentions=[rand_mention]), thread_id=thread_id, thread_type=thread_type)

def random_image(client, author_id, message_object,thread_id,thread_type):
    client.sendRemoteImage("https://scontent-sjc3-1.xx.fbcdn.net/v/t1.0-9/31706596_988075581341800_8419953087938035712_o.jpg?_nc_cat=101&_nc_sid=e007fa&_nc_ohc=6WKPJKXT4yQAX8izxEX&_nc_ht=scontent-sjc3-1.xx&oh=dd30e0dc74cffd606248ef9151576fe2&oe=5F2E0EBC",message=Message(text='This should work'), thread_id=thread_id, thread_type=thread_type)
def hear_meet(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    date = datetime.strptime(message_object.text.split(' ')[1], '%m/%d/%y')

    message_text = 'Meeting at' + date.strftime('%A, %m/%d/%y') +'. Who\'s in?'
    client.send(Message(text=message_text), thread_id=thread_id, thread_type=thread_type)

def laugh(client, author_id, message_object, thread_id, thread_type):
    """Laughs."""
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    client.sendLocalVoiceClips(clip_paths="resources/laugh.aac", thread_id=thread_id, thread_type=thread_type)

def kick(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_kick = message_object.text.split(' ')[1:]
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        names = [person.first_name, person.last_name, person.nickname]
        if any([name in person_to_kick for name in names]):
            log.info("{} removed {} from {}").format(author_id, person_to_kick, thread_id)
            Client.removeUserFromGroup(user_id=person.uid, thread_id=thread_id)
            return
    log.info("Unable to remove: person not found.")

command_lib = {"all" : {"func" : tag_all}, 
                "kick" : {"func" : kick}, 
                "meet" : {"func" : hear_meet},
                "laugh" : {"func" : laugh},
                "randomp" : {"func": random_mention},
                "randomi" : {"func": random_image}
                }

def command_handler(client, author_id, message_object, thread_id, thread_type):
    if message_object.text.split(' ')[0][0] == '!':
        command = command_lib.get(message_object.text.split(' ')[0][1:])
        if command is not None:
            command["func"](client, author_id, message_object, thread_id, thread_type)
