import time
import random
from datetime import datetime
from dateparser import parse
import wikipedia
from fbchat import log, Client, Message, Mention, Poll, PollOption, ThreadType, ShareAttachment

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
    today = datetime.today()
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    try:
        date = parse("".join(message_object.text.split(' ')[1:]))
    except ValueError: # date not found in string
        client.send(Message(text='Oi you forgot the date dingus'), thread_id=thread_id, thread_type=thread_type)
        return
    if isinstance(date, type(None)):
        client.send(Message(text='I can\'t read that.'), thread_id=thread_id, thread_type=thread_type)
    if date < today:
        client.send(Message(text='I\'m not stupid that date has passed.'), thread_id=thread_id, thread_type=thread_type)
    time_options = ['10AM', '12PM', '2PM', '4PM', '6PM', '8PM', '10PM', 'Can\'t make it']
    meeting = Poll(title=f"Meeting on {datetime.strftime(date, '%A, %x')}. Who's in?", options=[PollOption(text=time) for time in time_options])
    client.createPoll(poll=meeting, thread_id=thread_id)
    client.tag_all(client, author_id, None, thread_id, thread_type)

def wiki(client, author_id, message_object, thread_id, thread_type):
    """Checks wikipedia for term."""
    try:
        search_term = "".join(message_object.text.split(" ")[1:])
        search_result = Message(text=wikipedia.summary(search_term, sentences=2))
    except wikipedia.exceptions.PageError:
        client.send(Message(text='Invalid search term.'), thread_id=thread_id, thread_type=thread_type)
        return
    except wikipedia.exceptions.WikipediaException:
        client.send(Message(text='You didn\'t give me anything to search dipshit.'), thread_id=thread_id, thread_type=thread_type)
        return
    client.send(search_result, thread_id=thread_id, thread_type=thread_type)

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
            log.info("{} removed {} from {}".format(author_id, person_to_kick, thread_id))
            client.removeUserFromGroup(person.uid, thread_id=thread_id)
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

def kanav_comment(client, author_id, message_object, thread_id, thread_type):
    client.send(Message(text="If you commit to master I will kILL you"), thread_id=thread_id, thread_type=thread_type)

def removeme(client, author_id, message_object, thread_id, thread_type):
    print("{} will be removed from {}".format(author_id, thread_id))
    client.removeUserFromGroup(author_id, thread_id=thread_id)
                   
def kick_random(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_kick = message_object.text.split(' ')[1:]
    persons_list = Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread])
    
    num = random.randint(0, len(persons_list) + 3*len(persons_list)/3) #random number within range
    if (num > len(persons_list)-1):
        to_kick = author_id
    person = persons_list[num]

    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        if (person.uid == to_kick):
            person = person

    log.info("{} removed {} from {}".format(author_id, "random", thread_id))
    client.removeUserFromGroup(person.uid, thread_id=thread_id)
    return
    log.info("Unable to remove: person not found.")

command_lib = {"all" : {"func" : tag_all}, 
                "kick" : {"func" : kick}, 
                "meet" : {"func" : hear_meet},
                "laugh" : {"func" : laugh},
                "randomp" : {"func": random_mention},
                "randomi" : {"func": random_image},
                "sully" : {"func" : sully_comment},
                "pranshu" : {"func" : pranshu_comment},
                "ap" : {"func" : ap_comment},
                "aru" : {"func" : aru_comment},
                "kanav" : {"func" : kanav_comment},
               "kickr" : {"func" : kick_random},
                "removeme" : {"func" : removeme},
                "wiki" : {"func" : wiki}}

def command_handler(client, author_id, message_object, thread_id, thread_type):
    if message_object.text.split(' ')[0][0] == '!':
        command = command_lib.get(message_object.text.split(' ')[0][1:])
        if command is not None:
            command["func"](client, author_id, message_object, thread_id, thread_type)
