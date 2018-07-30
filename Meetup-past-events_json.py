#!/usr/bin/env python3

import collections
import datetime
import pprint

import click
import jinja2
import requests
import json

template = '''
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <meta name=viewport content="width=device-width, initial-scale=1.0">
        <style type="text/css">
            td.date_pretty {
                text-align: right;
            }
        </style>
    </head>
    <body>
        <h1>Previous events for <a href="http://www.meetup.com/{{ group_name }}/">{{ group_name }}</a>
        {% for grouping_name, events in groupings.items() %}
        <h2>{{ grouping_name }}</h2>
        <table>{% for i in events %}
            <tr><td class="date_pretty">{{ i.date_pretty }}</td><td><a href="{{ i.event_url }}">{{ i.name }}</a></td></tr>
         {%- endfor %}</table>
        {% endfor %}
    </body>
</html>
'''

default_payload = { 'status': 'past' }

def generate_html(group_name, g):
    global template

    je = jinja2.Environment()
    jt = je.from_string(template)

    out = jt.render(group_name=group_name, groupings=g)
    return out


def generate_events(group_name, api_key):
    offset = 0
    while True:
        offset_payload = { 'offset': offset,
                           'key': api_key,
                           'group_urlname': group_name }
        payload = default_payload.copy()
        payload.update(offset_payload)
        # Above is the equivalent of jQuery.extend()
        # for Python 3.5: payload = {**default_payload, **offset_payload}

        r = requests.get('https://api.meetup.com/2/events', params=payload)
        json = r.json()

        results, meta = json['results'], json['meta']
        for item in results:
            yield item

        # if we no longer have more results pages, stop…
        if not meta['next']:
            return

        offset = offset + 1


@click.command()
@click.option('--groupname', 'group_name', default='jornadahikers', help='Name of group in Meetup.com URL, i.e. http://meetup.com/<groupname>/')
@click.option('--apikey', 'api_key', envvar='MEETUP_API_KEY', help='Your Meetup.com API key, from https://secure.meetup.com/meetup_api/key/')
@click.option('--printjson/--no-printjson', default=False, help='Dump JSON instead of HTML')
def go(group_name, api_key, printjson):

    all_events = list(generate_events(group_name, api_key))

    if printjson is True:
        events_json = json.dumps(all_events, indent=2, separators=(',', ': '))
        print(events_json)
        return

    for event in all_events:
        # convert time returned by Meetup API
        time = int(event['time'])/1000
        time_obj = datetime.datetime.fromtimestamp(time)

        # create a pretty-looking date, and group by month
        date_pretty = time_obj.strftime('%a %b %-d')
        grouping_name = time_obj.strftime('%b %Y')

        event['grouping_name'] = grouping_name
        event['date_pretty'] = date_pretty

    # group by month
    groupings = collections.OrderedDict()
    for event in all_events:
        grouping_name = event['grouping_name']

        grouping = groupings.get(grouping_name, [])
        grouping.append(event)
        groupings[grouping_name] = grouping

    print(generate_html(group_name, groupings))

if __name__ == '__main__':
    go()
