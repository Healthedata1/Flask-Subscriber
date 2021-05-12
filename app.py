# A very simple Flask app to find R4 subscription topic and then subscribe to topic
# FHIR Subscriptions
# This is the test server for the FHIR R4 Server URL (https://server.subscriptions.argo.run/r4)
# with an ednpoint = ""
# It just perform the get subscription topic to the subscription $topic-list endpoint:
#
# https://server.subscriptions.argo.run/r4/Subscription/$topic-list
#  to get the available topics
# and subscribes for id=only notifications for all topics for these patients:
# - "Patient/06e1f0dd-5fbe-4480-9bb4-6b54ec02d31b"
from flask import Flask, request, Response, render_template, session
import os
import logging
from datetime import datetime, timedelta
from json import dumps, loads
from requests import get, post
from fhir.resources.parameters import Parameters as P
from fhir.resources.subscription import Subscription as S
import my_templates as t

logging.basicConfig(
#filename='demo.log',
level=logging.DEBUG,
format='[%(asctime)s] %(levelname)s in %(module)s %(lineno)d}: %(message)s')

app = Flask(__name__)
app.config["DEBUG"] = True
app.secret_key = 'my_secret_key'

my_base = 'https://server.subscriptions.argo.run/r4'
my_pub =  my_base
my_sub_endpt = "http://flask-pubsub-endpoint.healthedata1.co/webhook"
#my_sub_endpt = 'localhost:5000/webhook'
my_patients = [
"06e1f0dd-5fbe-4480-9bb4-6b54ec02d31b",
"b1cf5f57-b061-4b7f-aa9d-6283a121694b",
"aad0894e-47f4-4ffc-8fab-8fe5487110d2",
]

params = {
}

headers = {
    'Accept':'application/fhir+json',
    'Content-Type':'application/fhir+json'
    }

# *********************** Fetch Resource ********************
def fetch(my_base,my_type,my_id,ver=None):
    '''
    fetch resource by READ or VREAD method e.g. [base]/[Type]/[id]/{[_history]}/{[version]}
    return resource as fhirclient model
    '''
    r_url = (f'{my_base}/{my_type}/{my_id}/_history/{ver}'
            if ver else f'{my_base}/{my_type}/{my_id}')
    app.logger.info(f'****** r_url = {r_url}***')
    with get(r_url, headers=headers) as r:
        try:
            return r.json()
        except Exception as e:
            app.logger.exception(e)
            return


# ***********************Subscribe ********************
def my_sub(my_pub,topic):
    my_sub = t.base_sub
    now = datetime.now()
    future = now + timedelta(30) # update time = default to 30 days
    my_sub['end']=future.isoformat()
    my_sub['channel']['endpoint']= my_sub_endpt # .channel.endpoint = hardcode for now
    # .criteria = Encounter?patient=Patient/ID patient hard code but make a picker
    my_sub['criteria']=f'Encounter?patient=Patient/{my_patients[0]}'
    # .extension[0].valueUri = topic from list ...todo

    app.logger.info(f'URL = {my_pub}/Subscription\n headers = {headers}\n my_sub = {my_sub}')
    with post(f'{my_pub}/Subscription', headers=headers, data=dumps(my_sub)) as r:
        try:
            app.logger.info(f'r.status = {r.status_code}\n response body = {r.json()}')
            return r.json()
        except Exception as e:
            app.logger.info(f'r.status = {r.status_code}')
            app.logger.exception(e)
            return
        return

@app.route('/Subscription/$topic-list',)
def topic_list():
    topic_list = fetch(my_base=my_base,my_type='Subscription',my_id='$topic-list')

    fr_topic_list = P.parse_obj(topic_list)
    app.logger.info(f"fr_topic_list.yaml(indent=True)={fr_topic_list.yaml(indent=True)}")
    session['my_topics'] = [i.valueCanonical for i in fr_topic_list.parameter
        if i.name == 'subscription-topic-canonical']  # todo save from set as csv file for sharing with other apps
    return render_template('$topic-list.html',
        topic_list=fr_topic_list.yaml(indent=True),my_topics=session['my_topics'], my_pub=my_pub)

@app.route('/Subscribe')
def subscribe():

    my_subs = [my_sub(my_pub,topic) for topic in session['my_topics']]

    my_subs = [S.parse_obj(my_sub) for my_sub in my_subs]

    return render_template('subscribed.html',my_subs=my_subs, my_pub=my_pub)


@app.route('/',methods = ['POST', 'GET'])
def home():
    return render_template('index.html',)

if __name__ == '__main__':
    app.run(debug=True)
