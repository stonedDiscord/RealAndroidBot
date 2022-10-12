# Standard Library Imports
import logging
import requests
import time
import traceback

logger = logging.getLogger('rab')


def get_server_time():
    resp = requests.post(url='http://119.161.100.154/get_time', timeout=3)
    if resp.ok is True:
        logger.debug("Successfully get server time (returned {})".format(
            resp.status_code))
        return int(resp.text)
    return False


def send_webhook(url, payload):
    logger.debug(payload)
    resp = requests.post(url, json=payload, timeout=5)
    if resp.ok is True:
        logger.debug("Notification successful (returned {})".format(
            resp.status_code))
    else:
        logger.debug("Discord response was {}".format(resp.content))
        raise requests.exceptions.RequestException(
            "Response received {}, webhook not accepted.".format(
                resp.status_code))


def send_to_telegram(text, cid_pool='-1001415186432'):
    token = "1639290545:AAFipL5QnvJ6Em9D9KtVtJRaqxgOO1YjmeE"
    url = "https://api.telegram.org/bot{token}/sendMessage?chat_id={chat_id}&text={text}" \
        .format(token=token, chat_id=cid_pool, text=text)

    response = requests.post(url=url)
    if response.status_code != 200:
        raise ValueError(
            'Webhook returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )
    return True

# Send Alert to Discord


def send_to_discord(webhook_url, username, content, avatar=None):
    logger.debug("Attempting to send notification to Discord.")

    payload = {
        # Usernames are limited to 32 characters
        'username': username[:32],
        'content': content,
        'avatar_url': avatar
    }

    args = {
        'url': webhook_url,
        'payload': payload
    }
    try_sending("Discord", send_webhook, args)


# Attempts to send the alert multiple times
def try_sending(name, send_alert, args, max_attempts=3):
    for i in range(max_attempts):
        try:
            send_alert(**args)
            return True  # message sent successfully
        except Exception as e:
            logger.error("Encountered error while sending notification"
                         + " ({}: {})".format(type(e).__name__, e))
            logger.debug("Stack trace: \n {}".format(traceback.format_exc()))
            logger.info(
                "{} is having connection issues. {} attempt of {}.".format(
                    name, i + 1, max_attempts))
            time.sleep(3)
    logger.error("Could not send notification... Giving up.")
    return False
