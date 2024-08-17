from .helpers import load_data
from datetime import datetime, timedelta
from . import variables
import requests
import json

gameweeks = load_data("gameweeks.json", "data/original")


def get_cron_date(date):
    '''
    Converts to the given date to cron job format.
    '''

    day = date.day
    month = date.month
    hour = date.hour
    minute = date.minute
    cron = f'{minute} {hour} {day} {month} *'

    return cron


def get_deadline(gameweeks=gameweeks):
    '''
    Get's the next gameweek's deadline and time to notify.
    '''

    now = datetime.utcnow()
    for gameweek in gameweeks:
        next_deadline_date = datetime.strptime(
            gameweek['deadline_time'], '%Y-%m-%dT%H:%M:%SZ')
        if next_deadline_date > now:
            break

    # parse the deadline date into string for email notification
    next_deadline_date = next_deadline_date + timedelta(hours=5, minutes=30)
    next_deadline_date = next_deadline_date.strftime('%d %b, %Y %H:%M')

    return next_deadline_date


def get_gameweek(gameweeks=gameweeks):
    '''
    Get's the next gameweek's ID.
    '''

    now = datetime.utcnow()
    for gameweek in gameweeks:
        next_deadline_date = datetime.strptime(
            gameweek['deadline_time'], '%Y-%m-%dT%H:%M:%SZ')
        if next_deadline_date > now:
            break

    return gameweek['id']


def create_notification_content(transfers):
    '''
    Creates a phone-friendly notification content.
    '''
    content = f"Fantasy AI - Gameweek {get_gameweek()}\n\n"
    content += "Potential Transfers:\n"

    for transfer in transfers:
        content += f"OUT: {transfer['out']['name'].title()} (£{transfer['out']['cost']})\n"
        content += f"IN: {transfer['in']['name'].title()} (£{transfer['in']['cost']})\n"
        content += f"Points: {transfer['points']} | Gain/Loss: {transfer['g/l']}\n\n"

    content += f"Deadline: {get_deadline()}\n"
    content += f"Manage your team: https://fantasy.premierleague.com/entry/{variables.TEAM_ID}/event/{get_gameweek()-1}"

    return content


def send_notification(content):
    '''
    Sends a notification using ntfy.sh.
    '''
    url = os.environ.get('NTFY_URL', 'https://ntfy.sh/fantasy')
    headers = {
        "Title": f"Fantasy AI - GW {get_gameweek()}",
        "Tags": "soccer",
        "Priority": "default"
    }

    response = requests.post(
        url, data=content.encode('utf-8'), headers=headers)
    if response.status_code == 200:
        print("Notification sent successfully")
    else:
        print(
            f"Failed to send notification. Status code: {response.status_code}")


def notify(transfers):
    '''
    Creates and sends a notification with transfer suggestions.
    '''
    content = create_notification_content(transfers)
    send_notification(content)


if __name__ == '__main__':
    print(get_gameweek())
