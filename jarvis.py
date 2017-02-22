
# -*- coding: utf-8 -*-

# jarvis.py, 
# blatendr, Brad Latendresse

import websocket
import pickle
import json
import urllib
import requests
import sqlite3
import sklearn # you can import other stuff too!
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.externals import joblib
# FILL IN ANY OTHER SKLEARN IMPORTS ONLY

import botsettings # local .py, do not share!! can get your own at slack.com
TOKEN = botsettings.API_TOKEN
DEBUG = True

def debug_print(*args):
    if DEBUG:
        print(*args)


try:    
    conn = sqlite3.connect("jarvis.db")
    c = conn.cursor()
    #create the DB the first time running
   #c.execute("CREATE TABLE training_data (id INTEGER PRIMARY KEY ASC, txt text, action text)")
    
except:
    debug_print("Can't connect to sqlite3 database...")


def post_message(message_text, channel_id):
    requests.post("https://slack.com/api/chat.postMessage?token={}&channel={}&text={}&as_user=true".format(TOKEN,channel_id,message_text))



class Jarvis():
    #class variables    
    training_mode = False #enter training mode?
    training_item = None
    training_text = None
    testing_mode = False #enter testing mode?
    
    
    def __init__(self): # initialize Jarvis
             
        #set up NB classifier to be used later
        self.BRAIN = Pipeline([('vectorizer',  CountVectorizer()),('classifier',  MultinomialNB()) ])
        
         
    
    def on_message(self, ws, message):
        m = json.loads(message)
        
        #Prints all info from a message, we will only need text and channel id        
        #debug_print(m, self.JARVIS_MODE, self.ACTION_NAME)
        
        # only react to Slack "messages" not from bots (me):
        if m['type'] == 'message' and 'bot_id' not in m:
            
            #if user types done, exit respective mode            
            if (m['text'] == "DONE" and Jarvis.training_mode == True):
                post_message("Exiting training mode...", m['channel'])                     
                Jarvis.training_mode=False
                Jarvis.training_item = None
            if (m['text'] == "DONE" and Jarvis.testing_mode == True):
                post_message("Exiting testing mode...", m['channel'])                     
                Jarvis.testing_mode=False    
            
            
            #training mode
            if (Jarvis.training_mode == True):
                #if action name hasnt been set yet, set it                
                if (Jarvis.training_item == None):                
                    Jarvis.training_item = m['text']
                    post_message(("Ok, let us call this action ", m['text'], "what text do you want with it?"), m['channel'])                    
                else:
                    #action name already set, just need text to go with it and insert into DB                    
                    post_message("Ok, I've got it, add another or type DONE", m['channel'])        
                    Jarvis.training_text = m['text']
                    c.execute("INSERT INTO training_data (txt,action) VALUES (?, ?)", (Jarvis.training_item, Jarvis.training_text,))
                    conn.commit()
            #training mode switch            
            if (m['text'] == "training mode"):
                Jarvis.training_mode = True                    
                post_message("You have entered training mode, what is the name of this ACTION?", m['channel'])                    
            
            
            #testing mode
            if (Jarvis.testing_mode ==True):
                
                #get text and put into list for predict method       
                example = [m['text']]
                
                
                #get action data 
                actdat= []    
                for row in c.execute("SELECT txt from training_data"):
                    actdat.append(str(row))
                
                #get text data
                txtdat = []
                for row in c.execute("SELECT action from training_data"):
                    txtdat.append(str(row))
                 
                #use set up NB model 
                self.BRAIN.fit(txtdat, actdat)
                #pickle it                
                joblib.dump(self.BRAIN.fit(txtdat, actdat),"jarvis_brain.pk1")             
                
                
                #get prediction and clean it up a little
                predict =str(self.BRAIN.predict(example))
                predict_clean = predict[4:-4]
                
                          
                post_message(("I think that is",predict_clean),m['channel'])
                post_message("either keep testing or type DONE",m['channel'])                
                
            #testing mode switch
            if (m['text'] == 'testing mode'):
                post_message("You have entered testing mode, let me guess what Action you mean", m['channel'])            
                Jarvis.testing_mode= True
            
            


def start_rtm():
    """Connect to Slack and initiate websocket handshake"""
    r = requests.get("https://slack.com/api/rtm.start?token={}".format(TOKEN), verify=False)
    r = r.json()
    r = r["url"]
    return r


def on_error(ws, error):
    print("SOME ERROR HAS HAPPENED", error)


def on_close(ws):
    conn.close()
    print("Web and Database connections closed")


def on_open(ws):
    print("Connection Started - Ready to have fun on Slack!")



r = start_rtm()
jarvis = Jarvis()
ws = websocket.WebSocketApp(r, on_message=jarvis.on_message, on_error=on_error, on_close=on_close)
ws.run_forever()
