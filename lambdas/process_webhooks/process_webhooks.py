import base64
import json
import logging
import os

import boto3
import botocore.session
from botocore.vendored.requests import post
from github3 import login

logger = logging.getLogger()

# First log the function load message, then change
# the level to be configured via environment variable.
logger.setLevel(logging.INFO)
logger.info('Loading function')

# Log level is set as a string, default to 'INFO'
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
numeric_level = getattr(logging, log_level, None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: {}'.format(log_level))
logger.setLevel(numeric_level)


def _get_target_url(headers):
    """
    Get the target URL for the processed hooks from the
    OS environment variable. Based on the GitHub event,
    add the proper endpoint.
    Return the target URL with the appropriate endpoint
    """
    url = os.environ.get('TARGET_URL')
    if not url:
        raise StandardError(
            "Environment variable TARGET_URL was not set"
        )

    event_type = headers.get('X-GitHub-Event')

    # Based on the X-Github-Event header, determine the
    # proper endpoint for the target url.
    # PR's and Issue Comments use the ghprb Jenkins plugin
    # Pushes use the Github Jenkins plugin
    if event_type in ["issue_comment", "pull_request"]:
        endpoint = "ghprbhook/"
    elif event_type == "push":
        endpoint = "github-webhook/"
    elif event_type == "ping":
        return None
    else:
        raise StandardError(
            "The Spigot does not support webhooks of "
            "type: {}".format(event_type)
        )

    return url + "/" + endpoint


def _get_target_queue():
    """
    Get the target SQS name for the processed hooks from the
    OS environment variable.
    Return the name of the queue
    """
    queue_name = os.environ.get('TARGET_QUEUE')
    if not queue_name:
        raise StandardError(
            "Environment variable TARGET_QUEUE was not set"
        )

    return queue_name


def _get_gh_token_from_s3():
    """
    Get the token required for posting to
    github prs from s3.
    The expected object is a JSON file formatted as:
    {
        "token": "sampletoken123"
    }
    """
    session = botocore.session.get_session()
    client = session.create_client('s3')

    creds_file = client.get_object(
        Bucket='edx-tools-credentials-hack',
        Key='github-token.json'
    )
    creds = json.loads(creds_file['Body'].read())

    if not creds.get("token"):
        raise StandardError(
            'Credentials json file needs to '
            'contain a value for token'
        )

    return creds.get("token")


def _post_to_gh_pr(payload, event_type, is_spigot_on):
    """
    Post to the github PR that the spigot is on/off.
    """
    on_comment = 'Jenkins is back online and the queue is ' \
              'being drained. Testing will resume ' \
              'momentarily.'
    off_comment = 'Jenkins is down or under maintenance. The ' \
              'webhook generated from this PR has ' \
              'been queued and testing will occur soon. '
    if is_spigot_on:
        comment = on_comment
    else:
        comment = off_comment

    if event_type == "pull_request":
        gh_token = _get_gh_token_from_s3()

        if payload["action"] != "closed":
            pr_number = payload["number"]
            repo_name = payload["repository"]["name"]
            user = payload["repository"]["owner"]["login"]

            gh = login(token=gh_token)
            repo = gh.repository(user, repo_name)
            pull_request_object = repo.issue(pr_number)

            pull_request_object.create_comment(comment)


def _add_gh_header(event, headers):
    """
    Get the X-GitHub-Event header from the original request
    data, add this to the headers, and return the results.
    Raise an error if the GitHub event header is not found.
    """
    gh_headers = event.get('headers')
    gh_event = gh_headers.get('X-GitHub-Event')
    if not gh_event:
        msg = 'X-GitHub-Event header was not found in {}'.format(gh_headers)
        raise ValueError(msg)

    logger.debug('GitHub event was: {}'.format(gh_event))
    headers['X-GitHub-Event'] = gh_event
    return headers


def _is_from_queue(event):
    """
    Check to see if this webhook is being sent from the SQS queue.
    This is important to avoid duplicating the hook in the queue
    in the event of a failure.
    """
    return event.get('from_queue') == "True"


def _send_message(url, payload, headers):
    """ Send the webhook to the endpoint via an HTTP POST.
    Args:
        url (str): Target URL for the POST request
        payload (dict): Payload to send
        headers (dict): Dictionary of headers to send
    Returns:
        The response from the HTTP POST
    """
    response = post(url, json=payload, headers=headers, timeout=(3.05, 30))
    # Trigger the exception block for 4XX and 5XX responses
    response.raise_for_status()
    return response


def _send_to_queue(event, queue_name):
    """
    Send the webhook to the SQS queue.
    """
    try:
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=queue_name)
    except:
        raise StandardError("Unable to find the target queue")

    try:
        response = queue.send_message(MessageBody=json.dumps(event))
    except:
        raise StandardError("The message could not be sent to queue")

    return response


def lambda_handler(event, _context):
    # Determine if this message is coming from the queue
    from_queue = _is_from_queue(event)

    # The header we send should include the original GitHub header,
    # and also is set to send the data in the format that Jenkins expects.
    header = {'Content-Type': 'application/json'}

    # Add the headers from the event
    headers = _add_gh_header(event, header)
    logger.debug("headers are: '{}'".format(headers))

    event_type = headers.get('X-GitHub-Event')

    # Get the state of the spigot from the api variable
    spigot_state = event.get('spigot_state')
    logger.info(
        "spigot_state is set to: {}".format(spigot_state)
    )

    # We had stored the payload to send in the
    # 'body' node of the data object.
    payload = event.get('body')
    logger.debug("payload is: '{}'".format(payload))

    if spigot_state == "ON":
        # Get the url that the webhook will be sent to
        url = _get_target_url(headers)

        if not url:
            # If url is None, swallow the hook, since it is just a ping
            return (
                "Received a ping webhook. No action required."
            )

        # Send it off!
        try:
            _result = _send_message(url, payload, headers)
            if from_queue:
                _post_to_gh_pr(payload, event_type, True)
        except:
            if not from_queue:
                # The transmission was a failure, if it's not
                # already in the queue, add it.
                queue_name = _get_target_queue()
                _response = _send_to_queue(event, queue_name)
            raise StandardError(
                "There was an error sending the message "
                "to the url: {}".format(url)
            )
        return (
            "Webhook successfully sent to url: {}".format(url)
        )
    elif spigot_state == "OFF":
        # Since the spigot is off, send the event
        # to SQS for future processing. However,
        # if the message is already in the queue do
        # nothing.
        if from_queue:
            raise StandardError(
                "The spigot is OFF. No messages should be "
                "sent from the queue."
            )
        else:
            queue_name = _get_target_queue()
            _response = _send_to_queue(event, queue_name)

            _post_to_gh_pr(payload, event_type, False)

            return (
                "Webhook successfully sent to queue: {}".format(queue_name)
            )
    else:
        raise StandardError(
            "API Gateway stage variable spigot_state "
            "was not correctly set. Should be ON or OFF, "
            "was: {}".format(spigot_state)
        )
