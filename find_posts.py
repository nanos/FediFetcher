#!/usr/bin/env python3

from datetime import datetime, timedelta
from dateutil import parser
import itertools
import json
import os
import re
import sys
import requests
import time
import argparse

parser=argparse.ArgumentParser()

parser.add_argument('--server', required=True, help="The name of your server (e.g. `mstdn.thms.uk`)")
parser.add_argument('--access-token', required=True, help="The access token can be generated at https://<server>/settings/applications, and must have read:search, read:statuses and admin:read:accounts scopes.")
parser.add_argument('--reply-interval-in-hours', required = False, type=int, default=0, help="Only look at posts that have received replies in this period")
parser.add_argument('--home-timeline-length', required = False, type=int, default=0, help="Also look for replies to posts in the API-Key owner's home timeline, up to this many posts")
parser.add_argument('--user', required = False, default='', help="Use together with --max_followings_count or --max_followers_count to tell us which user's followings we should backfill")
parser.add_argument('--max-followings', required = False, type=int, default=0, help="If provided, we'll also backfill posts for new accounts followed by --user. We'll backfill at most this many followings' posts.")
parser.add_argument('--max-followers', required = False, type=int, default=0, help="If provided, we'll also backfill posts for new accounts following --user. We'll backfill at most this many followers' posts.")

def pull_context(
    server,
    access_token,
    seen_urls,
    replied_toot_server_ids,
    reply_interval_hours,
    max_home_timeline_length,
    max_followings,
    backfill_followings_for_user,
    known_followings,
    max_followers
):
    
    parsed_urls = {}

    if reply_interval_hours > 0:
        """pull the context toots of toots user replied to, from their
        original server, and add them to the local server."""
        user_ids = get_active_user_ids(server, access_token, reply_interval_hours)
        reply_toots = get_all_reply_toots(
            server, user_ids, access_token, seen_urls, reply_interval_hours
        )
        known_context_urls = get_all_known_context_urls(server, reply_toots,parsed_urls)
        seen_urls.update(known_context_urls)
        replied_toot_ids = get_all_replied_toot_server_ids(
            server, reply_toots, replied_toot_server_ids, parsed_urls
        )
        context_urls = get_all_context_urls(server, replied_toot_ids)
        add_context_urls(server, access_token, context_urls, seen_urls)


    if max_home_timeline_length > 0:
        """Do the same with any toots on the key owner's home timeline """
        timeline_toots = get_timeline(server, access_token, max_home_timeline_length)
        known_context_urls = get_all_known_context_urls(server, timeline_toots,parsed_urls)
        add_context_urls(server, access_token, known_context_urls, seen_urls)

    if max_followings > 0 and backfill_followings_for_user != '':
        log(f"Getting posts from {backfill_followings_for_user}'s last {max_followings} followings")
        user_id = get_user_id(server, backfill_followings_for_user)
        followings = get_new_followings(server, user_id, max_followings, known_followings)
        add_following_posts(server, access_token, followings, known_followings, seen_urls)
    
    if max_followers > 0 and backfill_followings_for_user != '':
        log(f"Getting posts from {backfill_followings_for_user}'s last {max_followers} followers")
        user_id = get_user_id(server, backfill_followings_for_user)
        followers = get_new_followers(server, user_id, max_followers, known_followings)
        add_following_posts(server, access_token, followers, known_followings, seen_urls)

def add_following_posts(server, access_token, followings, know_followings, seen_urls):
    for user in followings:
        posts = get_user_posts(user, know_followings, server)

        if(posts != None):
            count = 0
            failed = 0
            for post in posts:
                if post['url'] != None and post['url'] not in seen_urls:
                    added = add_context_url(post['url'], server, access_token)
                    if added is True:
                        seen_urls.add(post['url'])
                        count += 1
                    else:
                        failed += 1
            log(f"Added {count} posts for user {user['acct']} with {failed} errors")
            if failed == 0:
                know_followings.add(user['acct'])

def get_user_posts(user, know_followings, server):
    parsed_url = parse_user_url(user['url'])

    if parsed_url == None:
        # We are adding it as 'known' anyway, because we won't be able to fix this.
        know_followings.add(user['acct'])
        return None
    
    if(parsed_url[0] == server):
        log(f"{user['acct']} is a local user. Skip")
        know_followings.add(user['acct'])
        return None
    
    try:
        user_id = get_user_id(parsed_url[0], parsed_url[1])
    except Exception as ex:
        log(f"Error getting user ID for user {user['acct']}: {ex}")
        return None
    
    try:
        url = f"https://{parsed_url[0]}/api/v1/accounts/{user_id}/statuses?limit=40"
        response = get(url)

        if(response.status_code == 200):
            return response.json()
        elif response.status_code == 404:
            raise Exception(
                f"User {user['acct']} was not found on server {parsed_url[0]}"
            )
        else:
            raise Exception(
                f"Error getting URL {url}. Status code: {response.status_code}"
            )
    except Exception as ex:
        log(f"Error getting posts for user {user['acct']}: {ex}")
        return None

def get_new_followers(server, user_id, max, known_followers):
    """Get any new followings for the specified user, up to the max number provided"""
    response = get(f"https://{server}/api/v1/accounts/{user_id}/followers?limit={max}")

    followers = response.json()

    while len(followers) < max and 'next' in response.links:
        response = get(response.links['next']['url'])
        followers = followers + response.json()

    # Remove any we already know about    
    new_followers = list(filter(
        lambda user: user['acct'] not in known_followers,
        followers
    ))
    
    log(f"Got {len(followers)} followers, {len(new_followers)} of which are new")
        
    return new_followers

def get_new_followings(server, user_id, max, known_followings):
    """Get any new followings for the specified user, up to the max number provided"""

    response = get(f"https://{server}/api/v1/accounts/{user_id}/following?limit={max}")
    following = response.json()

    while len(following) < max and 'next' in response.links:
        response = get(response.links['next']['url'])
        following = following + response.json()

    # Remove any we already know about    
    new_followings = list(filter(
        lambda user: user['acct'] not in known_followings,
        following
    ))
    
    log(f"Got {len(following)} followings, {len(new_followings)} of which are new")
        
    return new_followings
    

def get_user_id(server, user):
    """Get the user id from the server, using a username"""
    url = f"https://{server}/api/v1/accounts/lookup?acct={user}"

    
    response = get(url)

    if response.status_code == 200:
        return response.json()['id'] 
    elif response.status_code == 404:
        raise Exception(
            f"User {user} was not found on server {server}."
        )
    else:
        raise Exception(
            f"Error getting URL {url}. Status code: {response.status_code}"
        )


def get_timeline(server, access_token, max):
    """Get all post in the user's home timeline"""

    url = f"https://{server}/api/v1/timelines/home"

    try:
    
        response = get_toots(url, access_token)

        if response.status_code == 200:
            toots = response.json()
        elif response.status_code == 401:
            raise Exception(
                f"Error getting URL {url}. Status code: {response.status_code}. "
                "Ensure your access token is correct"
            )
        elif response.status_code == 403:
            raise Exception(
                f"Error getting URL {url}. Status code: {response.status_code}. "
                "Make sure you have the read:statuses scope enabled for your access token."
            )
        else:
            raise Exception(
                f"Error getting URL {url}. Status code: {response.status_code}"
            )

        # Paginate as needed
        while len(toots) < max and 'next' in response.links:
            response = get_toots(response.links['next']['url'], access_token)
            toots = toots + response.json()
    except Exception as ex:
        log(f"Error getting timeline toots: {ex}")
        sys.exit(1)

    log(f"Found {len(toots)} toots in timeline")

    return toots
    
def get_toots(url, access_token):
    response = get( url, headers={
        "Authorization": f"Bearer {access_token}",
    })

    if response.status_code == 200:
        return response
    elif response.status_code == 401:
        raise Exception(
            f"Error getting URL {url}. Status code: {response.status_code}. "
            "It looks like your access token is incorrect."
        )
    elif response.status_code == 403:
        raise Exception(
            f"Error getting URL {url}. Status code: {response.status_code}. "
            "Make sure you have the read:statuses scope enabled for your access token."
        )
    else:
        raise Exception(
            f"Error getting URL {url}. Status code: {response.status_code}"
        )
    
def get_active_user_ids(server, access_token, reply_interval_hours):
    """get all user IDs on the server that have posted a toot in the given
       time interval"""
    since = datetime.now() - timedelta(days=reply_interval_hours / 24 + 1)
    url = f"https://{server}/api/v1/admin/accounts"
    resp = get(url, headers={
        "Authorization": f"Bearer {access_token}",
    })
    if resp.status_code == 200:
        for user in resp.json():
            last_status_at = user["account"]["last_status_at"]
            if last_status_at is not None:
                last_active = datetime.strptime(last_status_at, "%Y-%m-%d")
                if last_active > since:
                    log(f"Found active user: {user['username']}")
                    yield user["id"]
    elif resp.status_code == 401:
        raise Exception(
            f"Error getting user IDs on server {server}. Status code: {resp.status_code}. "
            "Ensure your access token is correct"
        )
    elif resp.status_code == 403:
        raise Exception(
            f"Error getting user IDs on server {server}. Status code: {resp.status_code}. "
            "Make sure you have the admin:read:accounts scope enabled for your access token."
        )
    else:
        raise Exception(
            f"Error getting user IDs on server {server}. Status code: {resp.status_code}"
        )


def get_all_reply_toots(
    server, user_ids, access_token, seen_urls, reply_interval_hours
):
    """get all replies to other users by the given users in the last day"""
    replies_since = datetime.now() - timedelta(hours=reply_interval_hours)
    reply_toots = list(
        itertools.chain.from_iterable(
            get_reply_toots(
                user_id, server, access_token, seen_urls, replies_since
            )
            for user_id in user_ids
        )
    )
    log(f"Found {len(reply_toots)} reply toots")
    return reply_toots


def get_reply_toots(user_id, server, access_token, seen_urls, reply_since):
    """get replies by the user to other users since the given date"""
    url = f"https://{server}/api/v1/accounts/{user_id}/statuses?exclude_replies=false&limit=40"

    try:
        resp = get(url, headers={
            "Authorization": f"Bearer {access_token}",
        })
    except Exception as ex:
        log(
            f"Error getting replies for user {user_id} on server {server}: {ex}"
        )
        return []

    if resp.status_code == 200:
        toots = [
            toot
            for toot in resp.json()
            if toot["in_reply_to_id"] is not None
            and toot["url"] not in seen_urls
            and datetime.strptime(toot["created_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
            > reply_since
        ]
        for toot in toots:
            log(f"Found reply toot: {toot['url']}")
        return toots
    elif resp.status_code == 403:
        raise Exception(
            f"Error getting replies for user {user_id} on server {server}. Status code: {resp.status_code}. "
            "Make sure you have the read:statuses scope enabled for your access token."
        )

    raise Exception(
        f"Error getting replies for user {user_id} on server {server}. Status code: {resp.status_code}"
    )


def get_all_known_context_urls(server, reply_toots,parsed_urls):
    """get the context toots of the given toots from their original server"""
    known_context_urls = set(
        filter(
            lambda url: not url.startswith(f"https://{server}/"),
            itertools.chain.from_iterable(
                get_toot_context(*parse_url(toot["url"] if toot["reblog"] is None else toot["reblog"]["url"],parsed_urls), toot["url"])
                for toot in filter(
                    lambda toot: toot_has_parseable_url(toot,parsed_urls),
                    reply_toots
                )            
            ),
        )
    )
    log(f"Found {len(known_context_urls)} known context toots")
    return known_context_urls


def toot_has_parseable_url(toot,parsed_urls):
    parsed = parse_url(toot["url"] if toot["reblog"] is None else toot["reblog"]["url"],parsed_urls)
    if(parsed is None) :
        return False
    return True
                

def get_all_replied_toot_server_ids(
    server, reply_toots, replied_toot_server_ids, parsed_urls
):
    """get the server and ID of the toots the given toots replied to"""
    return filter(
        lambda x: x is not None,
        (
            get_replied_toot_server_id(server, toot, replied_toot_server_ids, parsed_urls)
            for toot in reply_toots
        ),
    )


def get_replied_toot_server_id(server, toot, replied_toot_server_ids,parsed_urls):
    """get the server and ID of the toot the given toot replied to"""
    in_reply_to_id = toot["in_reply_to_id"]
    in_reply_to_account_id = toot["in_reply_to_account_id"]
    mentions = [
        mention
        for mention in toot["mentions"]
        if mention["id"] == in_reply_to_account_id
    ]
    if len(mentions) == 0:
        return None

    mention = mentions[0]

    o_url = f"https://{server}/@{mention['acct']}/{in_reply_to_id}"
    if o_url in replied_toot_server_ids:
        return replied_toot_server_ids[o_url]

    url = get_redirect_url(o_url)

    if url is None:
        return None

    match = parse_url(url,parsed_urls)
    if match is not None:
        replied_toot_server_ids[o_url] = (url, match)
        return (url, match)

    log(f"Error parsing toot URL {url}")
    replied_toot_server_ids[o_url] = None
    return None

def parse_user_url(url):
    match = parse_mastodon_profile_url(url)
    if match is not None:
        return match
    
    match = parse_pleroma_profile_url(url)
    if match is not None:
        return match

    log(f"Error parsing Profile URL {url}")
    
    return None

def parse_url(url, parsed_urls):
    if url not in parsed_urls:
        match = parse_mastodon_url(url)
        if match is not None:
            parsed_urls[url] = match
    
    if url not in parsed_urls:
        match = parse_pleroma_url(url)
        if match is not None:
            parsed_urls[url] = match

    if url not in parsed_urls:
        log(f"Error parsing toot URL {url}")
        parsed_urls[url] = None
    
    return parsed_urls[url]

def parse_mastodon_profile_url(url):
    """parse a Mastodon Profile URL and return the server and username"""
    match = re.match(
        r"https://(?P<server>.*)/@(?P<username>.*)", url
    )
    if match is not None:
        return (match.group("server"), match.group("username"))
    return None

def parse_mastodon_url(url):
    """parse a Mastodon URL and return the server and ID"""
    match = re.match(
        r"https://(?P<server>.*)/@(?P<username>.*)/(?P<toot_id>.*)", url
    )
    if match is not None:
        return (match.group("server"), match.group("toot_id"))
    return None


def parse_pleroma_url(url):
    """parse a Pleroma URL and return the server and ID"""
    match = re.match(r"https://(?P<server>.*)/objects/(?P<toot_id>.*)", url)
    if match is not None:
        server = match.group("server")
        url = get_redirect_url(url)
        if url is None:
            return None
        
        match = re.match(r"/notice/(?P<toot_id>.*)", url)
        if match is not None:
            return (server, match.group("toot_id"))
        return None
    return None

def parse_pleroma_profile_url(url):
    """parse a Pleroma Profile URL and return the server and username"""
    match = re.match(r"https://(?P<server>.*)/users/(?P<username>.*)", url)
    if match is not None:
        return (match.group("server"), match.group("username"))
    return None


def get_redirect_url(url):
    """get the URL given URL redirects to"""
    try:
        resp = requests.head(url, allow_redirects=False, timeout=5,headers={
            'User-Agent': 'mastodon_get_replies (https://go.thms.uk/mgr)'
        })
    except Exception as ex:
        log(f"Error getting redirect URL for URL {url}. Exception: {ex}")
        return None

    if resp.status_code == 200:
        return url
    elif resp.status_code == 302:
        redirect_url = resp.headers["Location"]
        log(f"Discovered redirect for URL {url}")
        return redirect_url
    else:
        log(
            f"Error getting redirect URL for URL {url}. Status code: {resp.status_code}"
        )
        return None


def get_all_context_urls(server, replied_toot_ids):
    """get the URLs of the context toots of the given toots"""
    return filter(
        lambda url: not url.startswith(f"https://{server}/"),
        itertools.chain.from_iterable(
            get_toot_context(server, toot_id, url)
            for (url, (server, toot_id)) in replied_toot_ids
        ),
    )


def get_toot_context(server, toot_id, toot_url):
    """get the URLs of the context toots of the given toot"""
    url = f"https://{server}/api/v1/statuses/{toot_id}/context"
    try:
        resp = get(url)
    except Exception as ex:
        log(f"Error getting context for toot {toot_url}. Exception: {ex}")
        return []

    if resp.status_code == 200:
        try:
            res = resp.json()
            log(f"Got context for toot {toot_url}")
            return (toot["url"] for toot in (res["ancestors"] + res["descendants"]))
        except Exception as ex:
            log(f"Error parsing context for toot {toot_url}. Exception: {ex}")
        return []
    elif resp.status_code == 429:
        reset = datetime.strptime(resp.headers['x-ratelimit-reset'], '%Y-%m-%dT%H:%M:%S.%fZ')
        log(f"Rate Limit hit when getting context for {toot_url}. Waiting to retry at {resp.headers['x-ratelimit-reset']}")
        time.sleep((reset - datetime.now()).total_seconds() + 1)
        return get_toot_context(server, toot_id, toot_url)

    log(
        f"Error getting context for toot {toot_url}. Status code: {resp.status_code}"
    )
    return []


def add_context_urls(server, access_token, context_urls, seen_urls):
    """add the given toot URLs to the server"""
    count = 0
    failed = 0
    for url in context_urls:
        if url not in seen_urls:
            added = add_context_url(url, server, access_token)
            if added is True:
                seen_urls.add(url)
                count += 1
            else:
                failed += 1

    log(f"Added {count} new context toots (with {failed} failures)")


def add_context_url(url, server, access_token):
    """add the given toot URL to the server"""
    search_url = f"https://{server}/api/v2/search?q={url}&resolve=true&limit=1"

    try:
        resp = get(search_url, headers={
            "Authorization": f"Bearer {access_token}",
        })
    except Exception as ex:
        log(
            f"Error adding url {search_url} to server {server}. Exception: {ex}"
        )
        return False

    if resp.status_code == 200:
        log(f"Added context url {url}")
        return True
    elif resp.status_code == 403:
        log(
            f"Error adding url {search_url} to server {server}. Status code: {resp.status_code}. "
            "Make sure you have the read:search scope enabled for your access token."
        )
        return False
    elif resp.status_code == 429:
        reset = datetime.strptime(resp.headers['x-ratelimit-reset'], '%Y-%m-%dT%H:%M:%S.%fZ')
        log(f"Rate Limit hit when adding url {search_url}. Waiting to retry at {resp.headers['x-ratelimit-reset']}")
        time.sleep((reset - datetime.now()).total_seconds() + 1)
        return add_context_url(url, server, access_token)
    else:
        log(
            f"Error adding url {search_url} to server {server}. Status code: {resp.status_code}"
        )
        return False
    
def get(url, headers = {}, timeout = 5, max_tries = 5):
    """A simple wrapper to make a get request while providing our user agent, and respecting rate limits"""
    h = headers.copy()
    if 'User-Agent' not in h:
        h['User-Agent'] = 'mastodon_get_replies (https://go.thms.uk/mgr)'
        
    response = requests.get( url, headers= h, timeout=timeout)
    if response.status_code == 429:
        if max_tries > 0:
            reset = parser.parse(response.headers['x-ratelimit-reset'])
            now = datetime.now(datetime.now().astimezone().tzinfo)
            wait = (reset - now).total_seconds() + 1
            log(f"Rate Limit hit requesting {url}. Waiting {wait} sec to retry at {response.headers['x-ratelimit-reset']}")
            time.sleep(wait)
            return get(url, headers, timeout, max_tries - 1)
        
        raise Exception(f"Maximum number of retries exceeded for rate limited request {url}")
    return response

def log(text):
    print(f"{datetime.now()} {datetime.now().astimezone().tzinfo}: {text}")

class OrderedSet:
    """An ordered set implementation over a dict"""

    def __init__(self, iterable):
        self._dict = {}
        for item in iterable:
            self.add(item)

    def add(self, item):
        if item not in self._dict:
            self._dict[item] = None

    def update(self, iterable):
        for item in iterable:
            self.add(item)

    def __contains__(self, item):
        return item in self._dict

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)


if __name__ == "__main__":

    SEEN_URLS_FILE = "artifacts/seen_urls"
    REPLIED_TOOT_SERVER_IDS_FILE = "artifacts/replied_toot_server_ids"
    KNOWN_FOLLOWINGS_FILE = "artifacts/known_followings"


    SEEN_URLS = OrderedSet([])
    if os.path.exists(SEEN_URLS_FILE):
        with open(SEEN_URLS_FILE, "r", encoding="utf-8") as f:
            SEEN_URLS = OrderedSet(f.read().splitlines())

    REPLIED_TOOT_SERVER_IDS = {}
    if os.path.exists(REPLIED_TOOT_SERVER_IDS_FILE):
        with open(REPLIED_TOOT_SERVER_IDS_FILE, "r", encoding="utf-8") as f:
            REPLIED_TOOT_SERVER_IDS = json.load(f)

    KNOWN_FOLLOWINGS = OrderedSet([])
    if os.path.exists(KNOWN_FOLLOWINGS_FILE):
        with open(KNOWN_FOLLOWINGS_FILE, "r", encoding="utf-8") as f:
            KNOWN_FOLLOWINGS = OrderedSet(f.read().splitlines())

    arguments = parser.parse_args()

    pull_context(
        arguments.server,
        arguments.access_token,
        SEEN_URLS,
        REPLIED_TOOT_SERVER_IDS,
        arguments.reply_interval_in_hours,
        arguments.home_timeline_length,
        arguments.max_followings,
        arguments.user,
        KNOWN_FOLLOWINGS,
        arguments.max_followers,
    )

    with open(KNOWN_FOLLOWINGS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(list(KNOWN_FOLLOWINGS)[-10000:]))

    with open(SEEN_URLS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(list(SEEN_URLS)[-10000:]))

    with open(REPLIED_TOOT_SERVER_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump(dict(list(REPLIED_TOOT_SERVER_IDS.items())[-10000:]), f)
