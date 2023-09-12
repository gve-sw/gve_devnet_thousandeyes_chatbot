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

import datetime
import json

import requests
from rich.console import Console

import config

# Rich Console Instance
console = Console()


def call_url(url):
    """
    Returns the data from the ThousandEyes url
    :param url - ThousandEyes apiLink
    :return: ThousandEyes test result data
    """
    payload = {}
    headers = {
        'Accept': 'application/json',
        'Authorization': f"Bearer {config.THOUSAND_EYES_TOKEN}"
    }

    response = requests.get(url, headers=headers, data=payload)
    return response


def generate_result(result, test_target):
    """
    Returns a JSON-formatted card for Webex Cards from ThousandEyes Test results
    :param result - ThousandEyes response for creating tests
    :param test_target: Target of Test (Endpoint Hostname, Enterprise Agent Name)
    :return card - formatted for Webex or None if apiLinks do not exist
    """
    # Endpoint Test Case
    if 'endpointTest' in result.keys():
        web = 'endpointWeb'
        test = 'endpointTest'
        net = 'endpointNet'

        # Error check test returned error
        if test not in result:
            return None

        if 'metrics' not in result[test][0]['apiLinks'][1]['href']:  # both exist = http-server test
            # Extract links from response payload
            http_link = result[test][0]['apiLinks'][1]['href']
            metrics_link = result[test][0]['apiLinks'][2]['href']

            # Get test results for each component from ThousandEyes
            http = call_url(http_link).json()
            metrics = call_url(metrics_link).json()

            # Extract relevant values from results
            code = http[web]['httpServer'][0]['responseCode']
            if code == 200:
                status = 'Everything seems normal at office, try rebooting your PC.'
                total = http[web]['httpServer'][0]['totalTime']
                cpu = http[web]['httpServer'][0]['systemMetrics']['cpuUtilization']['mean'] * 100
                cpu = round(cpu, 2)
                date = http[web][test]['createdDate']
            else:
                status = "Unfortunately it looks like your endpoint is having network issues with this application. " \
                         "Please call the help desk. "
                total = 'N/A'
                cpu = http[web]['httpServer'][0]['systemMetrics']['cpuUtilization']['mean'] * 100
                cpu = round(cpu, 2)
                date = 'N/A'
            url = http[web][test]['server']
        else:  # only metrics = agent-server
            # Extract links from response payload
            metrics_link = result[test][0]['apiLinks'][1]['href']

            # Get test results for each component from ThousandEyes
            metrics = call_url(metrics_link).json()

            # Extract relevant values from results
            date = metrics[net][test]['createdDate']
            cpu = metrics[net]['metrics'][0]['systemMetrics']['cpuUtilization']['mean'] * 100
            cpu = round(cpu, 2)
            url = metrics[net][test]['server']
            status = 'Agent-to-server Test'
            code = 'N/A'
            total = 'N/A'

    # Enterprise Test Case
    else:
        web = 'web'
        test = 'test'
        net = 'net'

        # Error check test returned error
        if test not in result:
            return None

        if 'metrics' not in result[test][0]['apiLinks'][1]['href']:  # both exist = http-server test
            # Extract links from response payload
            http_link = result[test][0]['apiLinks'][1]['href']
            metrics_link = result[test][0]['apiLinks'][2]['href']

            # Get test results for each component from ThousandEyes
            http = call_url(http_link).json()
            metrics = call_url(metrics_link).json()

            # Extract relevant values from results
            code = http[web]['httpServer'][0]['responseCode']
            if code == 200:
                status = 'Everything seems normal at office, try rebooting your PC.'
                total = http[web]['httpServer'][0]['totalTime']
                cpu = 'N/A'
                date = http[web][test]['createdDate']
            else:
                status = "Unfortunately it looks like your site is having network issues with this application. " \
                         "Please call the help desk. "
                total = 'N/A'
                cpu = 'N/A'
                date = http[web][test]['createdDate']
            url = http[web][test]['url']

        else:  # only metrics = agent-server
            # Extract links from response payload
            metrics_link = result[test][0]['apiLinks'][1]['href']

            # Get test results for each component from ThousandEyes
            metrics = call_url(metrics_link).json()

            # Extract relevant values from results
            date = metrics[net][test]['createdDate']
            cpu = 'N/A'
            url = metrics[net][test]['server']
            status = 'Agent-to-server Test'
            code = 'N/A'
            total = 'N/A'

    # Extract loss, latency, jitter from metrics results
    if 'loss' in metrics[net]['metrics'][0].keys():
        loss = metrics[net]['metrics'][0]['loss']
        if 'jitter' in metrics[net]['metrics'][0].keys():
            latency = metrics[net]['metrics'][0]['avgLatency']
            jitter = metrics[net]['metrics'][0]['jitter']
        else:
            latency = 'N/A'
            jitter = 'N/A'
    else:
        loss = 'N/A'
        latency = 'N/A'
        jitter = 'N/A'

    # Build contents of Webex Card
    result_card = json.loads(config.RESULT_CARD)

    result_card['body'][1]['text'] = f"Created {date}"  # Date message
    result_card['body'][2]['text'] = f"Agent: {test_target}"  # test target
    result_card['body'][3]['text'] = f"Test Target: {url}"  # url
    result_card['body'][4]['text'] = status  # Status message
    result_card['body'][5]['facts'][0]['value'] = str(code)  # Response Code
    result_card['body'][5]['facts'][1]['value'] = f"{total} ms"  # Total Response Time
    result_card['body'][5]['facts'][2]['value'] = f"{loss} %"  # Loss
    result_card['body'][5]['facts'][3]['value'] = f"{latency} ms"  # Average Latency
    result_card['body'][5]['facts'][4]['value'] = f"{jitter} ms"  # Jitter
    result_card['body'][5]['facts'][5]['value'] = f"{cpu} %"  # CPU

    return result_card


def send_result(result, sender, api_object, test_target):
    """
    Callable method for scheduler, create and send webex card with ThousandEyes test results
    :param test_target: Target of Test (Endpoint Hostname, Enterprise Agent Name)
    :param result - ThousandEyes response from creating tests
    :param sender - personId to send card to in Webex
    :param api_object - webexteamssdk api instance
    """
    # Generate Card Data (ThousandEyes Test Results)
    card = generate_result(result, test_target)

    if card:
        # Build Webex Card
        card_base = json.loads(config.CARD_BASE)
        card_base['content'] = card

        # Send Card to Webex
        api_object.messages.create(toPersonId=sender,
                                   text='ThousandEyes Webex Card Results',
                                   attachments=[card_base])
        console.print(f'[green]Webex result delivered![/]')
    else:
        # Send Error Message
        error_message = f"**Error:**  \nUnable to parse test results from ThousandEyes API for target: '{test_target}'\n\n**Results:**  \n```{result}```"
        api_object.messages.create(toPersonId=sender,
                                   markdown=error_message)


def schedule_result(result, sender, job_store, api_object, test_target):
    """
    Scheduled job to send result cards at a specific time
    :param test_target: Target of Test (Endpoint Hostname, Enterprise Agent Name)
    :param result - ThousandEyes response for creating tests
    :param sender - personId from Webex
    :param job_store - apscheduler scheduler instance
    :param api_object - webexteamssdk api instance
    """
    now = datetime.datetime.now()
    if 'endpointTest' in result.keys():
        interval = int(result['endpointTest'][0]['interval']) + 10
    else:
        interval = 70
    delta = datetime.timedelta(0, interval)
    when = now + delta

    console.print(f'Scheduling Webex Result Delivery at {when}...')
    job_store.add_job(send_result, trigger='date', run_date=when, args=[result, sender, api_object, test_target])
