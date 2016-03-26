#!/usr/bin/env python
"""An Alexa skill to record dirty diapers in the Baby Tracker app.

http://nighp.com/babytracker/
"""

import base64
import datetime
import json
import requests
import uuid

URL = "https://prodapp.babytrackers.com"

CONFIG = json.load(open("config.json"))
assert set(CONFIG.keys()) == {"device_id", "email_address", "password", "application_id"}

# TODO: load this from the baby tracker server
BABY_DATA = json.load(open("baby_data.json"))
assert set(BABY_DATA.keys()) == {
    "dueDay",
    "BCObjectType",
    "gender",
    "pictureName",
    "dob",
    "newFlage",
    "timestamp",
    "name",
    "objectID",
}

# TODO: figure out what portion of this is required
LOGIN_DATA = {
    "Device": {
        "DeviceOSInfo": "Alexa",
        "DeviceName": "Baby Tracker Alexa App",
        # TODO: grab something from either the Alexa device or the lambda function
        "DeviceUUID": CONFIG["device_id"]
    },
    # TODO: I don't know what this means
    "AppInfo": {
        "AppType": 0,
        "AccountType": 0
    },
    "Password": CONFIG["password"],
    "EmailAddress": CONFIG["email_address"]
}

DIAPER_STATUS = {
    "wet": 0,
    "dirty": 1,
    "poopy": 1,
    "mixed": 2,
    "dry": 3
}

## Generic Alexa -- this is pretty generic Alexa boilerplate.

def lambda_handler(event, context):
    # Ensure that we're being called by the expected application.
    application_id = CONFIG["application_id"]
    if application_id is not None and (
            event["session"]["application"]["applicationId"] != application_id):
        raise ValueError("Invalid Application ID")

    if event["request"]["type"] == "LaunchRequest":
        # TODO: Give a reasonable welcome speech.
        #return on_launch(event["request"], event["session"])
        pass
    elif event["request"]["type"] == "IntentRequest":
        return on_intent(event["request"], event["session"])

def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    intent = intent_request["intent"]
    intent_name = intent_request["intent"]["name"]

    if intent_name == "RecordDiaperIntent":
        return record_diaper_intent(intent, session)
    raise ValueError("Invalid intent")

def build_speechlet_response(title, output, reprompt_text=None, should_end_session=True):
    result = {
        "outputSpeech": {
            "type": "PlainText",
            "ssml": output
        },
        "card": {
            "type": "Simple",
            # TODO: Make these more resonable for this app.
            "title": "SessionSpeechlet - " + title,
            "content": "SessionSpeechlet - " + output
        },
        "reprompt": {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text
            }
        },
        "shouldEndSession": should_end_session
    }
    if reprompt_text is not None:
        result["reprompt"] = {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text
            }
        }
    return result

def build_response(response):
    # right now we don't use sessionAttributes
    return {
        "version": "1.0",
        "response": response
    }

## Baby Tracker Sync -- these functions are on the Baby Tracker side of the skill.

def generate_diaper_data(status):
    return {
        "BCObjectType": "Diaper",
        # These default to 5s on some apps (iPhone, I think) and 0s on others (Android?).
        # They don't seem to be used anywhere, though, so the values we set here don't
        # seem important.
        "pooColor": 5,
        "peeColor": 5,
        "note": "",
        # now
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S +0000"),
        "newFlage": "true",
        "pictureLoaded": "true",
        # Time of diaper. We could let people provide this time, but at the moment
        # there doesn't seem like a lot of benefit.
        "time": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S +0000"),
        "objectID": str(uuid.uuid1()),
        "texture": 5,
        "amount": 2,
        "baby": BABY_DATA,
        "flag": 0,
        "pictureNote": [],
        "status": status
    }

def generate_diaper_sync_data(status, sync_id):
    return {
        "Transaction": base64.b64encode(json.dumps(generate_diaper_data(status))),
        "SyncID": sync_id,
        # This is sometimes 0, sometimes 1. Not sure if ever higher. Not sure what it's for.
        "OPCode": 0
    }

def last_sync_id(session):
    response = session.get(URL + "/account/device")
    devices = json.loads(response.text)
    for device in devices:
        if device["DeviceUUID"] == CONFIG["device_id"]:
            return device["LastSyncID"]
    return 0

def record_diaper(status):
    session = requests.Session()
    r = session.post(URL + "/session", data=json.dumps(LOGIN_DATA))
    sync_id = last_sync_id(session) + 1
    session.post(URL + "/account/transaction", data=json.dumps(generate_diaper_sync_data(status, sync_id)))

## Intents -- these are somewhere between being on the Alexa side and being on the Baby Tracker side

def record_diaper_intent(intent, session):
    diaper_type = intent["slots"]["DiaperType"]["value"]
    record_diaper(DIAPER_STATUS[diaper_type])
    return build_response(build_speechlet_response(
        "Record Diaper", "{} diaper recorded.".format(diaper_type)))

if __name__ == "__main__":
    # record a wet diaper
    record_diaper(0)
