import time
from datetime import datetime, date
from dateparser import parse
import wikipedia
from fbchat import log, Client, Message, Mention, Poll, PollOption, ThreadType

meeting_polls = {}
CONSENSUS_THRESHOLD = 0.5

def tag_all(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    mention_list = []
    message_text = '@all'
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        mention_list.append(Mention(thread_id=person.uid, offset=0, length=1))
    client.send(Message(text=message_text, mentions=mention_list), thread_id=thread_id, thread_type=thread_type)

def hear_meet(client, author_id, message_object, thread_id, thread_type):
    today = date.today() + datetime.timedelta(days=1)
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    date = parse(message_object.text.split(' ', 1)[1])
    # parsing date failed
    if isinstance(date, type(None)):
        client.send(Message(text='I can\'t read that date.'), thread_id=thread_id, thread_type=thread_type)
        return
    if date < today:
        client.send(Message(text='I\'m not stupid that date has passed.'), thread_id=thread_id, thread_type=thread_type)
        return
    time_options = ['10AM', '12PM', '2PM', '4PM', '6PM', '8PM', '10PM', 'Can\'t make it']
    meeting = Poll(title=f"Meeting on {datetime.strftime(date, '%A, %x')}. Who's in?", options=[PollOption(text=time) for time in time_options])
    client.createPoll(poll=meeting, thread_id=thread_id)
    client.tag_all(client, author_id, None, thread_id, thread_type)
    meeting_polls[meeting] = {"date" : date}

def handle_meeting_vote(client, author_id, poll, thread_id, thread_type):
    global meeting_polls
    global CONSENSUS_THRESHOLD
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    
    # update meeting_polls by checking today's date, and prune any that've passed
    today = date.today() + datetime.timedelta(days=1)
    for poll, properties in zip(meeting_polls):
        if properties['date'] < today:
            meeting_polls.pop(poll)
    
    # check poll for consensus, i.e majority of users. If so, send update and deactivate poll
    n_users = float(len(Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread])))
    check_consensus = lambda votes: (votes / n_users) >= CONSENSUS_THRESHOLD
    consensus = [check_consensus(float(option.votes_count)) for option in client.fetchPollOptions(poll.uid)]
    if any(consensus[:-1]): # meeting is happening
        meeting_time = client.fetchPollOptions(poll.uid)[consensus.index(True)].text
        meeting_date = datetime.strftime(meeting_polls[poll]['date'], '%A, %x')
        client.send(Message(text=f'Consensus reached! Meeting at {meeting_time} on {meeting_date}'), thread_id=thread_id, thread_type=thread_type)
        return
    elif consensus[-1]: # meeting is not happening
        client.send(Message(text=f'Consensus reached! Meeting at {meeting_time} isn\'t happening.'), thread_id=thread_id, thread_type=thread_type)
        return
    else:
        log.info(f"No consensus on poll {poll.uid} yet.")

def wiki(client, author_id, message_object, thread_id, thread_type):
    """Checks wikipedia for term."""
    try:
        search_term = message_object.text.split(' ', 1)[1]
        search_result = Message(text=wikipedia.summary(search_term, sentences=2))
    except:
        client.send(Message(text='Invalid search term.'), thread_id=thread_id, thread_type=thread_type)
        return
    if len(search_term) == 0:
        client.send(Message(text='You didn\'t give me anything to search dipshit.'), thread_id=thread_id, thread_type=thread_type)
        return
    client.send(search_result, thread_id=thread_id, thread_type=thread_type)

def laugh(client, author_id, message_object, thread_id, thread_type):
    """Laughs."""
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    client.sendLocalVoiceClips(clip_paths="resources/laugh.aac", thread_id=thread_id, thread_type=thread_type)

def kick(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_kick = message_object.text.split(' ', 1)[1]
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

command_lib = {"all" : {"func" : tag_all}, 
                "kick" : {"func" : kick}, 
                "meet" : {"func" : hear_meet},
                "laugh" : {"func" : laugh},
               "sully" : {"func" : sully_comment},
               "pranshu" : {"func" : pranshu_comment},
                "ap" : {"func" : ap_comment},
                "aru" : {"func" : aru_comment},
                "kanav" : {"func" : kanav_comment},
                "removeme" : {"func" : removeme},
                "wiki" : {"func" : wiki}}

def command_handler(client, author_id, message_object, thread_id, thread_type):
    if message_object.text.split(' ')[0][0] == '!':
        command = command_lib.get(message_object.text.split(' ')[0][1:])
        if command is not None:
            command["func"](client, author_id, message_object, thread_id, thread_type)

def vote_handler(client, author_id, poll, thread_id, thread_type):
    """Routes actions after a poll is voted on."""
    # poll was a meeting poll
    if poll in list(meeting_polls.keys()):
        handle_meeting_vote(client, author_id, poll, thread_id, thread_type)
