#!/usr/bin/env python

import json # talk to watson
import watson_developer_cloud # connect to watson
from unicodereplace import asciiFixerFactory

import rospy
from assistant.msg import ChatbotAnswer
from rtspeech.msg import RealtimeTranscript

loglevel = rospy.get_param('/debug/loglevel', rospy.INFO)

rospy.init_node('assistant', anonymous=False, log_level=loglevel)

credfilepath = rospy.get_param(rospy.get_namespace() + 'assistant_cred', '/home/corobi/.cloudkeys/chatbot_cred.json')
minimumconfidence = rospy.get_param(rospy.get_namespace() + 'minimumconfidence', 0.6)
language = rospy.get_param(rospy.get_namespace() + 'language', 'en-US')

asciifix = asciiFixerFactory(language)

class WatsonChatbot:
    def __init__(self, credfile):
        with open(credfile, 'rb') as infile:
            creds = json.load(infile)
        self._assistant = watson_developer_cloud.AssistantV1(
            '2018-02-16',
            url=creds['url'],
            username=creds['username'],
            password=creds['password'])
        self._request = {
            'workspace_id' : creds['workspace'],
            'input' : { 'text' : '' }
            }

    def ask(self, question):
        self._request['input']['text'] = question
        resp = self._assistant.message(**self._request)
        self._request['context'] = resp['context']
        #print(json.dumps(resp, indent=2))
        intents = resp['intents']
        if len(intents):
            return (resp['output']['text'][0], intents[0]['confidence'])
        entities = resp['entities']
        if len(entities):
            return (resp['output']['text'][0], entities[0]['confidence'])
        return (resp['output']['text'][0], 0.0)


cb = WatsonChatbot(credfilepath)

cbanspub = rospy.Publisher(rospy.get_namespace() + 'chatbotanswer', ChatbotAnswer, queue_size=10)

def transcriptcb(rttrans):
    if rttrans.confidence > minimumconfidence:
        ans = cb.ask(rttrans.text)
        cbans = ChatbotAnswer()
        cbans.text = asciifix(ans[0])
        cbans.confidence = ans[1]
        rospy.loginfo(u"{}: {}".format(cbans.confidence, cbans.text))
        cbanspub.publish(cbans)

rospy.Subscriber(rospy.get_namespace() + 'realtimetranscript', RealtimeTranscript, transcriptcb)

while not rospy.is_shutdown():
    try:
        rospy.spin()
    except:
        pass

rospy.loginfo("assistant node shutdown")
