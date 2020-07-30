import time
import random
from datetime import datetime, date, timedelta
from dateparser import parse
import wikipedia
from fbchat import log, Client, Message, Mention, Poll, PollOption, ThreadType, ShareAttachment, MessageReaction, FBchatException
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import json
import requests
import urllib
import os
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process, fuzz
import firebase_admin	
from firebase_admin import credentials	
from firebase_admin import db	
import os 
import numpy as np
import copy
import re
from hashlib import shake_256


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
#this if statement is crucial to make sure that the file is able to be reloaded with out initilizing multiple apps
if not firebase_admin._apps:
    # Initialize the app with a custom auth variable, limiting the server's access
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ.get("DATABASEURL"),
        'databaseAuthVariableOverride': {
            'uid': os.environ.get("WORKERID")
        }
    })

# The app only has access as defined in the Security Rules
groups_ref = db.reference('/groups')

# Fetch the service account key JSON file contents
cred = credentials.Certificate(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

#this if statement is crucial to make sure that the file is able to be reloaded with out initilizing multiple apps
if not firebase_admin._apps:
    # Initialize the app with a custom auth variable, limiting the server's access
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ.get("DATABASEURL"),
        'databaseAuthVariableOverride': {
            'uid': os.environ.get("WORKERID")
        }
    })

# The app only has access as defined in the Security Rules
groups_ref = db.reference('/groups')

def tag_all(client, author_id, message_object, thread_id, thread_type):
    """Tags everyone in tshe chat"""
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    mention_list = []
    message_text = '@all'
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        mention_list.append(Mention(thread_id=person.uid, offset=0, length=1))
    client.send(Message(text=message_text, mentions=mention_list), thread_id=thread_id, thread_type=thread_type)

def random_mention(client, author_id, message_object, thread_id, thread_type):
    """Tags a random person"""
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_list = []
    for person in Client.fetchAllUsersFromThreads(self= client, threads = [gc_thread]):
        person_list.append(person)
    chosen_number = random.randrange(0,len(person_list),1)
    chosen_person = person_list[chosen_number]
    person_name = chosen_person.first_name
    rand_mention = Mention(thread_id = chosen_person.uid, offset=0, length= len(person_name)+1)
    client.send(Message(text = "@" + person_name + " you have been chosen", mentions=[rand_mention]), thread_id=thread_id, thread_type=thread_type)

def admin(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_admin = message_object.text.split(' ', 1)[1]
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        if person_to_admin.lower() in person.name.lower():
            log.info("{} added as admin {} from {}".format(author_id, person_to_admin, thread_id))
            client.addGroupAdmins(person.uid, thread_id=thread_id)
            return
    log.info("Unable to add admin: person not found.")
def random_image(client, author_id, message_object,thread_id,thread_type):
    """Sends a random image to chat"""
    client.sendRemoteImage("https://scontent-sjc3-1.xx.fbcdn.net/v/t1.0-9/31706596_988075581341800_8419953087938035712_o.jpg?_nc_cat=101&_nc_sid=e007fa&_nc_ohc=6WKPJKXT4yQAX8izxEX&_nc_ht=scontent-sjc3-1.xx&oh=dd30e0dc74cffd606248ef9151576fe2&oe=5F2E0EBC",message=Message(text='This should work'), thread_id=thread_id, thread_type=thread_type)
    
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
        client.send(Message(text='I can\'t read that date.'), thread_id=thread_id, thread_type=thread_type)
        return
    except ValueError:
        client.send(Message(text='I\'m not stupid that date has passed.'), thread_id=thread_id, thread_type=thread_type)
        return
    meeting = Poll(title=f"Meeting on {datetime.strftime(msg_date, '%A, %x')}. Who's in?", options=[PollOption(text=time) for time in time_options])
    client.createPoll(poll=meeting, thread_id=thread_id)
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
    client.send(Message(text= returnText),thread_id=thread_id, thread_type=thread_type)
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
        client.send(Message(text=f'Consensus reached! Meeting at {meeting_time} on {meeting_date}'), thread_id=thread_id, thread_type=thread_type)
        return
    elif consensus[-1]: # meeting is not happening
        client.send(Message(text=f'Consensus reached! Meeting at {meeting_time} isn\'t happening.'), thread_id=thread_id, thread_type=thread_type)
        return
    else:
        log.info(f"No consensus on poll {poll.uid} yet.")

def wiki(client, author_id, message_object, thread_id, thread_type):
    """Checks wikipedia for term"""
    try:
        search_term = message_object.text.split(' ', 1)[1]
        search_result = Message(text=wikipedia.summary(search_term, sentences=2))
    except wikipedia.exceptions.WikipediaException:
        client.send(Message(text='Invalid search term.'), thread_id=thread_id, thread_type=thread_type)
        return
    except IndexError:
        client.send(Message(text='You didn\'t give me anything to search dipshit.'), thread_id=thread_id, thread_type=thread_type)
        return
    client.send(search_result, thread_id=thread_id, thread_type=thread_type)

def laugh(client, author_id, message_object, thread_id, thread_type):
    """Laughs"""
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    client.sendLocalVoiceClips(clip_paths="resources/laugh.aac", thread_id=thread_id, thread_type=thread_type)

def kick(client, author_id, message_object, thread_id, thread_type):
    """Kicks the specified user from the chat"""
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_kick = message_object.text.split(' ', 1)[1]
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        if person_to_kick.lower() in person.name.lower():
            log.info("{} removed {} from {}".format(author_id, person_to_kick, thread_id))
            client.removeUserFromGroup(person.uid, thread_id=thread_id)
            return
    log.info("Unable to remove: person not found.")

def ap_comment(client, author_id, message_object, thread_id, thread_type):
    """Apurv's special comment"""
    client.send(Message(text="yOu CaN't AuToMaTe HeAlThCaRe"), thread_id=thread_id, thread_type=thread_type)
    
def sully_comment(client, author_id, message_object, thread_id, thread_type):
    """Sulaiman's special comment"""
    client.send(Message(text="i Am NoT ___ gUyS I swEAr"), thread_id=thread_id, thread_type=thread_type)
    
def pranshu_comment(client, author_id, message_object, thread_id, thread_type):
    """Pranshu's special comment"""
    client.send(Message(text="Pranshu is a student at the University of Illinois Urbana-Champaign studying Computer Science and Statistics. My interests lie in High Performance Computing (HPC) and in AI/Deep Learning. Recently I attended the Super Computing 19 conference where I represented my school as a member of the University of Illinois Student Cluster Competition team; our team won 2nd place nationwide. I've recently also won 2nd place at the National Center for Supercomputing Applications Deep Learning Hackathon. At the Technology Student Association’s national conference in June, 2019, my team won 1st place out of over 75 teams in a research presentation competition on exploring a novel application of artificial intelligence in a domain field (website: pinkai.tech). I am an enthusiastic candidate for any role relating to HPC or Deep Learning; I hope to expand my skill set in the summer of 2020 through an internship at a company focusing on these disciplines. "), thread_id=thread_id, thread_type=thread_type)

def aru_comment(client, author_id, message_object, thread_id, thread_type):
    """Arunav's special comment"""
    client.send(Message(text="Commit pushed to origin master"), thread_id=thread_id, thread_type=thread_type)

def kanav_comment(client, author_id, message_object, thread_id, thread_type):
    """Kanav's special comment"""
    client.send(Message(text="yEa i gO tO cOlOmBiA kOlLeGe iN tHe ViLlAgE oF oLd dOrK"), thread_id=thread_id, thread_type=thread_type)

def rishi_comment(client, author_id, message_object, thread_id, thread_type):
    """Rishi's special comment"""
    client.send(Message(text="yEa I gO tO gTeCh fOr ThE sKaTeBoArDiNg WeAtHer"), thread_id=thread_id, thread_type=thread_type)

def removeme(client, author_id, message_object, thread_id, thread_type):
    """Removes the person who calls this from the chat"""
    print("{} will be removed from {}".format(author_id, thread_id))
    client.removeUserFromGroup(author_id, thread_id=thread_id)
                   
def kick_random(client, author_id, message_object, thread_id, thread_type):
    """Kicks a random person from the chat"""
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    persons_list = Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread])
    num = random.randint(0, len(persons_list)-1) #random number within range
    person = persons_list[num]
    log.info("{} removed {} from {}".format(author_id, "random", thread_id))
    client.removeUserFromGroup(person.uid, thread_id=thread_id)
    return
    log.info("Unable to remove: person not found.")
                   
#the message goes to spam my default if you aren't friends with the bot
def pm_person(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_pm = message_object.text.split(' ')[1:]
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        names = [person.first_name, person.last_name, person.nickname]
        if any([name in person_to_pm for name in names]):
            thread_id = person.uid
    client.send(Message(text="hello friend"), thread_id=thread_id, thread_type=ThreadType.USER)

def return_self(client, author_id, message_object, thread_id, thread_type):
    """Echoes what you tell the bot to say"""
    client.send(Message(text=message_object.text.split(' ',1)[1]), thread_id=thread_id, thread_type=thread_type)

def list_functions(client, author_id, message_object, thread_id, thread_type):
    """Lists all available functions"""
    message_string = "List of available functions:\n"
    for key in list(command_lib.keys()):
        if key != "help":
            message_string += str(key) + " - " + command_lib[key]['description'] + "\n"
    client.send(Message(text=message_string), thread_id=thread_id, thread_type=thread_type)

def sentiment_react(client, author_id, message_object, thread_id, thread_type):
    global emotionmap
    pol = SentimentIntensityAnalyzer().polarity_scores(message_object.text)
    compound = pol['compound']
    pol = list(pol.values())[:-1][::-1]
    similarity = {np.dot(pol, emotionmap[i][0])/(np.linalg.norm(pol)*np.linalg.norm(emotionmap[i][0])) : i for i in emotionmap.keys()}
    # if emotion vector is +/- ~30 degrees from an emotion, send that reaction
    if sorted(list(similarity.keys()), reverse=True)[0] > 0.866 and np.absolute(compound) > 0.4:
        client.reactToMessage(message_object.uid, similarity[sorted(list(similarity.keys()), reverse=True)[0]])

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
    client.send(Message(text=f'Emotion memory reset at {datetime.now()}'), thread_id=thread_id, thread_type=thread_type)
    log.info(f'Emotion vectors: {emotionmap}')
    log.info(f'Reaction history: {reaction_history}')

def world_peace(client, author_id, message_object, thread_id, thread_type):
    """Creates world peace"""
    kick_random(client, author_id, message_object, thread_id, thread_type)
    client.sendLocalImage("resources/worldpeace.gif", thread_id=thread_id, thread_type=thread_type)

def pin(client, author_id, message_object, thread_id, thread_type):
    #making sure something isnt pinned in a User thread to save space
    if Client.fetchThreadInfo(client, thread_id)[thread_id].type == ThreadType.USER:
        client.send(Message(text="Pin only works in Group chats!"), thread_id=thread_id, thread_type=thread_type)
        return
    
    #using these variables to check if the value exists either to prevent overwrites or to make only one variable is occupied at a time
    string_get = groups_ref.child(thread_id).child("string").get()
    pin_get = groups_ref.child(thread_id).child("pin_id").get()
    if message_object.replied_to == None:
        #this is if they want to pin a string 
        to_pin = message_object.text.split(' ')[1:]
        
        if not to_pin:
            client.send(Message(text="Make sure you have something to pin!"), thread_id=thread_id, thread_type=thread_type)
            return
        
        if string_get is None:
            groups_ref.child(thread_id).set({"string": to_pin})
        else:
            groups_ref.child(thread_id).update({"string": to_pin})
        
        #making sure pin_id doesnt exist or equals nulls to make sure only variable is occuplied at a time
        if pin_get != None:
            groups_ref.child(thread_id).child("pin_id").delete()
    else:
        #this if they want to pin either an attachment or want to pin by replying to it
        if pin_get is None:
            groups_ref.child(thread_id).set({"pin_id": message_object.replied_to.uid})
        else:
            groups_ref.child(thread_id).update({"pin_id": message_object.replied_to.uid})

        if string_get != None:
                groups_ref.child(thread_id).child("string").delete()


def brief(client, author_id, message_object, thread_id, thread_type):
    if Client.fetchThreadInfo(client, thread_id)[thread_id].type == ThreadType.USER:
        client.send(Message(text="Brief only works in Group Chats"), thread_id=thread_id, thread_type=thread_type)
        return
    
    string_get = groups_ref.child(thread_id).child("string").get()
    pin_get = groups_ref.child(thread_id).child("pin_id").get()
    
    if string_get is None and pin_get is None:
        client.send(Message(text="You never pinned anything"), thread_id=thread_id, thread_type=thread_type)
    elif pin_get is None: 
        #return string pinned
        client.send(Message(text=string_get), thread_id=thread_id, thread_type=thread_type)
    else:
        #return the attachment pinned, also includes a provision incase someone decides to pin a string by replying to it
        #in reality i pulled pinned messages either by the string itself which isnt the best, or by the message id which is better but this is
        #something i will change later, the important thing is to wrap the fetchMessageInfo to catch FBchatException in case the message doesnt exist 
        try :
            message_object = Client.fetchMessageInfo(client, mid=pin_get, thread_id=thread_id)
            print(message_object.attachments)
            if not message_object.attachments:
                client.send(Message(text=message_object.text), thread_id=thread_id, thread_type=thread_type)
            else:
                for x in message_object.attachments:
                    client.forwardAttachment(x.uid,thread_id)
        except FBchatException:
            client.send(Message(text="Your Pinned Message might not exist anymore"), thread_id=thread_id, thread_type=thread_type)

def urban_dict(client, author_id, message_object, thread_id, thread_type):
    """Returns query output from Urban Dictionary"""
    word = message_object.text.split(' ',1)[1]
    r = requests.get("http://www.urbandictionary.com/define.php?term={}".format(word))
    soup = BeautifulSoup(r.content)
    client.send(Message(text=soup.find("div",attrs={"class":"meaning"}).text), thread_id=thread_id, thread_type=thread_type)

def check_status(client, author_id, message_object, thread_id, thread_type):
    client.send(Message(text="bot is live at {}".format(datetime.now())), thread_id=thread_id, thread_type=thread_type)

# returns the most probable command if the command was not immediately in the command_lib
def didyoumean(input_command):
    return process.extract(input_command ,command_lib.keys(), scorer = fuzz.partial_ratio, limit = 1)[0][0]
    
def recite(client, author_id, message_object, thread_id, thread_type):
    client.send(Message(text="1. A robot may not injure a human being or, through inaction, allow a human being to come to harm.\n" 
                        + "2. A robot must obey the orders given it by human beings except where such orders would conflict with the First Law.\n" 
                        + "3. A robot must protect its own existence as long as such protection does not conflict with the First or Second Laws"), thread_id=thread_id, thread_type=thread_type)

def make_friend(client, author_id, message_object, thread_id, thread_type):
    gc_thread = Client.fetchThreadInfo(client, thread_id)[thread_id]
    person_to_friend = message_object.text.split(' ', 1)[1]
    for person in Client.fetchAllUsersFromThreads(self=client, threads=[gc_thread]):
        if person_to_friend.lower() in person.name.lower():
            Client.friendConnect(client, person.uid)

def send_anon(client, author_id, message_object, thread_id, thread_type):
    """
    Sends message to selected person.
    Format: !send [target] message
    """
    global anon_dict
    global anon_target_dict
    
    if thread_type != ThreadType.USER:
        client.send(Message(text="Sorry, this feature only works in my PM."), thread_id=thread_id, thread_type=thread_type)
        return
    try:
        target = re.match(r"[^[]*\[([^]]*)\]", message_object.text).groups()[0]
        message = message_object.text.replace(f"[{target}]", "").split(" ", 1)[1][1:]
    except:
        client.send(Message(text="Didn't give a message! Usage: !send [recipient name] message"), thread_id=thread_id, thread_type=thread_type)
        return
    # find recipient
    target = client.searchForUsers(target, limit=1)[0]
    if not target.is_friend:
        client.send(Message(text=f"I can't contact {target.first_name} {target.last_name}; I'm not friends with them."), thread_id=thread_id, thread_type=thread_type)
        return
    # add author to lookup table {sha256(author_id + salt) : author_id}
    anon_id = shake_256(str(int(author_id) + random.randint(-1e4,1e4)).encode('utf-8')).hexdigest(8)
    anon_dict[anon_id] = author_id
    anon_target_dict[anon_id] = target.uid
    # pm recipient
    client.send(Message(text=f'New message from {anon_id}:\n{message}\nTo respond, copy/paste the template below and add in your response.'), thread_id=target.uid, thread_type=ThreadType.USER)
    client.send(Message(text=f'!reply [{anon_id}] <your message here>'), thread_id=target.uid, thread_type=ThreadType.USER)
    time.sleep(0.2)
    client.send(Message(text=f"Message sent from you ({anon_id}) to {target.first_name} {target.last_name}.\nReminder: you can end this chat session at any time by typing !end {target.first_name}"), thread_id=thread_id, thread_type=thread_type)
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
        client.send(Message(text="Sorry, this feature only works in my PM."), thread_id=thread_id, thread_type=thread_type)
        return
    try:
        target = re.match(r"[^[]*\[([^]]*)\]", message_object.text).groups()[0]
        message = message_object.text.replace(f"[{target}]", "").split(" ", 1)[1][1:]
    except:
        client.send(Message(text="Didn't give a message! Usage: !reply [recipient id] message"), thread_id=thread_id, thread_type=thread_type)
        return
        
    # determine whether message is coming from sender or target
    if author_id in anon_target_dict.values(): # message is from a target -> target is a hexcode
        target_user = client.fetchUserInfo(author_id)[author_id]
        if target in anon_dict.keys():
            client.send(Message(text=f"Reply from {target_user.first_name}: {message}\nTo reply to them, type !reply [<their name here>] <your message here>"), thread_id=anon_dict[target], thread_type=ThreadType.USER)
            time.sleep(0.2)
            client.send(Message(text=f'Reply sent to {target}.'), thread_id=thread_id, thread_type=thread_type)
            return
        else: # chat session has been deleted
            client.send(Message(text=f"You don't appear to have an active chat session with {target}. Use !send to start one."), thread_id=thread_id, thread_type=thread_type)
            return
    elif author_id in anon_dict.values(): # message is from a sender -> target is a name
        target_user = client.searchForUsers(target, limit=1)[0]
        # make sure sender and target have a session going
        for k, v in anon_dict.items():
            if v == author_id and anon_target_dict[k] == target_user.uid:
                client.send(Message(text=f"Reply from {k}: {message}\nCopy/paste the template below to send a reply."), thread_id=target_user.uid, thread_type=ThreadType.USER)
                client.send(Message(text=f"!reply [{k}] <reply here>"), thread_id=target_user.uid, thread_type=ThreadType.USER)
                time.sleep(0.2)
                client.send(Message(text=f'Reply sent from you ({anon_id}) to {target_user.first_name}.'), thread_id=thread_id, thread_type=thread_type)
                return
        # if code reaches here there was no active session found
        client.send(Message(text=f"You don't appear to have an active chat session with {target_user.first_name}. Use !send to start one."), thread_id=thread_id, thread_type=thread_type)
        return
    else:
        client.send(Message(text="You don't have any active chat sessions open. Either use !send to deliver an anonymous message or wait for one to come to you."), thread_id=thread_id, thread_type=thread_type)
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
        client.send(Message(text='Please only do this in my PM.'), thread_id=thread_id, thread_type=thread_type)
        return
    
    try:
        target = message_object.text.split(' ', 1)[1]
        target_id = client.searchForUsers(target, limit=1)[0].uid
    except IndexError:
        client.send(Message(text="Who do I end? Usage: !end <person name here>"), thread_id=thread_id, thread_type=thread_type)
        return 
    
    # make sure there's at least one active session between the sender and target
    author_chats = set([key for key, value in anon_dict.items() if value == author_id])
    target_chats = set([key for key, value in anon_target_dict.items() if value == target_id])
    common_chats = list(author_chats & target_chats)
    if len(common_chats) == 1:
        del anon_dict[common_chats[0]]
        del anon_target_dict[common_chats[0]]
        client.send(Message(text=f'Session with {target} ended. All data deleted.'), thread_id=thread_id, thread_type=thread_type)
    elif len(common_chats) > 1:
        client.send(Message(text=f'Multiple active sessions with {target} detected. Deleting all {len(common_chats)} sessions...'), thread_id=thread_id, thread_type=thread_type)
        for hexcode in common_chats:
            del anon_dict[hexcode]
            del anon_target_dict[hexcode]
        client.send(Message(text='All data deleted.'), thread_id=thread_id, thread_type=thread_type)
    else: # no chat sessions between sender and target
        client.send(Message(text=f"You don't appear to have an active chat sessions with {target}. Use !send to start one."), thread_id=thread_id, thread_type=thread_type)
        
    log.info(anon_dict)
    log.info(anon_target_dict)

#brew install poppler if on mac or pip install python-poppler on Ubuntu as in requirements.txt
def scenesfromahat(client, author_id, message_object, thread_id, thread_type):
	os.system("rm -rf scenesfromahat.pdf")
	os.system("rm -rf scenesfromahat.txt")
	os.system("wget https://docs.google.com/document/d/1Y3dCl8wC8Za_av1wN2GyJAquEoonE134ejjGIaJXzag/export?format=pdf -O scenesfromahat.pdf")
	os.system("pdftotext -layout scenesfromahat.pdf scenesfromahat.txt")
	with open("scenesfromahat.txt") as f:
		lines = f.readlines()
		client.send(Message(text=random.choice(lines)), thread_id=thread_id, thread_type=thread_type)

command_lib = {"all" : {"func" : tag_all, "description" : "Tags everyone in the chat"}, 
                "kick" : {"func" : kick, "description" : "Kicks the specified user from the chat"}, 
                "meet" : {"func" : hear_meet, "description" : "Creates poll to decide on time for given date"},
                "laugh" : {"func" : laugh, "description" : "Laughs"},
                "randomp" : {"func": random_mention, "description" : "Tags a random person"},
                "randomi" : {"func": random_image, "description" : "Sends a random image to chat"},
                "sully" : {"func" : sully_comment, "description" : "Sulaiman's special comment"},
                "pranshu" : {"func" : pranshu_comment, "description" : "Pranshu's special comment"},
                "ap" : {"func" : ap_comment, "description" : "Apurv's special comment"},
                "aru" : {"func" : aru_comment, "description" : "Arunav's special comment"},
                "kanav" : {"func" : kanav_comment, "description" : "Kanav's special comment"},
                "rishi" : {"func" : rishi_comment, "description" : "Rishi's special comment"},
                "kickr" : {"func" : kick_random, "description" : "Kicks a random person from the chat"},
                "removeme" : {"func" : removeme, "description" : "Removes the person who calls this from the chat"},
                "wiki" : {"func" : wiki, "description" : "Checks wikipedia for term"},
                "return": {"func": return_self, "description" : "Echoes what you tell the bot to say"},
                "pm" : {"func" : pm_person, "description" : "PMs the given person"}, 
                "help": {"func": list_functions, "description" : "Lists all available functions"},
                "admin": {"func": admin, "description": "Makes someone admin"},
                "yelp": {"func":yelp_search, "description": "Finds stores based on location and keyword"}, 
                "urbandict": {"func" : urban_dict, "description" : "Returns query output from Urban Dictionary"},
                "worldpeace" : {"func" : world_peace, "description" : "Creates world peace"},
                "status" : {"func" : check_status, "description" : "Returns the bot's status"},
                "pin" : {"func" : pin, "description" : "pins a message: call !pin to store the following text or reply to an image/text with !pin"},
                "brief" : {"func" : brief, "description" : "returns your pinned image or text"},
                "recite" : {"func" : recite, "description" : "Recites the three laws"},
                "emotionreset" : {"func" : reset_emotions, "description" : "Resets emotion memory"},
                "friend" : {"func" : make_friend, "description" : "Will accept the person's friend request"},
                "status" : {"func" : check_status, "description" : "Returns the bot's status"},
                "send" : {"func" : send_anon, "description" : "Sends anonymous message to specified person"},
                "reply" : {"func" : reply_anon, "description" : "Replies to anonymous message"},
                "end" : {"func" : end_anon, "description" : "Ends anonymous chat session"}},
                "scenesfromahat" : {"func" : scenesfromahat, "description" : "Returns a random sentence from Scenes from a Hat"}
               }


def command_handler(client, author_id, message_object, thread_id, thread_type):
    if message_object.text.split(' ')[0][0] == '!':
        command = command_lib.get(message_object.text.split(' ')[0][1:])
        if command is not None:
            command["func"](client, author_id, message_object, thread_id, thread_type)
        else:
            client.send(Message(text="That command doesnt exist. Did you mean !" + str(didyoumean(message_object.text.split(' ')[0][1:]))), thread_id=thread_id, thread_type=thread_type)
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
