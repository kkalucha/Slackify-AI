import time
from datetime import datetime
from fbchat import log, Client, Message, Mention

def tag_all(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    mention_list = []
    message_text = '@all'
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        mention_list.append(Mention(thread_id=person.uid, offset=0, length=1))
    client.send(Message(text=message_text, mentions=mention_list), thread_id=thread_id, thread_type=thread_type)

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

def ap_comment(client, author_id, message_object, thread_id, thread_type):
    client.send(Message(text="yOu CaN't AuToMaTe HeAlThCaRe"), thread_id=thread_id, thread_type=thread_type)
    
def sully_comment(client, author_id, message_object, thread_id, thread_type):
    client.send(Message(text="i Am NoT ___ gUyS I swEAr"), thread_id=thread_id, thread_type=thread_type)
    
def pranshu_comment(client, author_id, message_object, thread_id, thread_type):
    client.send(Message(text="Pranshu is a student at the University of Illinois Urbana-Champaign studying Computer Science and Statistics. My interests lie in High Performance Computing (HPC) and in AI/Deep Learning. Recently I attended the Super Computing 19 conference where I represented my school as a member of the University of Illinois Student Cluster Competition team; our team won 2nd place nationwide. I've recently also won 2nd place at the National Center for Supercomputing Applications Deep Learning Hackathon. At the Technology Student Association’s national conference in June, 2019, my team won 1st place out of over 75 teams in a research presentation competition on exploring a novel application of artificial intelligence in a domain field (website: pinkai.tech). I am an enthusiastic candidate for any role relating to HPC or Deep Learning; I hope to expand my skill set in the summer of 2020 through an internship at a company focusing on these disciplines. "), thread_id=thread_id, thread_type=thread_type)

def aru_comment(client, author_id, message_object, thread_id, thread_type):
    client.send(Message(text="Commit pushed to origin master"), thread_id=thread_id, thread_type=thread_type)

def removeme(client, author_id, message_object, thread_id, thread_type):
    if message_object.text == "!removeme" and thread_type == ThreadType.GROUP:
        log.info("{} will be removed from {}".format(author_id, thread_id))
        client.removeUserFromGroup(author_id, thread_id=thread_id)

command_lib = {"all" : {"func" : tag_all}, 
                "kick" : {"func" : kick}, 
                "meet" : {"func" : hear_meet},
                "laugh" : {"func" : laugh},
               "sully" : {"func" : sully_comment},
               "pranshu" : {"func" : pranshu_comment},
                "ap" : {"func" : ap_comment},
                "aru" : {"func" : aru_comment},
                "removeme" : {"func" : removeme}}

def command_handler(client, author_id, message_object, thread_id, thread_type):
    if message_object.text.split(' ')[0][0] == '!':
        command = command_lib.get(message_object.text.split(' ')[0][1:])
        if command is not None:
            command["func"](client, author_id, message_object, thread_id, thread_type)
