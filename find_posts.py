#!/usr/bin/env python3

from datetime import datetime, timedelta
import string
from dateutil import parser
import itertools
import json
import os
import re
import sys
import requests
import time
import argparse
import uuid
import git

argparser=argparse.ArgumentParser()

argparser.add_argument('-c','--config', required=False, type=str, help='Optionally provide a path to a JSON file containing configuration options. If not provided, options must be supplied using command line flags.')
argparser.add_argument('--server', required=False, help="Required: The name of your server (e.g. `mstdn.thms.uk`)")
argparser.add_argument('--access-token', action="append", required=False, help="Required: The access token can be generated at https://<server>/settings/applications, and must have read:search, read:statuses and admin:read:accounts scopes. You can supply this multiple times, if you want tun run it for multiple users.")
argparser.add_argument('--reply-interval-in-hours', required = False, type=int, default=0, help="Fetch remote replies to posts that have received replies from users on your own instance in this period")
argparser.add_argument('--home-timeline-length', required = False, type=int, default=0, help="Look for replies to posts in the API-Key owner's home timeline, up to this many posts")
argparser.add_argument('--user', required = False, default='', help="Use together with --max-followings or --max-followers to tell us which user's followings/followers we should backfill")
argparser.add_argument('--max-followings', required = False, type=int, default=0, help="Backfill posts for new accounts followed by --user. We'll backfill at most this many followings' posts")
argparser.add_argument('--max-followers', required = False, type=int, default=0, help="Backfill posts for new accounts following --user. We'll backfill at most this many followers' posts")
argparser.add_argument('--max-follow-requests', required = False, type=int, default=0, help="Backfill posts of the API key owners pending follow requests. We'll backfill at most this many requester's posts")
argparser.add_argument('--max-bookmarks', required = False, type=int, default=0, help="Fetch remote replies to the API key owners Bookmarks. We'll fetch replies to at most this many bookmarks")
argparser.add_argument('--max-favourites', required = False, type=int, default=0, help="Fetch remote replies to the API key owners Favourites. We'll fetch replies to at most this many favourites")
argparser.add_argument('--from-notifications', required = False, type=int, default=0, help="Backfill accounts of anyone appearing in your notifications, during the last hours")
argparser.add_argument('--remember-users-for-hours', required=False, type=int, default=24*7, help="How long to remember users that you aren't following for, before trying to backfill them again.")
argparser.add_argument('--http-timeout', required = False, type=int, default=5, help="The timeout for any HTTP requests to your own, or other instances.")
argparser.add_argument('--backfill-with-context', required = False, type=int, default=1, help="If enabled, we'll fetch remote replies when backfilling profiles. Set to `0` to disable.")
argparser.add_argument('--backfill-mentioned-users', required = False, type=int, default=1, help="If enabled, we'll backfill any mentioned users when fetching remote replies to timeline posts. Set to `0` to disable.")
argparser.add_argument('--lock-hours', required = False, type=int, default=24, help="The lock timeout in hours.")
argparser.add_argument('--lock-file', required = False, default=None, help="Location of the lock file")
argparser.add_argument('--state-dir', required = False, default="artifacts", help="Directory to store persistent files and possibly lock file")
argparser.add_argument('--on-done', required = False, default=None, help="Provide a url that will be pinged when processing has completed. You can use this for 'dead man switch' monitoring of your task")
argparser.add_argument('--on-start', required = False, default=None, help="Provide a url that will be pinged when processing is starting. You can use this for 'dead man switch' monitoring of your task")
argparser.add_argument('--on-fail', required = False, default=None, help="Provide a url that will be pinged when processing has failed. You can use this for 'dead man switch' monitoring of your task")

def get_notification_users(server, access_token, known_users, max_age):
    since = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(hours=max_age)
    notifications = get_paginated_mastodon(f"https://{server}/api/v1/notifications", since, headers={
        "Authorization": f"Bearer {access_token}",
    })
    notification_users = []
    for notification in notifications:
        notificationDate = parser.parse(notification['created_at'])
        if(notificationDate >= since and notification['account'] not in notification_users):
            notification_users.append(notification['account'])

    new_notification_users = filter_known_users(notification_users, known_users)

    log(f"Found {len(notification_users)} users in notifications, {len(new_notification_users)} of which are new")

    return new_notification_users

def get_bookmarks(server, access_token, max):
    return get_paginated_mastodon(f"https://{server}/api/v1/bookmarks", max, {
        "Authorization": f"Bearer {access_token}",
    })

def get_favourites(server, access_token, max):
    return get_paginated_mastodon(f"https://{server}/api/v1/favourites", max, {
        "Authorization": f"Bearer {access_token}",
    })

def add_user_posts(server, access_token, followings, know_followings, all_known_users, seen_urls):
    for user in followings:
        if user['acct'] not in all_known_users and not user['url'].startswith(f"https://{server}/"):
            posts = get_user_posts(user, know_followings, server)

            if(posts != None):
                count = 0
                failed = 0
                for post in posts:
                    if post.get('reblog') is None and post.get('url') is not None and post.get('url') not in seen_urls:
                        added = add_post_with_context(post, server, access_token, seen_urls)
                        if added is True:
                            seen_urls.add(post['url'])
                            count += 1
                        else:
                            failed += 1
                log(f"Added {count} posts for user {user['acct']} with {failed} errors")
                if failed == 0:
                    know_followings.add(user['acct'])
                    all_known_users.add(user['acct'])

def add_post_with_context(post, server, access_token, seen_urls):
    added = add_context_url(post['url'], server, access_token)
    if added is True:
        seen_urls.add(post['url'])
        if ('replies_count' in post or 'in_reply_to_id' in post) and getattr(arguments, 'backfill_with_context', 0) > 0:
            parsed_urls = {}
            parsed = parse_url(post['url'], parsed_urls)
            if parsed == None:
                return True
            known_context_urls = get_all_known_context_urls(server, [post],parsed_urls)
            add_context_urls(server, access_token, known_context_urls, seen_urls)
        return True
    
    return False

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
    if re.match(r"^https:\/\/[^\/]+\/c\/", user['url']):
        try:
            url = f"https://{parsed_url[0]}/api/v3/post/list?community_name={parsed_url[1]}&sort=New&limit=50"
            response = get(url)

            if(response.status_code == 200):
                posts = [post['post'] for post in response.json()['posts']]
                for post in posts:
                    post['url'] = post['ap_id']
                return posts

        except Exception as ex:
            log(f"Error getting community posts for community {parsed_url[1]}: {ex}")
        return None
    
    if re.match(r"^https:\/\/[^\/]+\/u\/", user['url']):
        try:
            url = f"https://{parsed_url[0]}/api/v3/user?username={parsed_url[1]}&sort=New&limit=50"
            response = get(url)

            if(response.status_code == 200):
                comments = [post['post'] for post in response.json()['comments']]
                posts = [post['post'] for post in response.json()['posts']]
                all_posts = comments + posts
                for post in all_posts:
                    post['url'] = post['ap_id']
                return all_posts
            
        except Exception as ex:
            log(f"Error getting user posts for user {parsed_url[1]}: {ex}")
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
    
def get_new_follow_requests(server, access_token, max, known_followings):
    """Get any new follow requests for the specified user, up to the max number provided"""

    follow_requests = get_paginated_mastodon(f"https://{server}/api/v1/follow_requests", max, {
        "Authorization": f"Bearer {access_token}",
    })

    # Remove any we already know about    
    new_follow_requests = filter_known_users(follow_requests, known_followings)
    
    log(f"Got {len(follow_requests)} follow_requests, {len(new_follow_requests)} of which are new")
        
    return new_follow_requests

def filter_known_users(users, known_users):
    return list(filter(
        lambda user: user['acct'] not in known_users,
        users
    ))

def get_new_followers(server, user_id, max, known_followers):
    """Get any new followings for the specified user, up to the max number provided"""
    followers = get_paginated_mastodon(f"https://{server}/api/v1/accounts/{user_id}/followers", max)

    # Remove any we already know about    
    new_followers = filter_known_users(followers, known_followers)
    
    log(f"Got {len(followers)} followers, {len(new_followers)} of which are new")
        
    return new_followers

def get_new_followings(server, user_id, max, known_followings):
    """Get any new followings for the specified user, up to the max number provided"""
    following = get_paginated_mastodon(f"https://{server}/api/v1/accounts/{user_id}/following", max)

    # Remove any we already know about    
    new_followings = filter_known_users(following, known_followings)
    
    log(f"Got {len(following)} followings, {len(new_followings)} of which are new")
        
    return new_followings
    

def get_user_id(server, user = None, access_token = None):
    """Get the user id from the server, using a username"""

    headers = {}

    if user != None and user != '':
        url = f"https://{server}/api/v1/accounts/lookup?acct={user}"
    elif access_token != None:
        url = f"https://{server}/api/v1/accounts/verify_credentials"
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
    else:
        raise Exception('You must supply either a user name or an access token, to get an user ID')
    
    response = get(url, headers=headers)

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
        raise

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


def get_all_known_context_urls(server, reply_toots, parsed_urls):
    """get the context toots of the given toots from their original server"""
    known_context_urls = set()
    
    for toot in reply_toots:
        if toot_has_parseable_url(toot, parsed_urls):
            url = toot["url"] if toot["reblog"] is None else toot["reblog"]["url"]
            parsed_url = parse_url(url, parsed_urls)
            context = get_toot_context(parsed_url[0], parsed_url[1], url)
            if context is not None:
                for item in context:
                    known_context_urls.add(item)
            else:
                log(f"Error getting context for toot {url}")
    
    known_context_urls = set(filter(lambda url: not url.startswith(f"https://{server}/"), known_context_urls))
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

    match = parse_lemmy_profile_url(url)
    if match is not None:
        return match

# Pixelfed profile paths do not use a subdirectory, so we need to match for them last.
    match = parse_pixelfed_profile_url(url)
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
        match = parse_lemmy_url(url)
        if match is not None:
            parsed_urls[url] = match

    if url not in parsed_urls:
        match = parse_pixelfed_url(url)
        if match is not None:
            parsed_urls[url] = match

    if url not in parsed_urls:
        log(f"Error parsing toot URL {url}")
        parsed_urls[url] = None
    
    return parsed_urls[url]

def parse_mastodon_profile_url(url):
    """parse a Mastodon Profile URL and return the server and username"""
    match = re.match(
        r"https://(?P<server>[^/]+)/@(?P<username>[^/]+)", url
    )
    if match is not None:
        return (match.group("server"), match.group("username"))
    return None

def parse_mastodon_url(url):
    """parse a Mastodon URL and return the server and ID"""
    match = re.match(
        r"https://(?P<server>[^/]+)/@(?P<username>[^/]+)/(?P<toot_id>[^/]+)", url
    )
    if match is not None:
        return (match.group("server"), match.group("toot_id"))
    return None


def parse_pleroma_url(url):
    """parse a Pleroma URL and return the server and ID"""
    match = re.match(r"https://(?P<server>[^/]+)/objects/(?P<toot_id>[^/]+)", url)
    if match is not None:
        server = match.group("server")
        url = get_redirect_url(url)
        if url is None:
            return None
        
        match = re.match(r"/notice/(?P<toot_id>[^/]+)", url)
        if match is not None:
            return (server, match.group("toot_id"))
        return None
    return None

def parse_pleroma_profile_url(url):
    """parse a Pleroma Profile URL and return the server and username"""
    match = re.match(r"https://(?P<server>[^/]+)/users/(?P<username>[^/]+)", url)
    if match is not None:
        return (match.group("server"), match.group("username"))
    return None

def parse_pixelfed_url(url):
    """parse a Pixelfed URL and return the server and ID"""
    match = re.match(
        r"https://(?P<server>[^/]+)/p/(?P<username>[^/]+)/(?P<toot_id>[^/]+)", url
    )
    if match is not None:
        return (match.group("server"), match.group("toot_id"))
    return None

def parse_pixelfed_profile_url(url):
    """parse a Pixelfed Profile URL and return the server and username"""
    match = re.match(r"https://(?P<server>[^/]+)/(?P<username>[^/]+)", url)
    if match is not None:
        return (match.group("server"), match.group("username"))
    return None

def parse_lemmy_url(url):
    """parse a Lemmy URL and return the server, and ID"""
    match = re.match(
        r"https://(?P<server>[^/]+)/(?:comment|post)/(?P<toot_id>[^/]+)", url
    )
    if match is not None:
        return (match.group("server"), match.group("toot_id"))
    return None

def parse_lemmy_profile_url(url):
    """parse a Lemmy Profile URL and return the server and username"""
    match = re.match(r"https://(?P<server>[^/]+)/(?:u|c)/(?P<username>[^/]+)", url)
    if match is not None:
        return (match.group("server"), match.group("username"))
    return None

def get_redirect_url(url):
    """get the URL given URL redirects to"""
    try:
        resp = requests.head(url, allow_redirects=False, timeout=5,headers={
            'User-Agent': 'FediFetcher (https://go.thms.uk/mgr)'
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
    if toot_url.find("/comment/") != -1:
        return get_comment_context(server, toot_id, toot_url)
    if toot_url.find("/post/") != -1:
        return get_comments_urls(server, toot_id, toot_url)
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

def get_comment_context(server, toot_id, toot_url):
    """get the URLs of the context toots of the given toot"""
    comment = f"https://{server}/api/v3/comment?id={toot_id}"
    try:
        resp = get(comment)
    except Exception as ex:
        log(f"Error getting comment {toot_id} from {toot_url}. Exception: {ex}")
        return []
    
    if resp.status_code == 200:
        try:
            res = resp.json()
            post_id = res['comment_view']['comment']['post_id']
            return get_comments_urls(server, post_id, toot_url)
        except Exception as ex:
            log(f"Error parsing context for comment {toot_url}. Exception: {ex}")
        return []
    elif resp.status_code == 429:
        reset = datetime.strptime(resp.headers['x-ratelimit-reset'], '%Y-%m-%dT%H:%M:%S.%fZ')
        log(f"Rate Limit hit when getting context for {toot_url}. Waiting to retry at {resp.headers['x-ratelimit-reset']}")
        time.sleep((reset - datetime.now()).total_seconds() + 1)
        return get_comment_context(server, toot_id, toot_url)

def get_comments_urls(server, post_id, toot_url):
    """get the URLs of the comments of the given post"""
    urls = []
    url = f"https://{server}/api/v3/post?id={post_id}"
    try:
        resp = get(url)
    except Exception as ex:
        log(f"Error getting post {post_id} from {toot_url}. Exception: {ex}")
        return []

    if resp.status_code == 200:
        try:
            res = resp.json()
            if res['post_view']['counts']['comments'] == 0:
                return []
            urls.append(res['post_view']['post']['ap_id'])
        except Exception as ex:
            log(f"Error parsing post {post_id} from {toot_url}. Exception: {ex}")

    url = f"https://{server}/api/v3/comment/list?post_id={post_id}&sort=New&limit=50"
    try:
        resp = get(url)
    except Exception as ex:
        log(f"Error getting comments for post {post_id} from {toot_url}. Exception: {ex}")
        return []

    if resp.status_code == 200:
        try:
            res = resp.json()
            list_of_urls = [comment_info['comment']['ap_id'] for comment_info in res['comments']]
            log(f"Got {len(list_of_urls)} comments for post {toot_url}")
            urls.extend(list_of_urls)
            return urls
        except Exception as ex:
            log(f"Error parsing comments for post {toot_url}. Exception: {ex}")
    elif resp.status_code == 429:
        reset = datetime.strptime(resp.headers['x-ratelimit-reset'], '%Y-%m-%dT%H:%M:%S.%fZ')
        log(f"Rate Limit hit when getting comments for {toot_url}. Waiting to retry at {resp.headers['x-ratelimit-reset']}")
        time.sleep((reset - datetime.now()).total_seconds() + 1)
        return get_comments_urls(server, post_id, toot_url)

    log(f"Error getting comments for post {toot_url}. Status code: {resp.status_code}")
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
    
def get_paginated_mastodon(url, max, headers = {}, timeout = 0, max_tries = 5):
    """Make a paginated request to mastodon"""
    if(isinstance(max, int)):
        furl = f"{url}?limit={max}"
    else:
        furl = url

    response = get(furl, headers, timeout, max_tries)

    if response.status_code != 200:
        if response.status_code == 401:
            raise Exception(
                f"Error getting URL {url}. Status code: {response.status_code}. "
                "Ensure your access token is correct"
            )
        elif response.status_code == 403:
            raise Exception(
                f"Error getting URL {url}. Status code: {response.status_code}. "
                "Make sure you have the correct scopes enabled for your access token."
            )
        else:
            raise Exception(
                f"Error getting URL {url}. Status code: {response.status_code}"
            )

    result = response.json()

    if(isinstance(max, int)):
        while len(result) < max and 'next' in response.links:
            response = get(response.links['next']['url'], headers, timeout, max_tries)
            if response.status_code != 200:
                raise Exception(
                    f"Error getting URL {response.url}. \
                        Status code: {response.status_code}"
                )
            response_json = response.json()
            if isinstance(response_json, list):
                result += response_json
            else:
                break
    else:
        while result and parser.parse(result[-1]['created_at']) >= max \
            and 'next' in response.links:
            response = get(response.links['next']['url'], headers, timeout, max_tries)
            if response.status_code != 200:
                raise Exception(
                    f"Error getting URL {response.url}. \
                        Status code: {response.status_code}"
                )
            response_json = response.json()
            if isinstance(response_json, list):
                result += response_json
            else:
                break
    return result


def get(url, headers = {}, timeout = 0, max_tries = 5):
    """A simple wrapper to make a get request while providing our user agent, and respecting rate limits"""
    h = headers.copy()
    if 'User-Agent' not in h:
        h['User-Agent'] = 'FediFetcher (https://go.thms.uk/mgr)'

    if timeout == 0:
        timeout = arguments.http_timeout
        
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
        if isinstance(iterable, dict):
            for item in iterable:
                if isinstance(iterable[item], str):
                    self.add(item, parser.parse(iterable[item]))
                else:
                    self.add(item, iterable[item])
        else:
            for item in iterable:
                self.add(item)

    def add(self, item, time = None):
        if item not in self._dict:
            if(time == None):
                self._dict[item] = datetime.now(datetime.now().astimezone().tzinfo)
            else:
                self._dict[item] = time

    def pop(self, item):
        self._dict.pop(item)
    
    def get(self, item):
        return self._dict[item]

    def update(self, iterable):
        for item in iterable:
            self.add(item)

    def __contains__(self, item):
        return item in self._dict

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)
    
    def toJSON(self):
        return json.dump(self._dict, f, default=str)


if __name__ == "__main__":
    start = datetime.now()

    repo = git.Repo(os.getcwd())

    tag = next((tag for tag in repo.tags if tag.commit == repo.head.commit), None)

    if(isinstance(tag, git.TagReference)) :
        version = tag.name
    else:
        version = f"on commit {repo.head.commit.name_rev}"

    log(f"Starting FediFetcher {version}")

    arguments = argparser.parse_args()

    if(arguments.config != None):
        if os.path.exists(arguments.config):
            with open(arguments.config, "r", encoding="utf-8") as f:
                config = json.load(f)

            for key in config:
                setattr(arguments, key.lower().replace('-','_'), config[key])

        else:
            log(f"Config file {arguments.config} doesn't exist")
            sys.exit(1)

    if(arguments.server == None or arguments.access_token == None):
        log("You must supply at least a server name and an access token")
        sys.exit(1)

    # in case someone provided the server name as url instead, 
    setattr(arguments, 'server', re.sub(r"^(https://)?([^/]*)/?$", "\\2", arguments.server))
        

    runId = uuid.uuid4()

    if(arguments.on_start != None and arguments.on_start != ''):
        try:
            get(f"{arguments.on_start}?rid={runId}")
        except Exception as ex:
            log(f"Error getting callback url: {ex}")

    if arguments.lock_file is None:
        arguments.lock_file = os.path.join(arguments.state_dir, 'lock.lock')
    LOCK_FILE = arguments.lock_file

    if( os.path.exists(LOCK_FILE)):
        log(f"Lock file exists at {LOCK_FILE}")

        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                lock_time = parser.parse(f.read())

            if (datetime.now() - lock_time).total_seconds() >= arguments.lock_hours * 60 * 60: 
                os.remove(LOCK_FILE)
                log(f"Lock file has expired. Removed lock file.")
            else:
                log(f"Lock file age is {datetime.now() - lock_time} - below --lock-hours={arguments.lock_hours} provided.")
                if(arguments.on_fail != None and arguments.on_fail != ''):
                    try:
                        get(f"{arguments.on_fail}?rid={runId}")
                    except Exception as ex:
                        log(f"Error getting callback url: {ex}")
                sys.exit(1)

        except Exception:
            log(f"Cannot read logfile age - aborting.")
            if(arguments.on_fail != None and arguments.on_fail != ''):
                try:
                    get(f"{arguments.on_fail}?rid={runId}")
                except Exception as ex:
                    log(f"Error getting callback url: {ex}")
            sys.exit(1)

    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(f"{datetime.now()}")

    try:

        SEEN_URLS_FILE = os.path.join(arguments.state_dir, "seen_urls")
        REPLIED_TOOT_SERVER_IDS_FILE = os.path.join(arguments.state_dir, "replied_toot_server_ids")
        KNOWN_FOLLOWINGS_FILE = os.path.join(arguments.state_dir, "known_followings")
        RECENTLY_CHECKED_USERS_FILE = os.path.join(arguments.state_dir, "recently_checked_users")


        seen_urls = OrderedSet([])
        if os.path.exists(SEEN_URLS_FILE):
            with open(SEEN_URLS_FILE, "r", encoding="utf-8") as f:
                seen_urls = OrderedSet(f.read().splitlines())

        replied_toot_server_ids = {}
        if os.path.exists(REPLIED_TOOT_SERVER_IDS_FILE):
            with open(REPLIED_TOOT_SERVER_IDS_FILE, "r", encoding="utf-8") as f:
                replied_toot_server_ids = json.load(f)

        known_followings = OrderedSet([])
        if os.path.exists(KNOWN_FOLLOWINGS_FILE):
            with open(KNOWN_FOLLOWINGS_FILE, "r", encoding="utf-8") as f:
                known_followings = OrderedSet(f.read().splitlines())

        recently_checked_users = OrderedSet({})
        if os.path.exists(RECENTLY_CHECKED_USERS_FILE):
            with open(RECENTLY_CHECKED_USERS_FILE, "r", encoding="utf-8") as f:
                recently_checked_users = OrderedSet(json.load(f))

        # Remove any users whose last check is too long in the past from the list
        for user in list(recently_checked_users):
            lastCheck = recently_checked_users.get(user)
            userAge = datetime.now(lastCheck.tzinfo) - lastCheck
            if(userAge.total_seconds() > arguments.remember_users_for_hours * 60 * 60):
                recently_checked_users.pop(user)    

        parsed_urls = {}

        all_known_users = OrderedSet(list(known_followings) + list(recently_checked_users))

        if(isinstance(arguments.access_token, str)):
            setattr(arguments, 'access_token', [arguments.access_token])

        for token in arguments.access_token:

            if arguments.reply_interval_in_hours > 0:
                """pull the context toots of toots user replied to, from their
                original server, and add them to the local server."""
                user_ids = get_active_user_ids(arguments.server, token, arguments.reply_interval_in_hours)
                reply_toots = get_all_reply_toots(
                    arguments.server, user_ids, token, seen_urls, arguments.reply_interval_in_hours
                )
                known_context_urls = get_all_known_context_urls(arguments.server, reply_toots,parsed_urls)
                seen_urls.update(known_context_urls)
                replied_toot_ids = get_all_replied_toot_server_ids(
                    arguments.server, reply_toots, replied_toot_server_ids, parsed_urls
                )
                context_urls = get_all_context_urls(arguments.server, replied_toot_ids)
                add_context_urls(arguments.server, token, context_urls, seen_urls)


            if arguments.home_timeline_length > 0:
                """Do the same with any toots on the key owner's home timeline """
                timeline_toots = get_timeline(arguments.server, token, arguments.home_timeline_length)
                known_context_urls = get_all_known_context_urls(arguments.server, timeline_toots,parsed_urls)
                add_context_urls(arguments.server, token, known_context_urls, seen_urls)

                # Backfill any post authors, and any mentioned users
                if arguments.backfill_mentioned_users > 0:
                    mentioned_users = []
                    cut_off = datetime.now(datetime.now().astimezone().tzinfo) - timedelta(minutes=60)
                    for toot in timeline_toots:
                        these_users = []
                        toot_created_at = parser.parse(toot['created_at'])
                        if len(mentioned_users) < 10 or (toot_created_at > cut_off and len(mentioned_users) < 30):
                            these_users.append(toot['account'])
                            if(len(toot['mentions'])):
                                these_users += toot['mentions']
                            if(toot['reblog'] != None):
                                these_users.append(toot['reblog']['account'])
                                if(len(toot['reblog']['mentions'])):
                                    these_users += toot['reblog']['mentions']
                        for user in these_users:
                            if user not in mentioned_users and user['acct'] not in all_known_users:
                                mentioned_users.append(user)

                    add_user_posts(arguments.server, token, filter_known_users(mentioned_users, all_known_users), recently_checked_users, all_known_users, seen_urls)

            if arguments.max_followings > 0:
                log(f"Getting posts from last {arguments.max_followings} followings")
                user_id = get_user_id(arguments.server, arguments.user, token)
                followings = get_new_followings(arguments.server, user_id, arguments.max_followings, all_known_users)
                add_user_posts(arguments.server, token, followings, known_followings, all_known_users, seen_urls)
            
            if arguments.max_followers > 0:
                log(f"Getting posts from last {arguments.max_followers} followers")
                user_id = get_user_id(arguments.server, arguments.user, token)
                followers = get_new_followers(arguments.server, user_id, arguments.max_followers, all_known_users)
                add_user_posts(arguments.server, token, followers, recently_checked_users, all_known_users, seen_urls)

            if arguments.max_follow_requests > 0:
                log(f"Getting posts from last {arguments.max_follow_requests} follow requests")
                follow_requests = get_new_follow_requests(arguments.server, token, arguments.max_follow_requests, all_known_users)
                add_user_posts(arguments.server, token, follow_requests, recently_checked_users, all_known_users, seen_urls)

            if arguments.from_notifications > 0:
                log(f"Getting notifications for last {arguments.from_notifications} hours")
                notification_users = get_notification_users(arguments.server, token, all_known_users, arguments.from_notifications)
                add_user_posts(arguments.server, token, notification_users, recently_checked_users, all_known_users, seen_urls)

            if arguments.max_bookmarks > 0:
                log(f"Pulling replies to the last {arguments.max_bookmarks} bookmarks")
                bookmarks = get_bookmarks(arguments.server, token, arguments.max_bookmarks)
                known_context_urls = get_all_known_context_urls(arguments.server, bookmarks,parsed_urls)
                add_context_urls(arguments.server, token, known_context_urls, seen_urls)

            if arguments.max_favourites > 0:
                log(f"Pulling replies to the last {arguments.max_favourites} favourites")
                favourites = get_favourites(arguments.server, token, arguments.max_favourites)
                known_context_urls = get_all_known_context_urls(arguments.server, favourites,parsed_urls)
                add_context_urls(arguments.server, token, known_context_urls, seen_urls)

        with open(KNOWN_FOLLOWINGS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(list(known_followings)[-10000:]))

        with open(SEEN_URLS_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(list(seen_urls)[-10000:]))

        with open(REPLIED_TOOT_SERVER_IDS_FILE, "w", encoding="utf-8") as f:
            json.dump(dict(list(replied_toot_server_ids.items())[-10000:]), f)

        with open(RECENTLY_CHECKED_USERS_FILE, "w", encoding="utf-8") as f:
            recently_checked_users.toJSON()

        os.remove(LOCK_FILE)

        if(arguments.on_done != None and arguments.on_done != ''):
            try:
                get(f"{arguments.on_done}?rid={runId}")
            except Exception as ex:
                log(f"Error getting callback url: {ex}")

        log(f"Processing finished in {datetime.now() - start}.")

    except Exception as ex:
        os.remove(LOCK_FILE)
        log(f"Job failed after {datetime.now() - start}.")
        if(arguments.on_fail != None and arguments.on_fail != ''):
            try:
                get(f"{arguments.on_fail}?rid={runId}")
            except Exception as ex:
                log(f"Error getting callback url: {ex}")
        raise