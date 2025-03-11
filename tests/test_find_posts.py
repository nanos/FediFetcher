import json
import re
from datetime import datetime

import find_posts
import pytest
import requests
from urllib import parse
from requests.models import Response
from unittest.mock import MagicMock, Mock, patch

from find_posts import (
    add_context_urls,
    add_user_posts,
    filter_known_users,
    get,
    get_bookmarks,
    get_favourites,
    get_lemmy_comment_context,
    get_lemmy_urls,
    get_list_timeline,
    get_list_users,
    get_misskey_urls,
    get_new_follow_requests,
    get_new_followings,
    get_peertube_urls,
    get_toot_context,
    get_user_id,
    get_user_posts_mastodon,
    get_user_posts_misskey,
    parse_lemmy_profile_url,
    parse_lemmy_url,
    parse_mastodon_profile_url,
    parse_mastodon_uri,
    parse_mastodon_url,
    parse_misskey_url,
    parse_peertube_profile_url,
    parse_peertube_url,
    parse_pixelfed_profile_url,
    parse_pixelfed_url,
    parse_pleroma_url,
    parse_pleroma_uri,
    post,
    set_server_apis,
    user_has_opted_out,
    parse_url
)



@patch("find_posts.get_paginated_mastodon")
def test_get_bookmarks(mock_get_paginated_mastodon):
    server = "test_server"
    access_token = "test_token"
    max = 5

    get_bookmarks(server, access_token, max)

    mock_get_paginated_mastodon.assert_called_once_with(
        f"https://{server}/api/v1/bookmarks",
        max,
        {
            "Authorization": f"Bearer {access_token}",
        },
    )


@pytest.mark.parametrize(
    "server,access_token,max",
    [
        ("test_server1", "test_token1", 2),
        ("test_server2", "test_token2", 10),
    ],
)
def test_get_bookmarks_parameterized(server, access_token, max):
    with patch("find_posts.get_paginated_mastodon") as mock_get_paginated_mastodon:
        get_bookmarks(server, access_token, max)
        mock_get_paginated_mastodon.assert_called_once_with(
            f"https://{server}/api/v1/bookmarks",
            max,
            {
                "Authorization": f"Bearer {access_token}",
            },
        )


@patch("find_posts.get_paginated_mastodon")
def test_get_favourites(mock_get_paginated_mastodon):
    server = "some.server"
    access_token = "token123"
    max = 5
    expected_result = "result"

    mock_get_paginated_mastodon.return_value = expected_result

    result = get_favourites(server, access_token, max)

    mock_get_paginated_mastodon.assert_called_once_with(
        f"https://{server}/api/v1/favourites",
        max,
        {
            "Authorization": f"Bearer {access_token}",
        },
    )
    assert result == expected_result


@patch("find_posts.get_user_posts")
@patch("find_posts.add_post_with_context")
@patch("find_posts.logger")
def test_add_user_posts(mock_logger, mock_add_post, mock_get_posts):
    server = "test_server"
    access_token = "test_token"
    followings = [
        {"acct": "user1", "url": "https://user1.com"},
        {"acct": "user2", "url": "https://test_server/user2"},
    ]
    known_followings = set()
    all_known_users = set()
    seen_urls = set()
    seen_hosts = set()

    mock_get_posts.return_value = [
        {"url": "https://user1.com/post1"},
        {"url": "https://user1.com/post2"},
    ]
    mock_add_post.return_value = True

    add_user_posts(
        server,
        access_token,
        followings,
        known_followings,
        all_known_users,
        seen_urls,
        seen_hosts,
    )

    mock_get_posts.assert_called_once_with(
        followings[0], known_followings, server, seen_hosts
    )
    assert mock_add_post.call_count == 2
    assert len(seen_urls) == 2
    assert "user1" in known_followings
    assert "user1" in all_known_users
    mock_logger.info.assert_called_with("Added 2 posts for user user1 with 0 errors")


@patch("find_posts.get_user_posts")
@patch("find_posts.add_post_with_context")
@patch("find_posts.logger")
def test_add_user_posts_with_no_new_posts(mock_logger, mock_add_post, mock_get_posts):
    server = "test_server"
    access_token = "test_token"
    followings = [{"acct": "user1", "url": "https://user1.com"}]
    known_followings = set()
    all_known_users = set()
    seen_urls = {"https://user1.com/post1", "https://user1.com/post2"}
    seen_hosts = set()

    mock_get_posts.return_value = [
        {"url": "https://user1.com/post1"},
        {"url": "https://user1.com/post2"},
    ]
    mock_add_post.return_value = True

    add_user_posts(
        server,
        access_token,
        followings,
        known_followings,
        all_known_users,
        seen_urls,
        seen_hosts,
    )

    mock_get_posts.assert_called_once_with(
        followings[0], known_followings, server, seen_hosts
    )
    mock_add_post.assert_not_called()
    assert len(seen_urls) == 2
    assert "user1" in known_followings
    assert "user1" in all_known_users


@pytest.fixture
def mock_functions():
    with patch(
        "find_posts.add_context_url", return_value=True
    ) as add_context_url, patch(
        "find_posts.parse_url", return_value=None
    ) as parse_url, patch(
        "find_posts.get_all_known_context_urls", return_value=[]
    ) as get_all_known_context_urls, patch(
        "find_posts.add_context_urls"
    ) as add_context_urls:
        yield add_context_url, parse_url, get_all_known_context_urls, add_context_urls


def test_add_post_with_context_post_not_added(mock_functions):
    add_context_url, _, _, _ = mock_functions
    add_context_url.return_value = False

    post = {"url": "http://example.com"}
    server = "server"
    access_token = "access_token"
    seen_urls = set()
    seen_hosts = set()

    result = find_posts.add_post_with_context(
        post, server, access_token, seen_urls, seen_hosts
    )

    add_context_url.assert_called_once_with(post["url"], server, access_token)

    assert result is False


def test_user_has_opted_out():
    assert user_has_opted_out({"note": "I love robots"}) == False
    assert user_has_opted_out({"note": "I love robots, nobot"}) == True
    assert user_has_opted_out({"note": "/tags/nobot"}) == True
    assert user_has_opted_out({"indexable": False}) == True
    assert user_has_opted_out({"discoverable": False}) == True


@pytest.fixture
def webserver():
    return "server.com"


@pytest.fixture
def userName():
    return "test_user"


def test_get_user_posts_mastodon_success(userName, webserver):
    with patch("find_posts.get_user_id") as mock_get_user_id, patch(
        "find_posts.get"
    ) as mock_get:

        # Mocking get_user_id
        mock_get_user_id.return_value = 1234

        # Mocking get function call
        mock_response = Response()
        mock_response.status_code = 200
        mock_response._content = b'{"data": "Test"}'
        mock_get.return_value = mock_response

        result = get_user_posts_mastodon(userName, webserver)
        assert result == {"data": "Test"}


def test_get_user_posts_mastodon_user_not_found(userName, webserver):
    with patch("find_posts.get_user_id") as mock_get_user_id, patch(
        "find_posts.get"
    ) as mock_get:

        # Mocking get_user_id
        mock_get_user_id.return_value = 1234

        # Mocking get function call
        mock_response = Response()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = get_user_posts_mastodon(userName, webserver)
        assert result == None


def test_get_user_posts_mastodon_error_status_code(userName, webserver):
    with patch("find_posts.get_user_id") as mock_get_user_id, patch(
        "find_posts.get"
    ) as mock_get:

        # Mocking get_user_id
        mock_get_user_id.return_value = 1234

        # Mocking get function call
        mock_response = Response()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = get_user_posts_mastodon(userName, webserver)
        assert result == None


@patch("find_posts.get")
@patch("find_posts.logger")
def test_get_user_posts_lemmy_community(mock_logger, mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"posts": [{"post": {"ap_id": "test_url"}}]}
    mock_get.return_value = mock_response

    result = find_posts.get_user_posts_lemmy(
        "test_user", "https://test.com/c/test_user", "test.com"
    )

    assert result == [{"ap_id": "test_url", "url": "test_url"}]
    mock_get.assert_called_once_with(
        "https://test.com/api/v3/post/list?community_name=test_user&sort=New&limit=50"
    )
    mock_logger.error.assert_not_called()


@patch("find_posts.get")
@patch("find_posts.logger")
def test_get_user_posts_lemmy_user(mock_logger, mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "posts": [{"post": {"ap_id": "post_url"}}],
        "comments": [{"post": {"ap_id": "comment_url"}}],
    }
    mock_get.return_value = mock_response

    result = find_posts.get_user_posts_lemmy(
        "test_user", "https://test.com/u/test_user", "test.com"
    )

    assert result == [
        {"ap_id": "comment_url", "url": "comment_url"},
        {"ap_id": "post_url", "url": "post_url"},
    ]
    mock_get.assert_called_once_with(
        "https://test.com/api/v3/user?username=test_user&sort=New&limit=50"
    )
    mock_logger.error.assert_not_called()


@patch("find_posts.get")
@patch("find_posts.logger")
def test_get_user_posts_peertube(mock_logger, mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": "test_data"}
    mock_get.return_value = mock_response

    result = find_posts.get_user_posts_peertube("test_user", "test_webserver")

    assert result == "test_data"
    mock_get.assert_called_once_with(
        "https://test_webserver/api/v1/accounts/test_user/videos"
    )
    mock_logger.error.assert_not_called()


@patch("find_posts.post")
@patch("find_posts.logger")
def test_get_user_posts_misskey(mock_logger, mock_post):
    mock_response = mock_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"host": None, "id": "id1"},
        {"host": "host1", "id": "id2"},
    ]

    result = get_user_posts_misskey("username", "webserver")

    mock_post.assert_called_with(
        "https://webserver/api/users/notes", {"userId": "id1", "limit": 40}
    )
    mock_logger.error.assert_not_called()
    assert result is not None


@patch("find_posts.get_paginated_mastodon")
@patch("find_posts.filter_known_users")
@patch("find_posts.logger")
def test_get_new_follow_requests(
    mock_logger, mock_filter_known_users, mock_get_paginated_mastodon
):
    mock_get_paginated_mastodon.return_value = ["request1", "request2"]
    mock_filter_known_users.return_value = ["request1"]

    result = get_new_follow_requests("server", "access_token", 10, ["known_following"])

    mock_get_paginated_mastodon.assert_called_with(
        "https://server/api/v1/follow_requests",
        10,
        {
            "Authorization": "Bearer access_token",
        },
    )
    mock_filter_known_users.assert_called_with(
        ["request1", "request2"], ["known_following"]
    )
    mock_logger.info.assert_called_with("Got 2 follow_requests, 1 of which are new")
    assert result == ["request1"]


def test_filter_known_users():
    users = [
        {"acct": "user1"},
        {"acct": "user2"},
        {"acct": "user3"},
    ]
    known_users = ["user1", "user3"]

    filtered_users = filter_known_users(users, known_users)

    assert filtered_users == [{"acct": "user2"}]


def test_filter_known_users_no_known_users():
    users = [
        {"acct": "user1"},
        {"acct": "user2"},
        {"acct": "user3"},
    ]
    known_users = []

    filtered_users = filter_known_users(users, known_users)

    assert filtered_users == users


def test_filter_known_users_all_users_known():
    users = [
        {"acct": "user1"},
        {"acct": "user2"},
        {"acct": "user3"},
    ]
    known_users = ["user1", "user2", "user3"]

    filtered_users = filter_known_users(users, known_users)

    assert filtered_users == []


def test_filter_known_users_no_users():
    users = []
    known_users = ["user1", "user2", "user3"]

    filtered_users = filter_known_users(users, known_users)

    assert filtered_users == []


@patch("find_posts.get_paginated_mastodon")
@patch("find_posts.filter_known_users")
@patch("find_posts.logger")
def test_get_new_followers(
    mock_logger, mock_filter_known_users, mock_get_paginated_mastodon
):
    mock_get_paginated_mastodon.return_value = ["follower1", "follower2", "follower3"]
    mock_filter_known_users.return_value = ["follower2", "follower3"]

    server = "server"
    user_id = 1
    access_token = "access_token"
    max = 50
    known_followers = ["follower1"]

    expected_result = ["follower2", "follower3"]
    result = find_posts.get_new_followers(server, user_id, access_token, max, known_followers)

    mock_get_paginated_mastodon.assert_called_once_with(
        f"https://{server}/api/v1/accounts/{user_id}/followers", max, {
            "Authorization": f"Bearer {access_token}",
        },
    )
    mock_filter_known_users.assert_called_once_with(
        ["follower1", "follower2", "follower3"], known_followers
    )
    mock_logger.info.assert_called_once_with("Got 3 followers, 2 of which are new")

    assert result == expected_result


@patch("find_posts.get_paginated_mastodon")
@patch("find_posts.filter_known_users")
@patch("find_posts.logger")
def test_get_new_followings(
    mock_logger, mock_filter_known_users, mock_get_paginated_mastodon
):
    mock_get_paginated_mastodon.return_value = ["user1", "user2", "user3"]
    mock_filter_known_users.return_value = ["user1", "user2"]
    result = get_new_followings("server", "100", "access_token", 5, "known_users")
    mock_get_paginated_mastodon.assert_called_with(
        "https://server/api/v1/accounts/100/following", 5, {
            "Authorization": "Bearer access_token",
        }
    )
    mock_filter_known_users.assert_called_with(
        ["user1", "user2", "user3"], "known_users"
    )
    assert result == ["user1", "user2"]
    mock_logger.info.assert_called_with("Got 3 followings, 2 of which are new")


@patch("find_posts.get")
def test_get_user_id_with_username(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "123"}
    mock_get.return_value = mock_response
    result = get_user_id("server", user="test_user")
    mock_get.assert_called_with(
        "https://server/api/v1/accounts/lookup?acct=test_user", headers={}
    )
    assert result == "123"


@patch("find_posts.get")
def test_get_user_id_with_access_token(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "456"}
    mock_get.return_value = mock_response
    result = get_user_id("server", access_token="test_token")
    mock_get.assert_called_with(
        "https://server/api/v1/accounts/verify_credentials",
        headers={
            "Authorization": "Bearer test_token",
        },
    )
    assert result == "456"


def test_get_user_id_with_no_user_or_token():
    with pytest.raises(
        Exception,
        match="You must supply either a user name or an access token, to get an user ID",
    ):
        get_user_id("server")


@patch("find_posts.get")
def test_get_user_id_with_404_status_code(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    with pytest.raises(
        Exception, match="User test_user was not found on server server."
    ):
        get_user_id("server", user="test_user")


@patch("find_posts.get")
def test_get_user_id_with_non_200_or_404_status_code(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_get.return_value = mock_response
    with pytest.raises(
        Exception,
        match=re.escape(
            "Error getting URL https://server/api/v1/accounts/lookup?acct=test_user. Status code: 500"
        ),
    ):
        get_user_id("server", user="test_user")


@patch("find_posts.get_toots")
def test_get_timeline(mock_get_toots):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = ["toot1", "toot2", "toot3"]
    mock_response.links = {}
    mock_get_toots.return_value = mock_response

    timeline = find_posts.get_timeline("server", "token", 5)

    mock_get_toots.assert_any_call("https://server/api/v1/timelines/home", "token")
    assert len(timeline) == 3


@patch("find_posts.get", autospec=True)
def test_get_reply_toots_error_status_code(mock_get):
    mock_resp = Mock()
    mock_resp.status_code = 403
    mock_get.return_value = mock_resp
    with pytest.raises(Exception) as e_info:
        find_posts.get_reply_toots(
            "test_user",
            "test_server",
            "test_token",
            ["some_seen_url"],
            datetime(2020, 1, 1),
        )
        assert (
            "Make sure you have the read:statuses scope enabled for your access token."
            in str(e_info.value)
        )


@patch("find_posts.logger")
def test_toot_context_can_be_fetched_public(mock_logger):
    toot = {"visibility": "public", "uri": "sample_uri"}
    result = find_posts.toot_context_can_be_fetched(toot)
    assert result is True
    mock_logger.debug.assert_not_called()


@patch("find_posts.logger")
def test_toot_context_can_be_fetched_unlisted(mock_logger):
    toot = {"visibility": "unlisted", "uri": "sample_uri"}
    result = find_posts.toot_context_can_be_fetched(toot)
    assert result is True
    mock_logger.debug.assert_not_called()


@patch("find_posts.logger")
def test_toot_context_can_be_fetched_private(mock_logger):
    toot = {"visibility": "private", "uri": "sample_uri"}
    result = find_posts.toot_context_can_be_fetched(toot)
    assert result is False
    mock_logger.debug.assert_called_once_with(
        "Cannot fetch context of private toot sample_uri"
    )


toot_with_existing_uri = {
    "uri": "existing_uri",
    "lastSeen": datetime.now(),
    "created_at": datetime.now(),
}

toot_with_new_uri = {
    "uri": "new_uri",
    "lastSeen": datetime.now(),
    "created_at": datetime.now(),
}

recently_checked_context = {"existing_uri": toot_with_existing_uri}


@patch("find_posts.toot_has_parseable_url")
@patch("find_posts.parse_url")
@patch("find_posts.toot_context_can_be_fetched")
@patch("find_posts.toot_context_should_be_fetched")
@patch("find_posts.get_toot_context")
@patch("find_posts.logger", new_callable=Mock())
def test_get_all_known_context_urls(
    mock_logger,
    get_toot_context,
    toot_context_should_be_fetched,
    toot_context_can_be_fetched,
    parse_url,
    toot_has_parseable_url,
):
    server = "test_server"
    reply_toots = [
        {"url": "test_url_1", "reblog": None, "uri": "test_uri_1"},
        {"url": "test_url_2", "reblog": {"url": "reblog_url_2"}, "uri": "test_uri_2"},
    ]
    parsed_urls = ["parsed_url_1", "parsed_url_2"]
    seen_hosts = ["seen_host_1", "seen_host_2"]
    find_posts.recently_checked_context = {
        "test_uri_1": {"lastSeen": datetime.now()},
        "test_uri_2": {"lastSeen": datetime.now()},
    }

    toot_has_parseable_url.return_value = True
    parse_url.return_value = ["parsed_url", "parsed_url_host"]
    toot_context_can_be_fetched.return_value = True
    toot_context_should_be_fetched.return_value = True
    get_toot_context.return_value = ["context_item_1", "context_item_2"]

    result_urls = find_posts.get_all_known_context_urls(
        server, reply_toots, parsed_urls, seen_hosts
    )

    # check if parseable url method called twice and the arguments correct
    assert toot_has_parseable_url.call_count == 2
    toot_has_parseable_url.assert_any_call(reply_toots[0], parsed_urls)
    toot_has_parseable_url.assert_any_call(reply_toots[1], parsed_urls)

    # check if parse url method was first called with the first toot url then with its reblog url
    parse_url.assert_any_call("test_url_1", parsed_urls)
    parse_url.assert_any_call("reblog_url_2", parsed_urls)

    # check if format of logger.info message is correct
    mock_logger.info.assert_called_once_with("Found 2 known context toots")

    # check if the correct context urls are returned
    assert result_urls == {"context_item_1", "context_item_2"}


def test_toot_has_parseable_url_with_parseable_url():
    toot = {"url": "http://test.com", "reblog": None}
    parsed_urls = []
    with patch("find_posts.parse_url", return_value="something") as mock_parse_url:
        assert find_posts.toot_has_parseable_url(toot, parsed_urls)
        mock_parse_url.assert_called_once_with("http://test.com", parsed_urls)


def test_toot_has_parseable_url_with_unparseable_url():
    toot = {"url": "http://test.com", "reblog": None}
    parsed_urls = []
    with patch("find_posts.parse_url", return_value=None) as mock_parse_url:
        assert not find_posts.toot_has_parseable_url(toot, parsed_urls)
        mock_parse_url.assert_called_once_with("http://test.com", parsed_urls)


def test_get_replied_toot_server_id_no_mentions():
    toot = {"in_reply_to_id": "1", "in_reply_to_account_id": "1", "mentions": []}
    assert find_posts.get_replied_toot_server_id("server", toot, {}, {}) is None


def test_get_replied_toot_server_id_no_url_redirect():
    toot = {
        "in_reply_to_id": "1",
        "in_reply_to_account_id": "1",
        "mentions": [{"id": "1", "acct": "account"}],
    }
    with patch("find_posts.get_redirect_url", return_value=None):
        assert find_posts.get_replied_toot_server_id("server", toot, {}, {}) is None


def test_get_replied_toot_server_id_with_url_redirect():
    toot = {
        "in_reply_to_id": "1",
        "in_reply_to_account_id": "1",
        "mentions": [{"id": "1", "acct": "account"}],
    }
    with patch("find_posts.get_redirect_url", return_value="redirect_url"), patch(
        "find_posts.parse_url", return_value="match"
    ) as mock_parse:
        assert find_posts.get_replied_toot_server_id("server", toot, {}, {}) == (
            "redirect_url",
            "match",
        )
        mock_parse.assert_called_once_with("redirect_url", {})


def test_get_replied_toot_server_id_with_existing_replied_toot_server_ids():
    toot = {
        "in_reply_to_id": "1",
        "in_reply_to_account_id": "1",
        "mentions": [{"id": "1", "acct": "account"}],
    }
    replied_toot_server_ids = {"https://server/@account/1": ("url", "match")}

    assert find_posts.get_replied_toot_server_id(
        "server", toot, replied_toot_server_ids, {}
    ) == ("url", "match")


@patch("find_posts.parse_mastodon_profile_url")
@patch("find_posts.parse_pleroma_profile_url")
@patch("find_posts.parse_lemmy_profile_url")
@patch("find_posts.parse_peertube_profile_url")
@patch("find_posts.parse_pixelfed_profile_url")
@patch("find_posts.logger")
def test_parse_user_url(
    mock_logger,
    mock_parse_pixelfed,
    mock_parse_peertube,
    mock_parse_lemmy,
    mock_parse_pleroma,
    mock_parse_mastodon,
):

    url = "test_url"
    match_value = "match"

    # Test that the function return a mastodon url when match is not None
    mock_parse_mastodon.return_value = match_value
    assert find_posts.parse_user_url(url) == match_value
    mock_parse_mastodon.assert_called_once_with(url)

    # Test that the function return a pleroma url when mastodon match is None
    mock_parse_mastodon.return_value = None
    mock_parse_pleroma.return_value = match_value
    assert find_posts.parse_user_url(url) == match_value
    mock_parse_pleroma.assert_called_once_with(url)

    # Continue similarly for the other urls: lemmy, peertube and pixelfed
    mock_parse_pleroma.return_value = None
    mock_parse_lemmy.return_value = match_value
    assert find_posts.parse_user_url(url) == match_value
    mock_parse_lemmy.assert_called_once_with(url)

    mock_parse_lemmy.return_value = None
    mock_parse_peertube.return_value = match_value
    assert find_posts.parse_user_url(url) == match_value
    mock_parse_peertube.assert_called_once_with(url)

    mock_parse_peertube.return_value = None
    mock_parse_pixelfed.return_value = match_value
    assert find_posts.parse_user_url(url) == match_value
    mock_parse_pixelfed.assert_called_once_with(url)

    # Test that function logs an error and returns None when no match is found
    mock_parse_pixelfed.return_value = None
    assert find_posts.parse_user_url(url) == None
    mock_logger.error.assert_called_once_with(f"Error parsing Profile URL {url}")


def test_parse_mastodon_profile_url_success():
    url = "https://mastodon.social/@username"
    result = parse_mastodon_profile_url(url)
    assert result == ("mastodon.social", "username")


def test_parse_mastodon_profile_url_not_match():
    url = "https://mastodon.social/username"
    result = parse_mastodon_profile_url(url)
    assert result == None


def test_parse_mastodon_url():
    valid_url = "https://mastodon.social/@user/1234"
    invalid_url = "https://twitter.com/user/status/1234"
    null_url = None

    # Testing valid mastodon URL
    server, toot_id = parse_mastodon_url(valid_url)
    assert server == "mastodon.social"
    assert toot_id == "1234"

    # Testing invalid URL
    assert parse_mastodon_url(invalid_url) is None

    # Testing null URL
    with pytest.raises(TypeError):
        parse_mastodon_url(null_url)


def test_parse_mastodon_uri():
    # Test that a valid URI is correctly parsed
    uri = "https://my.server.com/users/testuser/statuses/123456"
    assert parse_mastodon_uri(uri) == ("my.server.com", "123456")

    # Test that an invalid URI returns None
    uri = "http://invalid.uri.com"
    assert parse_mastodon_uri(uri) == None

    # Test that a URI missing elements returns None
    uri = "https://missing.elements.com/users/testuser/"
    assert parse_mastodon_uri(uri) == None

    # Test that a URI with extra elements returns the correct server and ID
    uri = "https://extra.elements.com/users/testuser/statuses/123456/7890"
    assert parse_mastodon_uri(uri) == ("extra.elements.com", "123456")

    # Test that a URI with different protocol still works
    uri = "http://still.works.com/users/testuser/statuses/123456"
    assert parse_mastodon_uri(uri) == None

    # Test that a URI without protocol doesn't work
    uri = "nowork/users/testuser/statuses/123456"
    assert parse_mastodon_uri(uri) == None

    # Test that a URI without slashes after https:// doesn't work
    uri = "https://noworkusers/testuser/statuses/123456"
    assert parse_mastodon_uri(uri) == None

    # Test the boundary case of an empty string
    uri = ""
    assert parse_mastodon_uri(uri) == None


@patch("find_posts.get_redirect_url")
def test_parse_pleroma_url(mock_get_redirect_url):
    mock_get_redirect_url.return_value = "/notice/123"

    result = parse_pleroma_url("https://example.com/objects/567")
    assert result == ("example.com", "123")

    mock_get_redirect_url.return_value = None
    result = parse_pleroma_url("https://example.com/objects/567")
    assert result is None

    result = parse_pleroma_url("not a url")
    assert result is None

    mock_get_redirect_url.return_value = "/different_pattern/123"
    result = parse_pleroma_url("https://example.com/objects/567")
    assert result is None

    mock_get_redirect_url.return_value = "/notice/789"
    result = parse_pleroma_url("https://different.example.com/objects/111")
    assert result == ("different.example.com", "789")

def test_parse_pleroma_uri():
    # Test that a valid URI is correctly parsed
    uri = "https://friedcheese.us/notice/Arv4zBVnAR84mmkVay"
    assert parse_pleroma_uri(uri) == ("friedcheese.us", "Arv4zBVnAR84mmkVay")    

import re
import pytest
from find_posts import parse_pleroma_profile_url


def test_parse_pleroma_profile_url():
    # successful parsing
    result = parse_pleroma_profile_url("https://pleroma.server/users/username")
    assert result == ("pleroma.server", "username")

    # unsuccessful parsing
    result = parse_pleroma_profile_url("http://notvalid/url")
    assert result is None

    # url with extra path and query string
    result = parse_pleroma_profile_url(
        "https://pleroma.server/users/username/extra/path?arg=value"
    )
    assert result == ("pleroma.server", "username")

    # url with www
    result = parse_pleroma_profile_url("https://www.pleroma.server/users/username")
    assert result == ("www.pleroma.server", "username")

    # url without https
    result = parse_pleroma_profile_url("http://pleroma.server/users/username")
    assert result is None


def test_parse_pixelfed_url():
    url = "https://server.com/p/username/post123"
    assert parse_pixelfed_url(url) == ("server.com", "post123")


def test_parse_pixelfed_url_no_match():
    url = "https://notaurl.com/abc/123"
    assert parse_pixelfed_url(url) is None


def test_parse_pixelfed_url_malformed():
    url = "malformed url"
    assert parse_pixelfed_url(url) is None


def test_parse_misskey_url():
    url = "https://misskey.io/notes/837jfe8372"
    server, toot_id = parse_misskey_url(url)
    assert server == "misskey.io"
    assert toot_id == "837jfe8372"


def test_parse_misskey_url_no_match():
    url = "https://notamisskeyurl.com"
    result = parse_misskey_url(url)
    assert result is None


def test_parse_misskey_url_incorrect_path():
    url = "https://misskey.io/notnotes/837jfe8372"
    result = parse_misskey_url(url)
    assert result is None


def test_parse_peertube_url_valid():
    # define a valid url
    url = "https://example.com/videos/watch/123456789"

    # the expected server and id from the url
    expected = ("example.com", "123456789")

    # call the function with the valid url
    result = parse_peertube_url(url)

    # assert that the result is as expected
    assert result == expected

def test_parse_url():
    tests = [
        (
            "https://video.infosec.exchange/videos/watch/56f1d0b5-d98f-4bad-b1e7-648ae074ab9d",
            ("video.infosec.exchange", "56f1d0b5-d98f-4bad-b1e7-648ae074ab9d")
        ),
        (
            "https://veedeo.org/videos/watch/a51bb77c-e1bd-4d6a-b119-95af176f6d66",
            ("veedeo.org", "a51bb77c-e1bd-4d6a-b119-95af176f6d66")
        ),
        (
            'https://foo.bar/nothing',
            None
        )
    ]
    for (url,expected) in tests:
        result = parse_url(url, {})
        assert result == expected


def test_parse_peertube_url_invalid():
    # define an invalid url
    url = "https://bad.example.com/watch/123456789"

    # call the function with the invalid url
    result = parse_peertube_url(url)

    # assert that the result is None
    assert result is None


def test_parse_peertube_url_no_match():
    # define a url without a match
    url = "https://example.com/videos/123456789"

    # call the function with the url without a match
    result = parse_peertube_url(url)

    # assert that the result is None
    assert result is None


def test_parse_pixelfed_profile_url_success():
    url = "https://pixelfed.server/user.name"
    server, username = parse_pixelfed_profile_url(url)
    assert server == "pixelfed.server"
    assert username == "user.name"


def test_parse_pixelfed_profile_url_invalid_url():
    url = "pixelfed.server/user.name"
    result = parse_pixelfed_profile_url(url)
    assert result is None


def test_parse_pixelfed_profile_url_empty_url():
    url = ""
    result = parse_pixelfed_profile_url(url)
    assert result is None


def test_parse_lemmy_url_success():
    url = "https://testserver/post/1234"

    result = parse_lemmy_url(url)

    assert result == ("testserver", "1234")


def test_parse_lemmy_url_fail_invalid_url():
    url = "http://testserver/post/1234"

    result = parse_lemmy_url(url)

    assert result == None


def test_parse_lemmy_url_fail_no_id():
    url = "https://testserver/post/"

    result = parse_lemmy_url(url)

    assert result == None


def test_parse_lemmy_url_fail_no_protocol():
    url = "testserver/post/1234"

    result = parse_lemmy_url(url)

    assert result == None


def test_parse_lemmy_profile_url():
    url = "https://my.lemmy.server/u/username"
    result = parse_lemmy_profile_url(url)
    assert result == ("my.lemmy.server", "username")


def test_parse_lemmy_profile_url_no_match():
    url = "http://my.lemmy.server/u/username"
    result = parse_lemmy_profile_url(url)
    assert result is None


def test_parse_lemmy_profile_url_with_community():
    url = "https://my.lemmy.server/c/username"
    result = parse_lemmy_profile_url(url)
    assert result == ("my.lemmy.server", "username")


def test_parse_peertube_profile_url_valid():
    server, username = parse_peertube_profile_url(
        "https://myserver.com/accounts/TestUser"
    )
    assert server == "myserver.com"
    assert username == "TestUser"


def test_parse_peertube_profile_url_invalid():
    assert parse_peertube_profile_url("https://invalidurl.com/TestUser") is None


def test_parse_peertube_profile_url_none():
    with pytest.raises(TypeError):
        parse_peertube_profile_url(None)


@patch("find_posts.requests")
@patch("find_posts.logger")
def test_get_redirect_url_success(mock_logger, mock_requests):
    response = Response()
    response.status_code = 200
    mock_requests.head.return_value = response
    assert find_posts.get_redirect_url("https://test.com") == "https://test.com"
    mock_logger.error.assert_not_called()
    mock_logger.debug.assert_not_called()


@patch("find_posts.requests")
@patch("find_posts.logger")
def test_get_redirect_url_redirected(mock_logger, mock_requests):
    response = Response()
    response.status_code = 302
    response.headers = {"Location": "https://redirected.com"}
    mock_requests.head.return_value = response
    assert find_posts.get_redirect_url("https://test.com") == "https://redirected.com"
    mock_logger.error.assert_not_called()
    mock_logger.debug.assert_called_once()


@patch("find_posts.requests")
@patch("find_posts.logger")
def test_get_redirect_url_error_status_code(mock_logger, mock_requests):
    response = Response()
    response.status_code = 500
    mock_requests.head.return_value = response
    assert find_posts.get_redirect_url("https://test.com") is None
    mock_logger.error.assert_called_once()
    mock_logger.debug.assert_not_called()


@patch("find_posts.requests")
@patch("find_posts.logger")
def test_get_redirect_url_exception(mock_logger, mock_requests):
    mock_requests.head.side_effect = requests.exceptions.RequestException
    assert find_posts.get_redirect_url("https://test.com") is None
    mock_logger.error.assert_called_once()
    mock_logger.debug.assert_not_called()


@patch("find_posts.get_server_info")
@patch("find_posts.logger")
def test_get_toot_context_no_server_info(mock_logger, mock_server_info):
    mock_server_info.return_value = None
    assert get_toot_context("server1", "toot1", "url1", {}) == []
    mock_logger.error.assert_called_once_with("server server1 not found for post")


@pytest.fixture
def mock_response_success():
    return_value = MagicMock()
    return_value.status_code = 200
    return_value.json.return_value = {
        "ancestors": [{"url": "https://abc.com/statuses/123456"}],
        "descendants": [{"url": "https://abc.com/statuses/789012"}],
    }
    return return_value


@pytest.fixture
def mock_response_fail():
    return_value = MagicMock()
    return_value.status_code = 404
    return return_value


@patch("find_posts.get")
@patch("find_posts.logger")
def test_get_mastodon_urls_request_fail(mock_logger, mock_get, mock_response_fail):
    mock_get.return_value = mock_response_fail

    result = find_posts.get_mastodon_urls(
        "abc.com", "123456", "https://abc.com/statuses/123456"
    )

    assert list(result) == []
    mock_logger.error.assert_called_once()


@patch("find_posts.get")
@patch("find_posts.logger")
def test_get_mastodon_urls_exception(mock_logger, mock_get):
    mock_get.side_effect = Exception("Test exception")

    result = find_posts.get_mastodon_urls(
        "abc.com", "123456", "https://abc.com/statuses/123456"
    )

    assert list(result) == []
    mock_logger.error.assert_called_once()


@patch("find_posts.get_lemmy_comment_context")
@patch("find_posts.get_lemmy_comments_urls")
@patch("find_posts.logger")
def test_get_lemmy_urls_comment(
    mock_logger, mock_get_lemmy_comments_urls, mock_get_lemmy_comment_context
):
    webserver = "webserver"
    toot_id = "toot_id"
    toot_url = "/comment/"

    get_lemmy_urls(webserver, toot_id, toot_url)

    mock_get_lemmy_comment_context.assert_called_once_with(webserver, toot_id, toot_url)
    mock_logger.error.assert_not_called()


@patch("find_posts.get_lemmy_comment_context")
@patch("find_posts.get_lemmy_comments_urls")
@patch("find_posts.logger")
def test_get_lemmy_urls_post(
    mock_logger, mock_get_lemmy_comments_urls, mock_get_lemmy_comment_context
):
    webserver = "webserver"
    toot_id = "toot_id"
    toot_url = "/post/"

    get_lemmy_urls(webserver, toot_id, toot_url)

    mock_get_lemmy_comments_urls.assert_called_once_with(webserver, toot_id, toot_url)
    mock_logger.error.assert_not_called()


@patch("find_posts.get_lemmy_comment_context")
@patch("find_posts.get_lemmy_comments_urls")
@patch("find_posts.logger")
def test_get_lemmy_urls_else(
    mock_logger, mock_get_lemmy_comments_urls, mock_get_lemmy_comment_context
):
    webserver = "webserver"
    toot_id = "toot_id"
    toot_url = "/else/"

    result = get_lemmy_urls(webserver, toot_id, toot_url)

    assert result == []
    mock_get_lemmy_comments_urls.assert_not_called()
    mock_get_lemmy_comment_context.assert_not_called()
    mock_logger.error.assert_called_once_with(f"unknown lemmy url type {toot_url}")


@patch("find_posts.get")
@patch("find_posts.logger")
def test_get_lemmy_comment_context_get_fail(mock_logger, mock_get):
    mock_get.side_effect = Exception

    assert (
        get_lemmy_comment_context("webserver.com", "test_toot_id", "test_toot_url")
        == []
    )

    mock_get.assert_called_once_with(
        "https://webserver.com/api/v3/comment?id=test_toot_id"
    )
    mock_logger.error.assert_called_once()


@patch("find_posts.get")
@patch("find_posts.logger")
def test_get_lemmy_comment_context_parse_fail(mock_logger, mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"invalid_key": "invalid_value"}

    assert (
        get_lemmy_comment_context("webserver.com", "test_toot_id", "test_toot_url")
        == []
    )

    mock_get.assert_called_once_with(
        "https://webserver.com/api/v3/comment?id=test_toot_id"
    )
    mock_logger.error.assert_called_once()


def test_get_peertube_urls_success():
    with patch("find_posts.get") as mock_get:
        mock_resp = Response()
        mock_resp.status_code = 200
        mock_resp._content = json.dumps(
            {"data": [{"url": "http://example.com/1"}, {"url": "http://example.com/2"}]}
        ).encode("utf-8")

        mock_get.return_value = mock_resp

        urls = get_peertube_urls("example.com", "123", "http://toot_url.com")
        mock_get.assert_called_once_with(
            "https://example.com/api/v1/videos/123/comment-threads"
        )
        assert urls == ["http://example.com/1", "http://example.com/2"]


@patch("find_posts.logger")
def test_get_peertube_urls_exception(mock_logger):
    with patch("find_posts.get") as mock_get:
        mock_get.side_effect = Exception("Test exception")

        urls = get_peertube_urls("example.com", "123", "http://toot_url.com")
        mock_get.assert_called_once_with(
            "https://example.com/api/v1/videos/123/comment-threads"
        )
        mock_logger.error.assert_called_once_with(
            "Error getting comments on video 123 from http://toot_url.com. Exception: Test exception"
        )
        assert urls == []


def test_get_misskey_urls_success():
    with patch("find_posts.post") as mock_post, patch(
        "find_posts.logger"
    ) as mock_logger:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": "123"}, {"id": "456"}]
        mock_post.return_value = mock_response
        result = get_misskey_urls("testserver", "1", "testurl")
        expected = [
            "https://testserver/notes/123",
            "https://testserver/notes/456",
            "https://testserver/notes/123",
            "https://testserver/notes/456",
        ]
        assert result == expected
        assert mock_post.call_count == 2
        assert mock_logger.debug.call_count == 2


def test_get_misskey_urls_post_error():
    with patch("find_posts.post") as mock_post, patch(
        "find_posts.logger"
    ) as mock_logger:
        mock_post.side_effect = Exception("Error")
        result = get_misskey_urls("testserver", "1", "testurl")
        expected = []
        assert result == expected
        assert mock_post.call_count == 1
        assert mock_logger.error.call_count == 1


def test_get_misskey_urls_non_200_response():
    with patch("find_posts.post") as mock_post, patch(
        "find_posts.logger"
    ) as mock_logger:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response
        result = get_misskey_urls("testserver", "1", "testurl")
        expected = []
        assert result == expected
        assert mock_logger.error.called


def test_get_misskey_urls_json_error():
    with patch("find_posts.post") as mock_post, patch(
        "find_posts.logger"
    ) as mock_logger:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = Exception("JSON Error")
        mock_post.return_value = mock_response
        result = get_misskey_urls("testserver", "1", "testurl")
        expected = []
        assert result == expected
        assert mock_post.call_count == 2
        assert mock_logger.error.call_count == 2


@patch("find_posts.add_context_url", return_value=False)
@patch("find_posts.logger")
def test_add_context_urls_all_fail(mock_logger, mock_add_context_url):
    server = "test_server"
    access_token = "test_token"
    context_urls = ["url1", "url2", "url3", "url4"]
    seen_urls = set()

    result = add_context_urls(server, access_token, context_urls, seen_urls)

    assert mock_add_context_url.call_count == 4
    assert len(seen_urls) == 0
    assert (
        mock_logger.info.call_args[0][0]
        == "Added 0 new context toots (with 4 failures)"
    )


@patch("find_posts.add_context_url", return_value=True)
@patch("find_posts.logger")
def test_add_context_urls_all_success(mock_logger, mock_add_context_url):
    server = "test_server"
    access_token = "test_token"
    context_urls = ["url1", "url2", "url3", "url4"]
    seen_urls = set()

    result = add_context_urls(server, access_token, context_urls, seen_urls)

    assert mock_add_context_url.call_count == 4
    assert len(seen_urls) == 4
    assert "url1" in seen_urls
    assert "url2" in seen_urls
    assert "url3" in seen_urls
    assert "url4" in seen_urls
    assert (
        mock_logger.info.call_args[0][0]
        == "Added 4 new context toots (with 0 failures)"
    )


class MockResponse:
    def __init__(self, status_code, links=None, json_data=None):
        self.status_code = status_code
        self.links = links
        self.json_data = json_data

    def json(self):
        return self.json_data


def test_add_context_url():
    with patch("find_posts.get", return_value=MockResponse(200)) as mocked_get:
        result = find_posts.add_context_url("test-url", "test-server", "test-token")
        assert result
        mocked_get.assert_called_once()
        assert (
            mocked_get.call_args[0][0]
            == "https://test-server/api/v2/search?q=test-url&resolve=true&limit=1"
        )

    with patch("find_posts.get", return_value=MockResponse(403)) as mocked_get:
        result = find_posts.add_context_url("test-url", "test-server", "test-token")
        assert not result


def test_get_paginated_mastodon():
    json_data = [{"created_at": "2022-02-18T05:31:00.000Z"} for _ in range(10)]
    with patch(
        "find_posts.get", return_value=MockResponse(200, json_data=json_data)
    ) as mocked_get:
        result = find_posts.get_paginated_mastodon("test-url", 10)
        assert len(result) == 10
        mocked_get.assert_called_once()

    with patch("find_posts.get", return_value=MockResponse(401)) as mocked_get:
        with pytest.raises(Exception):
            find_posts.get_paginated_mastodon("test-url", 10)

    with patch("find_posts.get", return_value=MockResponse(403)) as mocked_get:
        with pytest.raises(Exception):
            find_posts.get_paginated_mastodon("test-url", 10)

    with patch("find_posts.get", return_value=MockResponse(500)) as mocked_get:
        with pytest.raises(Exception):
            find_posts.get_paginated_mastodon("test-url", 10)


def test_get_cached_robots_cached():
    find_posts.ROBOTS_TXT = {"test_url": "test_robots_txt"}
    assert find_posts.get_cached_robots("test_url") == "test_robots_txt"


@patch("find_posts.get_robots_txt_cache_path", return_value="test_cache_path")
def test_get_cached_robots_no_cache(mock_get_path):
    find_posts.ROBOTS_TXT = {}
    assert find_posts.get_cached_robots("test_url") is None


@patch("find_posts.get_cached_robots", return_value="test_robots_txt")
def test_get_robots_from_url_cached(mock_get_cached_robots):
    assert find_posts.get_robots_from_url("test_url") == "test_robots_txt"


@patch("find_posts.get")
@patch("find_posts.get_cached_robots", return_value=None)
def test_get_robots_from_url_exception(mock_get_cached_robots, mock_get):
    mock_get.side_effect = Exception
    find_posts.ROBOTS_TXT = {}
    assert find_posts.get_robots_from_url("test_url") is True
    assert find_posts.ROBOTS_TXT["test_url"] is True


@patch("find_posts.get_robots_from_url")
@patch("urllib.robotparser.RobotFileParser")
def test_can_fetch(mock_robotFileParser, mock_get_robots_from_url):
    test_url = "http://test.com"
    test_user_agent = "test_agent"

    # Prepare mocks
    mock_robotsTxt = MagicMock()
    mock_robotParser = MagicMock()
    find_posts.INSTANCE_BLOCKLIST = []

    # Mock return values
    mock_get_robots_from_url.return_value = mock_robotsTxt
    mock_robotFileParser.return_value = mock_robotParser

    mock_robotsTxt.splitlines.return_value = "User-agent: *\nDisallow: /"
    mock_robotParser.can_fetch.return_value = True

    # Call function
    result = find_posts.can_fetch(test_user_agent, test_url)

    # Check calls and results
    mock_get_robots_from_url.assert_called_once_with(
        "{uri.scheme}://{uri.netloc}/robots.txt".format(uri=parse.urlparse(test_url))
    )
    mock_robotParser.parse.assert_called_once_with(mock_robotsTxt.splitlines())
    mock_robotParser.can_fetch.assert_called_once_with(test_user_agent, test_url)
    assert result is True

    # Testing when get_robots_from_url return bool type
    mock_get_robots_from_url.return_value = True
    result = find_posts.can_fetch(test_user_agent, test_url)
    assert result is True


@pytest.fixture
def headers():
    return {"User-Agent": "test-agent"}


@pytest.fixture
def url():
    return "http://test.com"


@patch("find_posts.requests")
def test_robots_txt_prohibited(mock_requests, headers, url):
    with patch("find_posts.can_fetch") as mock_can_fetch:
        mock_can_fetch.return_value = False
        with pytest.raises(Exception) as exc_info:
            get(url, headers)

        assert "prohibited by robots.txt" in str(exc_info.value)
        mock_can_fetch.assert_called_once_with(headers["User-Agent"], url)


@patch("find_posts.requests")
@patch("find_posts.can_fetch")
@patch("find_posts.user_agent")
@patch("find_posts.logger")
def test_post_success(mock_logger, mock_user_agent, mock_can_fetch, mock_requests):
    url = "http://testurl.com"
    mock_json = {"key": "value"}
    headers = {"User-Agent": "test_agent"}
    timeout = 2
    mock_user_agent.return_value = "test_agent"
    mock_can_fetch.return_value = True
    mock_requests.post.return_value.status_code = 200

    post(url, mock_json, headers, timeout)

    mock_requests.post.assert_called_once_with(
        url, json=mock_json, headers=headers, timeout=timeout
    )


@patch("find_posts.requests")
@patch("find_posts.can_fetch")
@patch("find_posts.user_agent")
@patch("find_posts.logger")
def test_post_rate_limit(mock_logger, mock_user_agent, mock_can_fetch, mock_requests):
    url = "http://testurl.com"
    mock_json = {"key": "value"}
    headers = {"User-Agent": "test_agent"}
    timeout = 2
    mock_user_agent.return_value = "test_agent"
    mock_can_fetch.return_value = True
    response = Mock()
    response.status_code = 429
    response.headers = {"x-ratelimit-reset": "1900-01-01 01:00:00"}
    mock_requests.post.return_value = response

    with pytest.raises(Exception):
        post(url, mock_json, headers, timeout)


@patch("find_posts.requests")
@patch("find_posts.can_fetch")
@patch("find_posts.user_agent")
@patch("find_posts.logger")
def test_post_robotstxt_disallowed(
    mock_logger, mock_user_agent, mock_can_fetch, mock_requests
):
    url = "http://testurl.com"
    mock_json = {"key": "value"}
    headers = {}
    mock_user_agent.return_value = "test_agent"
    mock_can_fetch.return_value = False

    with pytest.raises(Exception):
        post(url, mock_json, headers)


@patch("find_posts.get", autospec=True)
@patch("find_posts.ET.fromstring", autospec=True)
@patch("find_posts.logger", autospec=True)
def test_get_server_from_host_meta(mock_logger, mock_parse, mock_get):
    server = "dummy-server"
    result = "result"

    # Happy Path
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "<dummy>dummy text</dummy>"
    mock_get.return_value = mock_response
    mock_parse.return_value.find.return_value.get.return_value = f"https://{result}/"
    assert find_posts.get_server_from_host_meta(server) == result
    mock_get.assert_called_once_with(
        f"https://{server}/.well-known/host-meta", timeout=30
    )
    mock_parse.assert_called_once_with(mock_response.text)
    mock_logger.error.assert_not_called()

    # Case when get(url) call throws an Exception
    mock_get.side_effect = Exception("mocked exception")
    assert find_posts.get_server_from_host_meta(server) is None
    mock_logger.error.assert_called_once()

    # Case when status code is not 200
    mock_response.status_code = 404
    mock_get.side_effect = None
    assert find_posts.get_server_from_host_meta(server) is None
    mock_logger.error.assert_called()

    # Case when parsing fails
    mock_response.status_code = 200
    mock_parse.side_effect = Exception("mocked exception")
    assert find_posts.get_server_from_host_meta(server) is None
    mock_logger.error.assert_called()

    # Case when matching fails
    mock_parse.side_effect = None
    mock_parse.return_value.find.return_value.get.return_value = "malformed url"
    assert find_posts.get_server_from_host_meta(server) is None
    mock_logger.error.assert_called()


@patch("find_posts.get", side_effect=Exception("Mock Exception"))
@patch("find_posts.logger")
def test_get_nodeinfo_get_exception(mock_logger, mock_get):
    response = find_posts.get_nodeinfo("test_server", {})
    mock_logger.error.assert_called()
    assert response is None


@patch("find_posts.get", return_value=Mock(status_code=404))
@patch("find_posts.get_server_from_host_meta", return_value="new_server")
@patch("find_posts.logger")
def test_get_nodeinfo_404_status_no_fallback(mock_logger, mock_get_server, mock_get):
    response = find_posts.get_nodeinfo("test_server", {})
    mock_logger.debug.assert_called()
    assert response is None


@patch("find_posts.get", return_value=Mock(status_code=200))
@patch("find_posts.logger")
def test_get_nodeinfo_200_status_no_links(mock_logger, mock_get):
    mock_get.return_value.json.return_value = {"links": []}
    response = find_posts.get_nodeinfo("test_server", {})
    mock_logger.error.assert_called()
    assert response is None


@patch("find_posts.get", return_value=Mock(status_code=404))
@patch("find_posts.logger")
def test_get_nodeinfo_404_status(mock_logger, mock_get):
    mock_get.return_value.json.return_value = {
        "links": [
            {
                "rel": "http://nodeinfo.diaspora.software/ns/schema/2.0",
                "href": "http://test.com",
            }
        ]
    }
    response = find_posts.get_nodeinfo("test_server", {})
    mock_logger.error.assert_called()
    assert response is None


def test_set_server_apis():
    # mock server data
    server = {
        "software": "mastodon",
        "rawnodeinfo": {"metadata": {"features": ["mastodon_api"]}},
    }

    # call the function to test
    set_server_apis(server)

    # check APIs support
    assert server["mastodonApiSupport"] == True
    assert server["misskeyApiSupport"] == False
    assert server["lemmyApiSupport"] == False
    assert server["peertubeApiSupport"] == False

    # check if 'last_checked' is updated
    assert isinstance(server["last_checked"], datetime)


def test_set_server_apis_without_metadata():
    # mock server data
    server = {"software": "mastodon", "rawnodeinfo": {}}

    # call the function to test
    set_server_apis(server)

    # check APIs support
    assert server["mastodonApiSupport"] == True
    assert server["misskeyApiSupport"] == False
    assert server["lemmyApiSupport"] == False
    assert server["peertubeApiSupport"] == False

    # check if 'last_checked' is updated
    assert isinstance(server["last_checked"], datetime)


def test_set_server_apis_with_unknown_software():
    # mock server data
    server = {
        "software": "unknown",
        "rawnodeinfo": {"metadata": {"features": ["unknown_feature"]}},
    }

    # call the function to test
    set_server_apis(server)

    # check APIs support
    assert server["mastodonApiSupport"] == False
    assert server["misskeyApiSupport"] == False
    assert server["lemmyApiSupport"] == False
    assert server["peertubeApiSupport"] == False

    # check if 'last_checked' is updated
    assert isinstance(server["last_checked"], datetime)


@patch("find_posts.get_paginated_mastodon")
def test_get_user_lists(mock_get_paginated_mastodon):
    mock_get_paginated_mastodon.return_value = "Test value"

    server = "test-server"
    token = "test-token"
    expected_url = f"https://{server}/api/v1/lists"
    expected_limit = 99
    expected_headers = {"Authorization": f"Bearer {token}"}

    result = find_posts.get_user_lists(server, token)

    mock_get_paginated_mastodon.assert_called_once_with(
        expected_url, expected_limit, expected_headers
    )

    assert result == "Test value"


@patch("find_posts.get_paginated_mastodon")
@patch("find_posts.logger")
def test_get_list_timeline(mock_logger, mock_get_paginated_mastodon):
    # Arrange
    server = "mastodon.social"
    list_info = {"id": 123, "title": "test_list"}
    token = "token12345"
    max = 100
    mock_get_paginated_mastodon.return_value = ["post1", "post2"]

    # Act
    result = get_list_timeline(server, list_info, token, max)

    # Assert
    mock_get_paginated_mastodon.assert_called_once_with(
        f"https://{server}/api/v1/timelines/list/{list_info['id']}",
        max,
        {
            "Authorization": f"Bearer {token}",
        },
    )
    mock_logger.info.assert_called_once_with(
        f"Found {len(mock_get_paginated_mastodon.return_value)} toots in list {list_info['title']}"
    )
    assert len(result) == 2
    assert result == ["post1", "post2"]


@patch("find_posts.get_paginated_mastodon")
@patch("find_posts.logger")
def test_get_list_users(mock_logger, mock_get_paginated_mastodon):
    # define mock values
    mock_server = "mock_server"
    mock_list = {"id": "mock_id", "title": "mock_title"}
    mock_token = "mock_token"
    mock_max = 5
    mock_accounts = ["account1", "account2", "account3"]

    # setup expected url
    expected_url = f"https://{mock_server}/api/v1/lists/{mock_list['id']}/accounts"

    # Mock the return value of get_paginated_mastodon
    mock_get_paginated_mastodon.return_value = mock_accounts

    # Call the function with the mock values
    result = get_list_users(mock_server, mock_list, mock_token, mock_max)

    # Assert the function called get_paginated_mastodon with correct arguments
    mock_get_paginated_mastodon.assert_called_once_with(
        expected_url, mock_max, {"Authorization": f"Bearer {mock_token}"}
    )

    # Assert the function called logger.info with correct arguments
    mock_logger.info.assert_called_once_with(
        f"Found {len(mock_accounts)} accounts in list {mock_list['title']}"
    )

    # Assert the function returned correct result
    assert result == mock_accounts


@patch("find_posts.get_all_known_context_urls")
@patch("find_posts.add_context_urls")
@patch("find_posts.add_user_posts")
@patch("find_posts.filter_known_users")
def test_fetch_timeline_context_with_empty_posts(
    mock_filter_known_users,
    mock_add_user_posts,
    mock_add_context_urls,
    mock_get_all_known_context_urls,
):
    # Arrange
    timeline_posts = []
    token, parsed_urls, seen_hosts = "", [], []
    seen_urls, all_known_users, recently_checked_users = [], [], []
    arguments = type("", (), {})()
    arguments.server = "server_test"
    arguments.backfill_mentioned_users = 0

    # Act
    find_posts.arguments = arguments
    find_posts.fetch_timeline_context(
        timeline_posts,
        token,
        parsed_urls,
        seen_hosts,
        seen_urls,
        all_known_users,
        recently_checked_users,
    )

    # Assert
    mock_get_all_known_context_urls.assert_called_once_with(
        arguments.server, timeline_posts, parsed_urls, seen_hosts
    )
    mock_add_context_urls.assert_called_once_with(
        arguments.server, token, mock_get_all_known_context_urls.return_value, seen_urls
    )
    assert not mock_filter_known_users.called
    assert not mock_add_user_posts.called
