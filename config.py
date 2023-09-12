# Webex Bot
BOT_TOKEN = ''
BOT_EMAIL = ''
WEBHOOK_BASE_URL = ""

# ThousandEyes
THOUSAND_EYES_TOKEN = ''

# Card Payload to launch tests
CARD_PAYLOAD = """{
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.2",
    "body": [
        {
            "type": "TextBlock",
            "size": "Large",
            "weight": "Bolder",
            "text": "ThousandEyes Instant Test(s)",
            "horizontalAlignment": "Center",
            "color": "Light"
        },
        {
            "type": "Input.Text",
            "placeholder": "Enterprise Agent Name (case-sensitive)",
            "style": "text",
            "maxLength": 0,
            "id": "sitenameVal"
        },
        {
            "type": "Input.Text",
            "placeholder": "Endpoint Agent Device Hostname (case-sensitive)",
            "style": "text",
            "maxLength": 0,
            "id": "hostnameVal"
        },
        {
            "type": "TextBlock",
            "text": "Which applications are experiencing issue? (multiselect)"
        },
        {
            "type": "Input.ChoiceSet",
            "id": "IssueSelectVal",
            "isMultiSelect": true,
            "choices": [
                {
                    "title": "Office 365",
                    "value": "Office365"
                },
                {
                    "title": "Webex Audio",
                    "value": "WebexAudio"
                },
                {
                    "title": "Webex Video",
                    "value": "WebexVideo"
                },
                {
                    "title": "SalesForce",
                    "value": "salesforce"
                }
            ]
        },
        {
            "type": "TextBlock",
            "text": "Custom URL (if None of the above selected)"
        },
        {
            "type": "Input.Text",
            "placeholder": "What's the url of the application?",
            "style": "text",
            "maxLength": 0,
            "id": "CustomURLVal"
        }
    ],
    "actions": [
        {
            "type": "Action.Submit",
            "title": "Submit",
            "data": {
                "action": "newTest",
                "id": "inputTypesExample"
            }
        }
    ]
}
    }"""

# Card payload for result card
CARD_BASE = """{
      "contentType": "application/vnd.microsoft.card.adaptive",
      "content": {}
    }"""

RESULT_CARD = """{
    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
    "type": "AdaptiveCard",
    "version": "1.2",
    "body": [
        {
            "type": "TextBlock",
            "text": "ThousandEyes Test Result",
            "weight": "Bolder",
            "size": "Medium"
        },
        {
            "type": "TextBlock",
            "spacing": "None",
            "text": "Created {{DATE(2020-02-14T06:08:39Z, SHORT)}}",
            "isSubtle": true,
            "wrap": true
        },
        {
            "type": "TextBlock",
            "text": "www.google.com",
            "weight": "Bolder",
            "wrap": true
        },
        {
            "type": "TextBlock",
            "text": "www.google.com",
            "weight": "Bolder",
            "wrap": true
        },
        {
            "type": "TextBlock",
            "text": "Everything seems normal!",
            "wrap": true
        },
        {
            "type": "FactSet",
            "facts": [
                {
                    "title": "Response:",
                    "value": "200 Okay"
                },
                {
                    "title": "Total Response Time:",
                    "value": "252ms"
                },
                {
                    "title": "Loss:",
                    "value": "1%"
                },
                {
                    "title": "Average Latency:",
                    "value": "251ms"
                },
                {
                    "title": "Jitter:",
                    "value": "10ms"
                },
                {
                    "title": "Average CPU Usage:",
                    "value": "10ms"
                }
            ]
        }
    ]
}"""