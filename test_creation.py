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

import concurrent.futures
import json

import requests

import config

""""     Test URLs       """

PrimaryCBServerURL = "https://ed1sgcb191.webex.com"
SecondaryCBServerURL = "https://epycb16302.webex.com"
WebExPrimaryAudioURL = "msg2mcs136.webex.com"
WebExSecondaryAudioURL = "gmjp2mcs192.webex.com"
WebExPrimaryVideoURL = "msg2mcs136.webex.com"
WebExSecondaryVideoURL = "gmjp2mcs192.webex.com"
SalesforceURL = "https://ciscosales.my.salesforce.com/"
O365URL = "https://login.microsoftonline.com"

# Define Global ThousandEyes Header
headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f"Bearer {config.THOUSAND_EYES_TOKEN}"
}

# Define Global ThousandEyes Instant Test Endpoints
endpoint_instant_test_url = "https://api.thousandeyes.com/v6/endpoint-instant/http-server.json"
endpoint_instant_test_agent_to_server_url = "https://api.thousandeyes.com/v6/endpoint-instant/agent-to-server.json"

enterprise_instant_test_url = "https://api.thousandeyes.com/v6/instant/http-server.json"
enterprise_instant_test_agent_to_server_url = "https://api.thousandeyes.com/v6/instant/agent-to-server.json"


def api_call_wrapper(api_function, agent_id, test_type, resultArray, CustomURL=None):
    """
    Wrapper function for test methods, allows parallelization and increased performance
    :param CustomURL: Customer URL (if provided)
    :param api_function: Test Function
    :param agent_id: Endpoint or Enterprise Agent ID
    :param test_type: test type (options: endpoint, enterprise)
    :param resultArray: List of test results
    """
    if CustomURL:
        resultArray.append(api_function(agent_id, CustomURL, test_type))
    else:
        resultArray.append(api_function(agent_id, test_type))


def find_endpoint_agent_id(hostname):
    """
    Find Endpoint Agent unique ID based on computer hostname
    :param hostname: Endpoint computer hostname
    :return: Endpoint Agent ID
    """
    # Define Endpoint URL
    url = f"https://api.thousandeyes.com/v6/endpoint-agents.json?computerName={hostname}"
    response = requests.get(url, headers=headers, data="")

    if response.ok:
        response_json = json.loads(response.text)

        if len(response_json["endpointAgents"]) > 0:
            return response_json["endpointAgents"][0]["agentId"]
        else:
            # No endpoint agent found with that host name
            return None

    return None


def find_enterprise_agent_id(agent_name):
    """
    Find Enterprise Agent unique ID based on agent name
    :param agent_name: Enterprise agent name
    :return: Enterprise Agent ID
    """
    # Define Endpoint URL (enterprise agents only)
    url = f"https://api.thousandeyes.com/v6/agents.json?agentTypes=ENTERPRISE"
    response = requests.get(url, headers=headers, data="")

    if response.ok:
        response_json = json.loads(response.text)

        # Iterate through Enterprise Agents identify the correct agent id
        agents = response_json['agents']
        for agent in agents:
            if agent['agentName'] == agent_name:
                return agent['agentId']

    return None


def test_selector(agent_id, webex_card_data, test_type):
    """
    Conduct ThousandEyes instant test from various pre-built options or a custom url
    :param agent_id: Endpoint or Enterprise Agent ID
    :param webex_card_data: Card data containing selected test, custom url, etc.
    :param test_type: test type (options: endpoint, enterprise)
    :return: list of test results from ThousandEyes apis
    """
    # Selected applications to run tests on (checkboxes)
    issueArray = webex_card_data["IssueSelectVal"].split(",")

    # For each app, launch the dedicated instant test (using the global urls defined above), append results to list
    resultArray = []

    # Execute instant tests in parallel using futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []

        for issue in issueArray:
            if issue == "WebexAudio":
                futures.append(executor.submit(api_call_wrapper, webex_primary_audio, agent_id, test_type, resultArray))
                futures.append(
                    executor.submit(api_call_wrapper, webex_secondary_audio, agent_id, test_type, resultArray))
                futures.append(
                    executor.submit(api_call_wrapper, webex_primary_cb_server, agent_id, test_type, resultArray))
                futures.append(
                    executor.submit(api_call_wrapper, webex_secondary_cb_server, agent_id, test_type, resultArray))
            elif issue == "WebexVideo":
                futures.append(executor.submit(api_call_wrapper, webex_primary_video, agent_id, test_type, resultArray))
                futures.append(
                    executor.submit(api_call_wrapper, webex_secondary_video, agent_id, test_type, resultArray))
                futures.append(
                    executor.submit(api_call_wrapper, webex_primary_cb_server, agent_id, test_type, resultArray))
                futures.append(
                    executor.submit(api_call_wrapper, webex_secondary_cb_server, agent_id, test_type, resultArray))
            elif issue == "salesforce":
                futures.append(executor.submit(api_call_wrapper, salesforce, agent_id, test_type, resultArray))
            elif issue == "Office365":
                futures.append(executor.submit(api_call_wrapper, o365_test, agent_id, test_type, resultArray))

        # Special custom url case: extract url, then pass url to custom test method
        CustomURL = webex_card_data["CustomURLVal"]

        if CustomURL != '':
            futures.append(
                executor.submit(api_call_wrapper, custom_endpoint_test, agent_id, test_type, resultArray, CustomURL))

        # Wait for all tasks to complete
        for future in concurrent.futures.as_completed(futures):
            future.result()  # This is just to wait for the task to complete, the result is already appended in the
            # wrapper function

    return resultArray


def webex_primary_cb_server(agent_id, test_type):
    """
    ThousandEyes Instant Test for Webex Primary CB Service
    :param agent_id: Endpoint or Enterprise Agent ID
    :param test_type: test type (options: endpoint, enterprise)
    :return: ThousandEyes Instant Test result
    """
    # Case 1: Endpoint Test
    if test_type == 'endpoint':
        url = endpoint_instant_test_url
        payload = json.dumps({
            "agentSelectorType": "SPECIFIC_AGENTS",
            "agentIds": [agent_id],
            "authType": "NONE",
            "flagPing": True,
            "flagTraceroute": True,
            "httpTimeLimit": 5000,
            "maxMachines": 5,
            "sslVersion": 0,
            "targetResponseTime": 1000,
            "testName": "WebEx Primary CB Server Endpoint Instant HTTP test",
            "url": PrimaryCBServerURL,
            "verifyCertHostname": True
        })
    # Case 2: Enterprise Test
    else:
        url = enterprise_instant_test_url
        payload = json.dumps({
            "agents": [
                {
                    "agentId": agent_id
                }
            ],
            "testName": "WebEx Primary CB Server Enterprise Instant HTTP test",
            "url": PrimaryCBServerURL
        })

    response = requests.post(url, headers=headers, data=payload)
    return response.text


def webex_secondary_cb_server(agent_id, test_type):
    """
    ThousandEyes Instant Test for Webex Secondary CB Service
    :param agent_id: Endpoint or Enterprise Agent ID
    :param test_type: test type (options: endpoint, enterprise)
    :return: ThousandEyes Instant Test result
    """
    # Case 1: Endpoint Test
    if test_type == 'endpoint':
        url = endpoint_instant_test_url
        payload = json.dumps({
            "agentSelectorType": "SPECIFIC_AGENTS",
            "agentIds": [agent_id],
            "authType": "NONE",
            "flagPing": True,
            "flagTraceroute": True,
            "httpTimeLimit": 5000,
            "maxMachines": 5,
            "sslVersion": 0,
            "targetResponseTime": 1000,
            "testName": "WebEx Secondary CB Server Endpoint Instant HTTP test",
            "url": SecondaryCBServerURL,
            "verifyCertHostname": True
        })
    # Case 2: Enterprise Test
    else:
        url = enterprise_instant_test_url
        payload = json.dumps({
            "agents": [
                {
                    "agentId": agent_id
                }
            ],
            "testName": "WebEx Secondary CB Server Enterprise Instant HTTP test",
            "url": SecondaryCBServerURL
        })

    response = requests.post(url, headers=headers, data=payload)
    return response.text


def webex_primary_audio(agent_id, test_type):
    """
    ThousandEyes Instant Test for Webex Primary Audio Service
    :param agent_id: Endpoint or Enterprise Agent ID
    :param test_type: test type (options: endpoint, enterprise)
    :return: ThousandEyes Instant Test result
    """
    # Case 1: Endpoint Test
    if test_type == 'endpoint':
        url = endpoint_instant_test_agent_to_server_url
        payload = json.dumps({
            "agentSelectorType": "SPECIFIC_AGENTS",
            "agentIds": [agent_id],
            "flagPing": True,
            "flagTraceroute": True,
            "maxMachines": 5,
            "testName": "Webex Primary Audio Endpoint Instant Test",
            "serverName": WebExPrimaryAudioURL,
            "port": 5004
        })
    # Case 2: Enterprise Test
    else:
        url = enterprise_instant_test_agent_to_server_url
        payload = json.dumps({
            "agents": [
                {
                    "agentId": agent_id
                }
            ],
            "testName": "Webex Primary Audio Enterprise Instant HTTP test",
            "server": WebExPrimaryAudioURL,
            "interval": 900
        })

    response = requests.post(url, headers=headers, data=payload)
    return response.text


def webex_secondary_audio(agent_id, test_type):
    """
    ThousandEyes Instant Test for Webex Secondary Audio Service
    :param agent_id: Endpoint or Enterprise Agent ID
    :param test_type: test type (options: endpoint, enterprise)
    :return: ThousandEyes Instant Test result
    """
    # Case 1: Endpoint Test
    if test_type == 'endpoint':
        url = endpoint_instant_test_agent_to_server_url
        payload = json.dumps({
            "agentSelectorType": "SPECIFIC_AGENTS",
            "agentIds": [agent_id],
            "flagPing": True,
            "flagTraceroute": True,
            "maxMachines": 5,
            "testName": "Webex Secondary Audio Endpoint Instant Test",
            "serverName": WebExSecondaryAudioURL,
            "port": 5004
        })
    # Case 2: Enterprise Test
    else:
        url = enterprise_instant_test_agent_to_server_url
        payload = json.dumps({
            "agents": [
                {
                    "agentId": agent_id
                }
            ],
            "testName": "Webex Secondary Audio Enterprise Instant HTTP test",
            "server": WebExSecondaryAudioURL,
            "interval": 900
        })

    response = requests.post(url, headers=headers, data=payload)
    return response.text


def webex_primary_video(agent_id, test_type):
    """
    ThousandEyes Instant Test for Webex Primary Video Service
    :param agent_id: Endpoint or Enterprise Agent ID
    :param test_type: test type (options: endpoint, enterprise)
    :return: ThousandEyes Instant Test result
    """
    # Case 1: Endpoint Test
    if test_type == 'endpoint':
        url = endpoint_instant_test_agent_to_server_url
        payload = json.dumps({
            "agentSelectorType": "SPECIFIC_AGENTS",
            "agentIds": [agent_id],
            "flagPing": True,
            "flagTraceroute": True,
            "maxMachines": 5,
            "testName": "Webex Primary Video Endpoint Instant Test",
            "serverName": WebExPrimaryVideoURL,
            "port": 5004
        })
    # Case 2: Enterprise Test
    else:
        url = enterprise_instant_test_agent_to_server_url
        payload = json.dumps({
            "agents": [
                {
                    "agentId": agent_id
                }
            ],
            "testName": "Webex Primary Video Enterprise Instant HTTP test",
            "server": WebExPrimaryVideoURL,
            "interval": 900
        })

    response = requests.post(url, headers=headers, data=payload)
    return response.text


def webex_secondary_video(agent_id, test_type):
    """
    ThousandEyes Instant Test for Webex Secondary Video Service
    :param agent_id: Endpoint or Enterprise Agent ID
    :param test_type: test type (options: endpoint, enterprise)
    :return: ThousandEyes Instant Test result
    """
    # Case 1: Endpoint Test
    if test_type == 'endpoint':
        url = endpoint_instant_test_agent_to_server_url
        payload = json.dumps({
            "agentSelectorType": "SPECIFIC_AGENTS",
            "agentIds": [agent_id],
            "flagPing": True,
            "flagTraceroute": True,
            "maxMachines": 5,
            "testName": "Webex Secondary Video Endpoint Instant Test",
            "serverName": WebExSecondaryVideoURL,
            "port": 5004
        })
    # Case 2: Enterprise Test
    else:
        url = enterprise_instant_test_agent_to_server_url
        payload = json.dumps({
            "agents": [
                {
                    "agentId": agent_id
                }
            ],
            "testName": "Webex Secondary Video Enterprise Instant HTTP test",
            "server": WebExSecondaryVideoURL,
            "interval": 900
        })

    response = requests.post(url, headers=headers, data=payload)
    return response.text


def salesforce(agent_id, test_type):
    """
    ThousandEyes Instant Test for SalesForce Service
    :param agent_id: Endpoint or Enterprise Agent ID
    :param test_type: test type (options: endpoint, enterprise)
    :return: ThousandEyes Instant Test result
    """
    # Case 1: Endpoint Test
    if test_type == 'endpoint':
        url = endpoint_instant_test_url
        payload = json.dumps({
            "agentSelectorType": "SPECIFIC_AGENTS",
            "agentIds": [agent_id],
            "authType": "NONE",
            "flagPing": True,
            "flagTraceroute": True,
            "httpTimeLimit": 5000,
            "maxMachines": 5,
            "sslVersion": 0,
            "targetResponseTime": 5000,
            "testName": "Salesforce Endpoint Instant HTTP test",
            "url": SalesforceURL,
            "verifyCertHostname": True
        })
    # Case 2: Enterprise Test
    else:
        url = enterprise_instant_test_url
        payload = json.dumps({
            "agents": [
                {
                    "agentId": agent_id
                }
            ],
            "testName": "Salesforce Enterprise Instant HTTP test",
            "url": SalesforceURL
        })

    response = requests.post(url, headers=headers, data=payload)
    return response.text


def custom_endpoint_test(agent_id, custom_url, test_type):
    """
    ThousandEyes Instant Test for custom url
    :param custom_url: customer url (format: youtube.com - https:// not strictly required)
    :param agent_id: Endpoint or Enterprise Agent ID
    :param test_type: test type (options: endpoint, enterprise)
    :return: ThousandEyes Instant Test result
    """
    # Case 1: Endpoint Test
    if test_type == 'endpoint':
        url = endpoint_instant_test_url
        payload = json.dumps({
            "agentSelectorType": "SPECIFIC_AGENTS",
            "agentIds": [agent_id],
            "authType": "NONE",
            "flagPing": True,
            "flagTraceroute": True,
            "httpTimeLimit": 5000,
            "maxMachines": 5,
            "sslVersion": 0,
            "targetResponseTime": 5000,
            "testName": "Custom URL Endpoint Instant HTTP test",
            "url": custom_url,
            "verifyCertHostname": True
        })
    # Case 2: Enterprise Test
    else:
        url = enterprise_instant_test_url
        payload = json.dumps({
            "agents": [
                {
                    "agentId": agent_id
                }
            ],
            "testName": "Custom URL Enterprise Instant HTTP test",
            "url": custom_url
        })

    response = requests.post(url, headers=headers, data=payload)
    return response.text


def o365_test(agent_id, test_type):
    """
    ThousandEyes Instant Test for O365 Service
    :param agent_id: Endpoint or Enterprise Agent ID
    :param test_type: test type (options: endpoint, enterprise)
    :return: ThousandEyes Instant Test result
    """
    # Case 1: Endpoint Test
    if test_type == 'endpoint':
        url = endpoint_instant_test_url
        payload = json.dumps({
            "agentSelectorType": "SPECIFIC_AGENTS",
            "agentIds": [agent_id],
            "authType": "NONE",
            "flagPing": True,
            "flagTraceroute": True,
            "httpTimeLimit": 5000,
            "maxMachines": 5,
            "sslVersion": 0,
            "targetResponseTime": 1000,
            "testName": "O365 Endpoint Instant HTTP test",
            "url": O365URL,
            "verifyCertHostname": True
        })
    # Case 2: Enterprise Test
    else:
        url = enterprise_instant_test_url
        payload = json.dumps({
            "agents": [
                {
                    "agentId": agent_id
                }
            ],
            "testName": "O365 Enterprise Instant HTTP test",
            "url": O365URL
        })

    response = requests.post(url, headers=headers, data=payload)
    return response.text
