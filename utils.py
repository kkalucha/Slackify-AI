import copy
import json
import os
import random
import re
import time
import urllib
from datetime import date, datetime, timedelta
from hashlib import shake_256
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
import firebase_admin
import numpy as np
import requests
import wikipedia
from bs4 import BeautifulSoup
from dateparser import parse
from fbchat import (Client, FBchatException, Mention, Message, MessageReaction,
                    Poll, PollOption, ShareAttachment, ThreadType, log)
from firebase_admin import credentials, db
from fuzzywuzzy import fuzz, process
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import random 
from config import action_queue
from objects import Action

meeting_polls = {}
CONSENSUS_THRESHOLD = 0.5
time_options = ['10AM', '12PM', '2PM', '4PM', '6PM', '8PM', '10PM', 'Can\'t make it']
YELP_API_KEY = os.environ.get("YELP_API_KEY")
# emotionmap = {<MessageReaction object> : [[<pos>, <neutral>, <neg>], <n_messages>]}
emotionmap = {MessageReaction.HEART : [[1, 0, 0], 1],
            MessageReaction.SAD : [[0, 0, 1], 1],
            MessageReaction.SMILE : [[0.707, 0, 0.707], 1],
            MessageReaction.WOW : [[0.707, 0.707, 0], 1],
            MessageReaction.ANGRY : [[0, 0.707, 0.707], 1]}
reaction_history = {}
# anon_dict {hash(rand) : sender_id}
anon_dict = {}
# anon_target_dict {hash(rand): target_id}
anon_target_dict = {}

# Fetch the service account key JSON file contents
cred = credentials.Certificate(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

if not firebase_admin._apps:
    # Initialize the app with a custom auth variable, limiting the server's access for unauth users
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ.get("DATABASEURL"),
        'databaseAuthVariableOverride': {
            'uid': os.environ.get("WORKERID")
        }
    })

# The app only has access as defined in the Security Rules
groups_ref = db.reference('/groups')

def tag_all(client, author_id, message_object, thread_id, thread_type):
    """Tags everyone in the chat"""
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    mention_list = []
    message_text = '@all'
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        mention_list.append(Mention(thread_id=person.uid, offset=0, length=1))
    action_queue.put(Action(client, 'message', thread_id, thread_type, text=message_text, mentions=mention_list))

def random_mention(client, author_id, message_object, thread_id, thread_type):
    """Tags a random person"""
    random.seed(time.time())
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_list = []
    for person in Client.fetchAllUsersFromThreads(self= client, threads = [gc_thread]):
        person_list.append(person)
    chosen_number = random.randrange(0,len(person_list),1)
    chosen_person = person_list[chosen_number]
    person_name = chosen_person.first_name
    rand_mention = Mention(thread_id = chosen_person.uid, offset=0, length= len(person_name)+1)
    action_queue.put(Action(client, 'message', thread_id, thread_type, 
        text="@" + person_name + " you have been chosen", mentions=[rand_mention]))

def admin(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_admin = message_object.text.split(' ', 1)[1]
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        if person_to_admin.lower() in person.name.lower():
            log.info("{} added as admin {} from {}".format(author_id, person_to_admin, thread_id))
            action_queue.put(Action(client, 'makeadmin', thread_id, thread_type, pid=person.uid))
            return
    log.info("Unable to add admin: person not found.")
   
def hear_meet(client, author_id, message_object, thread_id, thread_type):
    """Creates poll to decide on time for given date"""
    global meeting_polls
    global time_options
    
    today = date.today()
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    try:
        msg_date = parse(message_object.text.split(' ', 1)[1])
        assert(not isinstance(msg_date, type(None)))
        if msg_date.date() < today:
            raise ValueError
    except (IndexError, AssertionError) as e:
        action_queue.put(Action(client, 'message', thread_id, thread_type, 
            text='I can\'t read that date.'))
        return
    except ValueError:
        action_queue.put(Action(client, 'message', thread_id, thread_type, 
            text='I\'m not stupid that date has passed.'))
        return
    meeting = Poll(title=f"Meeting on {datetime.strftime(msg_date, '%A, %x')}. Who's in?", options=[PollOption(text=time) for time in time_options])
    action_queue.put(Action(client, 'makepoll', thread_id, thread_type, poll=meeting))
    tag_all(client, author_id, None, thread_id, thread_type)

def yelp_search(client, author_id, message_object, thread_id, thread_type):
    inputs_array = message_object.text.split(' ', 1)[1].split("in", 1)
    keyword = inputs_array[0]
    location = inputs_array[1]
    def request(host, path, api_key, url_params=None):
        """Given your API_KEY, send a GET request to the API.
        Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        API_KEY (str): Your API Key.
        url_params (dict): An optional set of query parameters in the request.
        Returns:
        dict: The JSON response from the request.
        Raises:
        HTTPError: An error occurs from the HTTP request.
        """
        url_params = url_params or {}
        url = '{0}{1}'.format(host, quote(path.encode('utf8')))
        headers = {
        'Authorization': 'Bearer %s' % api_key,}
        print(u'Querying {0} ...'.format(url))
        response = requests.request('GET', url, headers=headers, params=url_params)
        return response.json()
    SEARCH_LIMIT = 5
    API_HOST = 'https://api.yelp.com'
    SEARCH_PATH = '/v3/businesses/search'
    BUSINESS_PATH = '/v3/businesses/' 
    url_params = {
        'term': keyword.replace(' ', '+'),
        'location': location.replace(' ', '+'),
        'limit': SEARCH_LIMIT
    }

    def result_parser(result): 
        whole_text = ""
        for business in result["businesses"]:
            attributes = ["name", "location","price","rating"]
            for name in attributes: 
                if name in business:
                    if (name == "location"):
                        if "display_address" in business["location"] and len(business["location"]["display_address"]) != 0:
                            whole_text += name.capitalize() + ": " + " ".join(business["location"]["display_address"]) + "\n"
                    else:
                        whole_text += name.capitalize() + ": " + str(business[name]) + "\n"
            whole_text += "\n\n"
        return whole_text
    result_dict = request(API_HOST, SEARCH_PATH, YELP_API_KEY, url_params=url_params)
    returnString = json.dumps(result_dict)
    returnText = result_parser(result_dict)
    action_queue.put(Action(client, 'message', thread_id, thread_type, text=returnText))

def handle_meeting_vote(client, author_id, poll, thread_id, thread_type):
    global meeting_polls
    global CONSENSUS_THRESHOLD
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    
    # update meeting_polls by checking today's date, and prune any that've passed
    today = date.today()
    for poll_uid in list(meeting_polls.keys()):
        if meeting_polls[poll_uid]['date'].date() < today:
            meeting_polls.pop(poll_uid)
    
    # check poll for consensus, i.e majority of users. If so, send update and deactivate poll
    n_users = float(len(Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread])))
    check_consensus = lambda votes: (votes / n_users) >= CONSENSUS_THRESHOLD
    consensus = [check_consensus(float(option.votes_count)) for option in client.fetchPollOptions(poll.uid)]
    if any(consensus[:-1]): # meeting is happening
        meeting_time = client.fetchPollOptions(poll.uid)[consensus.index(True)].text
        meeting_date = datetime.strftime(meeting_polls[poll.uid]['date'], '%A, %x')
        action_queue.put(Action(client, 'message', thread_id, thread_type, 
            text=f'Consensus reached! Meeting at {meeting_time} on {meeting_date}'))
        return
    elif consensus[-1]: # meeting is not happening
        action_queue.put(Action(client, 'message', thread_id, thread_type, 
            text=f'Consensus reached! Meeting at {meeting_time} isn\'t happening.'))
        return
    else:
        log.info(f"No consensus on poll {poll.uid} yet.")

def wiki(client, author_id, message_object, thread_id, thread_type):
    """Checks wikipedia for term"""
    try:
        search_term = message_object.text.split(' ', 1)[1]
        search_result = wikipedia.summary(search_term, sentences=2)
    except wikipedia.exceptions.WikipediaException:
        action_queue.put(Action(client, 'message', thread_id, thread_type, 
            text='Invalid search term.'))
        return
    except IndexError:
        action_queue.put(Action(client, 'message', thread_id, thread_type, 
            text='You didn\'t give me anything to search dipshit.'))
        return
    action_queue.put(Action(client, 'message', thread_id, thread_type, text=search_result))

def laugh(client, author_id, message_object, thread_id, thread_type):
    """Laughs"""
    action_queue.put(Action(client, 'voiceclip', thread_id, thread_type, clipPath="resources/laugh.aac"))

def kick(client, author_id, message_object, thread_id, thread_type):
    """Kicks the specified user from the chat"""
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_kick = message_object.text.split(' ', 1)[1]
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        if person_to_kick.lower() in person.name.lower():
            log.info("{} removed {} from {}".format(author_id, person_to_kick, thread_id))
            action_queue.put(Action(client, 'removeuser', thread_id, thread_type, pid=person.uid))
            return
    log.info("Unable to remove: person not found.")


def removeme(client, author_id, message_object, thread_id, thread_type):
    """Removes the person who calls this from the chat"""
    log.info("{} will be removed from {}".format(author_id, thread_id))
    action_queue.put(Action(client, 'removeuser', thread_id, thread_type, pid=author_id))

def kick_random(client, author_id, message_object, thread_id, thread_type):
    """Kicks a random person from the chat"""
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    persons_list = Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread])
    num = random.randint(0, len(persons_list)-1) #random number within range
    person = persons_list[num]
    log.info("{} removed {} from {}".format(author_id, "random", thread_id))
    action_queue.put(Action(client, 'removeuser', thread_id, thread_type, pid=person.uid))
    return
    log.info("Unable to remove: person not found.")
                   
#the message goes to spam by default if you aren't friends with the bot
def pm_person(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_pm = message_object.text.split(' ')[1:]
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        names = [person.first_name, person.last_name, person.nickname]
        if any([name in person_to_pm for name in names]):
            thread_id = person.uid
    action_queue.put(Action(client, 'message', thread_id, ThreadType.USER, text="hello friend"))

def return_self(client, author_id, message_object, thread_id, thread_type):
    """Echoes what you tell the bot to say"""
    action_queue.put(Action(client, 'message', thread_id, thread_type, text=message_object.text.split(' ',1)[1]))

def list_functions(client, author_id, message_object, thread_id, thread_type):
    """Lists all available functions"""
    message_string = "List of available functions:\n"
    for key in list(command_lib.keys()):
        if key != "help" and command_lib[key]["private"] == "N":
            message_string += str(key) + " - " + command_lib[key]['description'] + "\n"
    action_queue.put(Action(client, 'message', thread_id, thread_type, text=message_string))

def sentiment_react(client, author_id, message_object, thread_id, thread_type):
    global emotionmap
    pol = SentimentIntensityAnalyzer().polarity_scores(message_object.text)
    compound = pol['compound']
    pol = list(pol.values())[:-1][::-1]
    similarity = {np.dot(pol, emotionmap[i][0])/(np.linalg.norm(pol)*np.linalg.norm(emotionmap[i][0])) : i for i in emotionmap.keys()}
    # if emotion vector is +/- ~30 degrees from an emotion, send that reaction
    if sorted(list(similarity.keys()), reverse=True)[0] > 0.866 and np.absolute(compound) > 0.4:
        action_queue.put(Action(client, 'reaction', thread_id, thread_type, 
            mid=message_object.uid, reaction=similarity[sorted(list(similarity.keys()), reverse=True)[0]]))

def reset_emotions(client, author_id, message_object, thread_id, thread_type):
    global emotionmap
    global reaction_history
    default_emotions = {MessageReaction.HEART : [[1, 0, 0], 1],
                MessageReaction.SAD : [[0, 0, 1], 1],
                MessageReaction.SMILE : [[0.707, 0, 0.707], 1],
                MessageReaction.WOW : [[0.707, 0.707, 0], 1],
                MessageReaction.ANGRY : [[0, 0.707, 0.707], 1]}
    emotionmap = copy.deepcopy(default_emotions)
    reaction_history = {}
    action_queue.put(Action(client, 'message', thread_id, thread_type, text=f'Emotion memory reset at {datetime.now()}'))
    log.info(f'Emotion vectors: {emotionmap}')
    log.info(f'Reaction history: {reaction_history}')

def world_peace(client, author_id, message_object, thread_id, thread_type):
    """Creates world peace"""
    kick_random(client, author_id, message_object, thread_id, thread_type)
    action_queue.put(Action(client, 'image', thread_id, thread_type, imagePath="resources/worldpeace.gif"))

def pin(client, author_id, message_object, thread_id, thread_type):
    if Client.fetchThreadInfo(client, thread_id)[thread_id].type == ThreadType.USER:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="Pin only works in Group chats!"))
        return
    
    string_get = groups_ref.child(thread_id).child("string").get()
    pin_get = groups_ref.child(thread_id).child("pin_id").get()
    if message_object.replied_to == None:
        to_pin = message_object.text.split(' ')[1:]
        if not to_pin:
            action_queue.put(Action(client, 'message', thread_id, thread_type, text="Make sure you have something to pin!"))
            return
        if string_get is None:
            groups_ref.child(thread_id).set({"string": to_pin})
        else:
            groups_ref.child(thread_id).update({"string": to_pin})
        if pin_get != None:
            groups_ref.child(thread_id).child("pin_id").delete()
    else:
        if pin_get is None:
            groups_ref.child(thread_id).set({"pin_id": message_object.replied_to.uid})
        else:
            groups_ref.child(thread_id).update({"pin_id": message_object.replied_to.uid})

        if string_get != None:
                groups_ref.child(thread_id).child("string").delete()


def brief(client, author_id, message_object, thread_id, thread_type):
    if Client.fetchThreadInfo(client, thread_id)[thread_id].type == ThreadType.USER:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="Brief only works in Group chats!"))
        return
    
    string_get = groups_ref.child(thread_id).child("string").get()
    pin_get = groups_ref.child(thread_id).child("pin_id").get()
    
    if string_get is None and pin_get is None:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="You never pinned anything"))
    elif pin_get is None: 
        action_queue.put(Action(client, 'message', thread_id, thread_type, text=string_get))
    else:
        try :
            message_object = Client.fetchMessageInfo(client, mid=pin_get, thread_id=thread_id)
            print(message_object.attachments)
            if not message_object.attachments:
                action_queue.put(Action(client, 'message', thread_id, thread_type, text=message_object.text))
            else:
                for x in message_object.attachments:
                    action_queue.put(Action(client, 'forward', thread_id, thread_type, attachmentID=x.uid))
        except FBchatException:
            action_queue.put(Action(client, 'message', thread_id, thread_type, text="Your Pinned Message might not exist anymore"))

def urban_dict(client, author_id, message_object, thread_id, thread_type):
    """Returns query output from Urban Dictionary"""
    word = message_object.text.split(' ',1)[1]
    r = requests.get("http://www.urbandictionary.com/define.php?term={}".format(word))
    soup = BeautifulSoup(r.content, features="html.parser")
    action_queue.put(Action(client, 'message', thread_id, thread_type, text=soup.find("div",attrs={"class":"meaning"}).text))

def check_status(client, author_id, message_object, thread_id, thread_type):
    action_queue.put(Action(client, 'message', thread_id, thread_type, text="bot is live at {}".format(datetime.now())))

def didyoumean(input_command):
    return process.extract(input_command ,command_lib.keys(), scorer = fuzz.partial_ratio, limit = 1)[0][0]
    
def recite(client, author_id, message_object, thread_id, thread_type):
    action_queue.put(Action(client, 'message', thread_id, thread_type, text="1. A robot may not injure a human being or, through inaction, allow a human being to come to harm.\n" 
                        + "2. A robot must obey the orders given it by human beings except where such orders would conflict with the First Law.\n" 
                        + "3. A robot must protect its own existence as long as such protection does not conflict with the First or Second Laws"))

def make_friend(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_friend = message_object.text.split(' ', 1)[1]
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        if person_to_friend.lower() in person.name.lower():
            action_queue.put(Action(client, 'makefriend', thread_id, thread_type, pid=person.uid))

def send_anon(client, author_id, message_object, thread_id, thread_type):
    """
    Sends message to selected person.
    Format: !send [target] message
    """
    global anon_dict
    global anon_target_dict
    
    if thread_type != ThreadType.USER:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="Sorry, this feature only works in my PM."))
        return
    try:
        target = re.match(r"[^[]*\[([^]]*)\]", message_object.text).groups()[0]
        message = message_object.text.replace(f"[{target}]", "").split(" ", 1)[1][1:]
    except:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="Didn't give a message! Usage: !send [recipient name] message"))
        return
    # find recipient
    target = client.searchForUsers(target, limit=1)[0]
    if not target.is_friend:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text=f"I can't contact {target.first_name} {target.last_name}; I'm not friends with them."))
        return
    # add author to lookup table {sha256(author_id + salt) : author_id}
    anon_id = shake_256(str(int(author_id) + random.randint(-1e4,1e4)).encode('utf-8')).hexdigest(8)
    anon_dict[anon_id] = author_id
    anon_target_dict[anon_id] = target.uid
    # pm recipient
    action_queue.put(Action(client, 'message', target.uid, ThreadType.USER, text=f'New message from {anon_id}:\n{message}\nTo respond, copy/paste the template below and add in your response.'))
    action_queue.put(Action(client, 'message', target.uid, ThreadType.USER, text=f'!reply [{anon_id}] <your message here>'))
    action_queue.put(Action(client, 'message', thread_id, thread_type, text=f"Message sent from you ({anon_id}) to {target.first_name} {target.last_name}.\nReminder: you can end this chat session at any time by typing !end {target.first_name}"))
    log.info(anon_dict)
    log.info(anon_target_dict)

def reply_anon(client, author_id, message_object, thread_id, thread_type):
    """
    Replies to message from anonymous sender.
    Format: !reply [sender's id] message
    """
    global anon_dict
    global anon_target_dict
    
    if thread_type != ThreadType.USER:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="Sorry, this feature only works in my PM."))
        return
    try:
        target = re.match(r"[^[]*\[([^]]*)\]", message_object.text).groups()[0]
        message = message_object.text.replace(f"[{target}]", "").split(" ", 1)[1][1:]
    except:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="Didn't give a message! Usage: !reply [recipient name] message"))
        return
        
    # determine whether message is coming from sender or target
    if author_id in anon_target_dict.values(): # message is from a target -> target is a hexcode
        target_user = client.fetchUserInfo(author_id)[author_id]
        if target in anon_dict.keys():
            action_queue.put(Action(client, 'message', anon_dict[target], ThreadType.USER, text=f"Reply from {target_user.first_name}: {message}\nTo reply to them, type !reply [<their name here>] <your message here>"))
            action_queue.put(Action(client, 'message', thread_id, thread_type, text=f'Reply sent to {target}.'))
            return
        else: # chat session has been deleted
            action_queue.put(Action(client, 'message', thread_id, thread_type, text=f"You don't appear to have an active chat session with {target}. Use !send to start one."))
            return
    elif author_id in anon_dict.values(): # message is from a sender -> target is a name
        target_user = client.searchForUsers(target, limit=1)[0]
        # make sure sender and target have a session going
        for k, v in anon_dict.items():
            if v == author_id and anon_target_dict[k] == target_user.uid:
                action_queue.put(Action(client, 'message', target_user.uid, ThreadType.USER, text=f"Reply from {k}: {message}\nCopy/paste the template below to send a reply."))
                action_queue.put(Action(client, 'message', target_user.uid, ThreadType.USER, text=f"!reply [{k}] <reply here>"))
                action_queue.put(Action(client, 'message', thread_id, thread_type, text=f'Reply sent from you ({anon_id}) to {target_user.first_name}.'))
                return
        # if code reaches here there was no active session found
        action_queue.put(Action(client, 'message', thread_id, thread_type, text=f"You don't appear to have an active chat session with {target_user.first_name}. Use !send to start one."))
        return
    else:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="You don't have any active chat sessions open. Either use !send to deliver an anonymous message or wait for one to come to you."))
    log.info(anon_dict)
    log.info(anon_target_dict)

def end_anon(client, author_id, message_object, thread_id, thread_type):
    """
    Ends an anonymous chat session and destroys data.
    Format: !end <person name>
    """
    global anon_dict
    global anon_target_dict
    
    if thread_type != ThreadType.USER:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text='Please only do this in my PM.'))
        return
    
    try:
        target = message_object.text.split(' ', 1)[1]
        target_id = client.searchForUsers(target, limit=1)[0].uid
    except IndexError:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="Who do I end? Usage: !end <person name here>"))
        return 
    
    # make sure there's at least one active session between the sender and target
    author_chats = set([key for key, value in anon_dict.items() if value == author_id])
    target_chats = set([key for key, value in anon_target_dict.items() if value == target_id])
    common_chats = list(author_chats & target_chats)
    if len(common_chats) == 1:
        del anon_dict[common_chats[0]]
        del anon_target_dict[common_chats[0]]
        action_queue.put(Action(client, 'message', thread_id, thread_type, text=f'Session with {target} ended. All data deleted.'))
    elif len(common_chats) > 1:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text=f'Multiple active sessions with {target} detected. Deleting all {len(common_chats)} sessions...'))
        for hexcode in common_chats:
            del anon_dict[hexcode]
            del anon_target_dict[hexcode]
        action_queue.put(Action(client, 'message', thread_id, thread_type, text='All data deleted.'))
    else: # no chat sessions between sender and target
        action_queue.put(Action(client, 'message', thread_id, thread_type, text=f"You don't appear to have an active chat sessions with {target}. Use !send to start one."))
        
    log.info(anon_dict)
    log.info(anon_target_dict)


 
def coin_flip(client, author_id, message_object, thread_id, thread_type):
    coin_flip = random.choice([1,2])
    if coin_flip == 1:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="It turned up heads!"))
    else:
        action_queue.put(Action(client, 'message', thread_id, thread_type, text="You got tails!"))

#brew install poppler if on mac or pip install python-poppler on Ubuntu as in requirements.txt
def scenesfromahat(client, author_id, message_object, thread_id, thread_type):
    os.system("rm -rf scenesfromahat.pdf")
    os.system("rm -rf scenesfromahat.txt")
    os.system("wget https://docs.google.com/document/d/1Y3dCl8wC8Za_av1wN2GyJAquEoonE134ejjGIaJXzag/export?format=pdf -O scenesfromahat.pdf")
    os.system("pdftotext -layout scenesfromahat.pdf scenesfromahat.txt")
    with open("scenesfromahat.txt") as f:
        lines = f.readlines()
        action_queue.put(Action(client, 'message', thread_id, thread_type, text=random.choice(lines)))


        
command_lib = {"all" : {"func" : tag_all, "description" : "Tags everyone in the chat", "private":"N"}, 
                "kick" : {"func" : kick, "description" : "Kicks the specified user from the chat", "private":"N"}, 
                "meet" : {"func" : hear_meet, "description" : "Creates poll to decide on time for given date", "private":"N"},
                "laugh" : {"func" : laugh, "description" : "Laughs", "private":"N"},
                "randomp" : {"func": random_mention, "description" : "Tags a random person", "private":"N"},
                "kickr" : {"func" : kick_random, "description" : "Kicks a random person from the chat", "private":"N"},
                "removeme" : {"func" : removeme, "description" : "Removes the person who calls this from the chat", "private":"N"},
                "wiki" : {"func" : wiki, "description" : "Checks wikipedia for term", "private":"N"},
                "return": {"func": return_self, "description" : "Echoes what you tell the bot to say", "private":"Y"},
                "pm" : {"func" : pm_person, "description" : "PMs the given person", "private":"N"}, 
                "help": {"func": list_functions, "description" : "Lists all available functions","private":"N"},
                "admin": {"func": admin, "description": "Makes someone admin", "private":"N"},
                "yelp": {"func":yelp_search, "description": "Finds stores based on location and keyword", "private":"N"}, 
                "urbandict": {"func" : urban_dict, "description" : "Returns query output from Urban Dictionary", "private":"N"},
                "worldpeace" : {"func" : world_peace, "description" : "Creates world peace", "private":"N"},
                "status" : {"func" : check_status, "description" : "Returns the bot's status", "private":"Y"},
                "pin" : {"func" : pin, "description" : "pins a message: call !pin to store the following text or reply to an image/text with !pin", "private":"N"},
                "brief" : {"func" : brief, "description" : "returns your pinned image or text", "private":"N"},
                "recite" : {"func" : recite, "description" : "Recites the three laws", "private":"N"},
                "emotionreset" : {"func" : reset_emotions, "description" : "Resets emotion memory", "private":"Y"},
                "friend" : {"func" : make_friend, "description" : "Will accept the person's friend request", "private":"N"},
                "send" : {"func" : send_anon, "description" : "Sends anonymous message to specified person", "private":"N"},
                "reply" : {"func" : reply_anon, "description" : "Replies to anonymous message", "private":"N"},
                "end" : {"func" : end_anon, "description" : "Ends anonymous chat session", "private":"N"},
                "coin" : {"func" : coin_flip, "description" : "Flip a Coin!", "private":"Y"},
                "scenesfromahat" : {"func" : scenesfromahat, "description" : "Returns a random sentence from Scenes from a Hat","private":"Y"}
}

def command_handler(client, author_id, message_object, thread_id, thread_type):
    if message_object.text.split(' ')[0][0] == '!':
        command = command_lib.get(message_object.text.split(' ')[0][1:])
        if command is not None:
            command["func"](client, author_id, message_object, thread_id, thread_type)
        else:
            action_queue.put(Action(client, 'message', thread_id, thread_type, text="That command doesnt exist. Did you mean !" + str(didyoumean(message_object.text.split(' ')[0][1:]))))
    else:
        sentiment_react(client, author_id, message_object, thread_id, thread_type)	


def vote_handler(client, author_id, poll, thread_id, thread_type):
    """Routes actions after a poll is voted on."""
    global meeting_polls
    
    # poll is a meeting poll
    if poll.uid in list(meeting_polls.keys()):
        handle_meeting_vote(client, author_id, poll, thread_id, thread_type)

def new_poll_handler(client, author_id, poll, thread_id, thread_type):
    """Routes actions after a poll is created."""
    global meeting_polls
    global time_options
    
    log.info("New poll created!")
    if poll.title.split(" ", 1)[0] == "Meeting" and poll.options_count == len(time_options):
        meeting_polls[poll.uid] = {'date': parse(poll.title.split(" ")[3])}

def title_change_handler(client, author_id, new_title, thread_id, thread_type):
    pass

def image_change_handler(client, author_id, new_image, thread_id, thread_type):
    pass

def nickname_handler(client, author_id, changed_for, new_nickname, thread_id, thread_type):
    pass

def person_added_handler(client, added_ids, author_id, thread_id):
    pass

def person_removed_handler(client, removed_id, author_id, thread_id):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    if removed_id == client.uid and gc_thread.type == ThreadType.GROUP:
        try:
            groups_ref.child(thread_id).delete()
        except FirebaseError:
            print("Not deleted properly")

        #removes groups referece in the database to prevent wasted space

def fr_handler(client, from_id, msg):
    pass

def reaction_added_handler(client, mid, reaction, author_id, thread_id, thread_type):
    global emotionmap
    global reaction_history
    
    if author_id != client.uid:
        # add to reaction reaction history
        reaction_history[(author_id, mid)] = reaction
        # update emotion map
        pol = SentimentIntensityAnalyzer().polarity_scores(client.fetchMessageInfo(mid, thread_id=thread_id).text)
        react_sentiment = emotionmap[reaction][0]
        react_sentiment = [emotionmap[reaction][1] * i for i in react_sentiment]
        react_sentiment = [i + j for i, j in zip(react_sentiment, list(pol.values())[:-1][::-1])]
        emotionmap[reaction][1] += 1
        react_sentiment = [float(i / emotionmap[reaction][1]) for i in react_sentiment]
        emotionmap[reaction][0] = react_sentiment
        log.info(f"Added sentiment {pol} for message {mid} to {reaction}.")
        log.info(emotionmap)

def reaction_removed_handler(client, mid, author_id, thread_id, thread_type, ts, msg):
    global emotionmap
    global reaction_history
    
    if author_id != client.uid:
        # update emotion map
        message = client.fetchMessageInfo(mid, thread_id=thread_id)
        pol = SentimentIntensityAnalyzer().polarity_scores(message.text)
        try:
            reaction = reaction_history[(author_id, mid)]
        except KeyError: # emotion history cleared before reaction removed
            return
        react_sentiment = emotionmap[reaction][0]
        react_sentiment = [emotionmap[reaction][1] * i for i in react_sentiment]
        react_sentiment = [i - j for i, j in zip(react_sentiment, list(pol.values())[:-1][::-1])]
        emotionmap[reaction][1] -= 1
        react_sentiment = [float(i / emotionmap[reaction][1]) for i in react_sentiment]
        emotionmap[reaction][0] = react_sentiment
        log.info(f"Removed sentiment {pol} for message {mid} to {reaction}.")
        log.info(emotionmap)

def timestamp_handler(client, buddylist, msg):
    pass
