#!/usr/bin/env python3
"""
Copyright (c) 2023 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

__author__ = "Trevor Maco <tmaco@cisco.com>, Josh Ingeniero <jingenie@cisco.com>"
__copyright__ = "Copyright (c) 2023 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"

import json
import logging
import os
import re

import urllib3
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request
from rich.console import Console
from rich.panel import Panel
from webexteamssdk import WebexTeamsAPI
from dotenv import load_dotenv

import config
import generate_result
import test_creation

# Load env variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Global Variables
app = Flask(__name__)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Declare logger (writes all errors and basic calls to app.log)
logging.basicConfig(filename='app.log', filemode='a', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Webex API
api = WebexTeamsAPI(access_token=BOT_TOKEN)

# Background scheduler (for running ThousandEyes tests as background processes)
sender_store = BackgroundScheduler()
sender_store.start()

# Rich Console Instance
console = Console()


def create_webhooks(webhook_name, webhook_url, resource, event):
    """
    Create webhooks for chatbot, listen for standard messages and card actions
    """
    # Check if a webhook with the same name and target URL already exists
    existing_webhooks = api.webhooks.list()
    for webhook in existing_webhooks:
        if webhook.targetUrl == webhook_url:
            console.print(f"Webhook {webhook_url} already exists... skipping")
            return

    api.webhooks.create(webhook_name, webhook_url, resource=resource, event=event)
    console.print(f'[green]Successfully created webhook at {webhook_url}[/]')


@app.route('/', methods=['GET', 'POST'])
def webhook():
    """
    A general message (non-card message), return help card or redirect user to help card
    """
    payload = request.json
    if not payload['data']['personEmail'] == config.BOT_EMAIL:
        # Message received in bot space which isn't from the bot
        info = api.messages.get(payload['data']['id']).to_dict()
        console.print(f'Message: {info}')

        if re.search('network-help', info['text'], re.IGNORECASE):
            # Network-help command, display test card for user to launch ThousandEyes test
            api.messages.create(roomId=info['roomId'],
                                text='Let me help!',
                                attachments=[json.loads(config.CARD_PAYLOAD)])  # where to load the card
        else:
            # All other input, redirect user to network-help command
            api.messages.create(roomId=info['roomId'], text='Hello! Please enter the "network-help" '
                                                                             'command to begin the troubleshooting '
                                                                             'workflow.')

    return jsonify({'info': 'Hello from the ThousandEyes Chatbot!'})


@app.route('/card', methods=['GET', 'POST'])
def card_webhook():
    """
    Respond to card attachment actions (clicking submit), run an endpoint instant test, enterprise instant test,
    or both with the specified application
    """

    payload = request.json
    console.print(f'Card Payload: {payload}')

    # Extract card attachment actions
    info = api.attachment_actions.get(payload['data']['id']).to_dict()['inputs']
    if info['action'] == 'newTest':

        # Submit action detected, sanity check an application has been selected (or there's a custom url)
        if info['IssueSelectVal'] != '' or info['CustomURLVal'] != '':
            # Sanity check at least one value provided
            if info['hostnameVal'] == '' and info['sitenameVal'] == '':
                api.messages.create(roomId=payload['data']['roomId'],
                                    text='Please enter at least one of the following: Enterprise Agent Name, Endpoint '
                                         'Agent Hostname')
                return jsonify({'info': 'Not quite... try another request!'})

            # Delete card, user feedback of test received
            api.messages.delete(messageId=payload['data']['messageId'])
            api.messages.create(roomId=payload['data']['roomId'],
                                text='Your test request has been received. Test results will be '
                                     'returned in ~5 minutes')

            # Endpoint Agent Case
            if info['hostnameVal'] != '':
                cardinfo = {'hostnameVal': info['hostnameVal'], 'IssueSelectVal': info['IssueSelectVal'],
                            'CustomURLVal': info['CustomURLVal']}
                console.print(f'[blue]Endpoint[/] Agent Test: {cardinfo}')

                # Find Endpoint Agent Unique ID (required for instant test)
                agent_id = test_creation.find_endpoint_agent_id(cardinfo['hostnameVal'])

                if agent_id:
                    # Perform endpoint instant test (select from pre-selected apps, or custom url)
                    test_result = test_creation.test_selector(agent_id, cardinfo, test_type='endpoint')

                    print("================================================")
                    console.print(f'ThousandEyes Results: {test_result}')
                    print("================================================")

                    # Schedule job to return result cards after a specific time, this provides time for test results
                    # to return (critical) and supports parallel processing
                    for result in test_result:
                        try:
                            generate_result.schedule_result(json.loads(result), payload['data']['roomId'],
                                                            sender_store,
                                                            api, cardinfo['hostnameVal'])
                        except Exception as e:
                            print(f'There was an exception: {str(e)}')
                else:
                    api.messages.create(roomId=payload['data']['roomId'],
                                        text='Endpoint Agent Name not found, please double check the provided name.')

            # Enterprise Agent Case
            if info['sitenameVal'] != '':
                cardinfo = {'sitenameVal': info['sitenameVal'], 'IssueSelectVal': info['IssueSelectVal'],
                            'CustomURLVal': info['CustomURLVal']}
                console.print(f'[blue]Enterprise[/] Agent Test: {cardinfo}')

                agent_id = test_creation.find_enterprise_agent_id(cardinfo['sitenameVal'])

                if agent_id:
                    # Perform endpoint instant test (select from pre-selected apps, or custom url)
                    test_result = test_creation.test_selector(agent_id, cardinfo, test_type='enterprise')

                    print("================================================")
                    console.print(f'ThousandEyes Results: {test_result}')
                    print("================================================")

                    # Schedule job to return result cards after a specific time, this provides time for test results
                    # to return (critical) and supports parallel processing
                    for result in test_result:
                        try:
                            generate_result.schedule_result(json.loads(result), payload['data']['roomId'],
                                                            sender_store,
                                                            api, cardinfo['sitenameVal'])
                        except Exception as e:
                            print(f'There was an exception: {str(e)}')
                else:
                    api.messages.create(roomId=payload['data']['roomId'],
                                        text='Enterprise Agent Name not found, please double check the provided name.')

        else:
            api.messages.create(roomId=payload['data']['roomId'],
                                text='Please select an application to test (or provide your own URL)')

    return jsonify({'info': 'Hello from the ThousandEyes Chatbot!'})


if __name__ == '__main__':
    # Create Webex Bot Webhooks
    console.print(Panel.fit(f"Creating Webhooks", title="Step 1"))
    create_webhooks('ThousandEyes Chatbot All', config.WEBHOOK_BASE_URL, 'messages', 'all')
    create_webhooks('ThousandEyes Chatbot Card', config.WEBHOOK_BASE_URL + '/card', 'attachmentActions', 'created')

    console.print(Panel.fit(f"Listening for Requests", title="Step 2"))

    app.run(port=4000)
