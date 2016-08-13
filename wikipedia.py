#!/usr/bin/python
import unicodedata
import json
import time
import sys
import os

from lib import requests
from utils import *


def search(query, lang, max_hits):
    """Use Wikipedia's search API to find matches
    """
    # Convert Alfred's decomposed utf-8 to composed as expected by the endpoint
    q = unicodedata.normalize('NFC', query.decode('utf-8')).encode('utf-8')
    try:
        response = requests.get(
            url='https://{lang}.wikipedia.org/w/api.php'.format(lang=lang),
            params={'action': 'query',
                    'format': 'json',
                    'utf8': '',
                    # Build generator
                    'generator': 'search',
                    'gsrsearch': q,
                    'gsrlimit': max_hits,
                    # Get properties
                    'prop': 'extracts|info',
                    'explaintext': '',
                    'exintro': '',
                    'exlimit': 'max',
                    'exsentences': '1',
                    'inprop': 'url'})
        response.raise_for_status()  # Raise error on 4xx and 5xx status codes
        response = json.loads(response.content.decode('utf-8'))
        results = response['query']['pages'].values()
    except KeyError:
        raise ResultsException(query)
    except requests.exceptions.RequestException as e:
        raise RequestException(e.request)

    return results


def language(query):
    lang, query = query.split('.')
    return lang.strip(), query.strip()


def alfred_item(result, lang):
    """Return result dictionary in Alfred format
    """
    title = result['title']
    subtitle = result['extract']
    url = result['fullurl']
    mobile_url = url_to_mobile(url)
    dbpedia_url = url_to_dbpedia(url)

    return {
        'title': title,
        'subtitle': subtitle,
        'arg': url,  # Passed on to action
        'uid': title,  # Used to learn order
        'autocomplete': lang + '. ' + title,  # Added to search field
        'quicklookurl': mobile_url,  # Opened on quick look
        'text': {'copy': url,  # Pasted to clipboard
                 'largetype': title},  # Shown in large
        'mods': {
            # Hold cmd to open mobile Wikipedia (better for reading)
            'cmd': {'arg': mobile_url,
                    'subtitle': 'Open in mobile version'},
            # Hold ctrl to open DBpedia page
            'ctrl': {'arg': dbpedia_url,
                     'subtitle': 'Open in DBpedia'}}}


def alfred_output(results, lang):
    """Return Alfred output
    """
    items = [alfred_item(result, lang) for result in results]
    return json.dumps({'items': items}, ensure_ascii=False).encode('utf-8')


def alfred_error(e, query):
    message = e.message if hasattr(e, 'message') else e
    return json.dumps({'items': [{
        'title': "Search Google for '{0}'".format(query),
        'subtitle': str(message),
        'arg': 'https://www.google.de/#q={0}'.format(query)}]})


if __name__ == "__main__":
    # Get settings
    max_hits = os.getenv('maxHits') or 9
    lang = os.getenv('defaultLang') or 'en'
    # Get query
    query = sys.argv[1]
    if '.' in query:
        lang, query = language(query)
    # Check non-empty input
    if not query:
        # Keep Alfred from removing the placeholder
        time.sleep(2)
        quit()
    # Try connection
    try:
        # Get matches for input
        hits = search(query, lang, max_hits)
        # Return Alfred output
        output = alfred_output(hits, lang)
        print(output)
    except Exception as e:
        # Return error
        print(alfred_error(e, query))
