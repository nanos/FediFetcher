# FediFetcher configuration options

FediFetcher has quite a few configuration options, so here is my quick configuration advice, that should probably work for most people:

> [!CAUTION]
>
> **Remove the `access-token` from the `config.json`** when running FediFetcher as GitHub Action. When running FediFetcher as GitHub Action **ALWAYS** [set the Access Token as an Action Secret](./github-actions.md).

```json
{
  "access-token": "Your access token",
  "server": "your.mastodon.server",
  "home-timeline-length": 200,
  "max-followings": 80,
  "from-notifications": 1
}
```

If you configure FediFetcher this way, it'll fetch missing remote replies to the last 200 posts in your home timeline. It'll additionally backfill profiles of the last 80 people you followed, and of every account who appeared in your notifications during the past hour.

## Providing configuration options

Unless you are running FediFetcher as GitHub Action (please see above for instructions on configuring FediFetcher with GitHub Actions), there are a three ways in which you provide configuration options:

1. Configuration File: <br>
   You can provide a `json` file with configuration options. Then run the script like so: <br>`python find_posts.py -c=/path/to/config.json`
2. Command line flags: <br>
   You can provide all options directly in the command line. Simply run the script with te correct options supplied: <br>`python find_posts.py --server=example.com --home-timeline-length=80`.
3. Environment variables: <br>
   You can supply your options as environment variables. To do so take the option name from the table below, replace `-` with `_` and prefix with `FF_`. For example `max-favourites` can be set via `FF_MAX_FAVOURITES`. (Environment variables are not case sensitive.)



## Advanced Options

Below is a list of all configuration options, including their descriptions.

Option | Required? | Notes |
|:----------------------------------------------------|-----------|:------|
|`access-token` | Yes | The access token. If using GitHub action, this needs to be provided as a Secret called  `ACCESS_TOKEN`. If running as a cron job or a container, you can supply this option as array, to [fetch posts for multiple users](https://blog.thms.uk/2023/04/muli-user-support-for-fedifetcher) on your instance. To set tokens for multiple users using environment variables, define multiple environment variables with `FF_ACCESS_TOKEN` prefix, eg. `FF_ACCESS_TOKEN_USER1=…` and `FF_ACCESS_TOKEN_USER2=…`|
|`server`|Yes|The domain only of your mastodon server (without `https://` prefix) e.g. `mstdn.thms.uk`. |
|`instance-blocklist` | No | A comma seperated list of instance domains that FediFetcher should never attempt to connect to. 
|`home-timeline-length` | No | Provide to fetch remote replies to posts in the API-Key owner's home timeline. Determines how many posts we'll fetch replies for. Recommended value: `200`.
| `max-bookmarks` | No | Provide to fetch remote replies to any posts you have bookmarked. Determines how many of your bookmarks you want to get replies to. Recommended value: `80`. Requires an access token with `read:bookmarks` scope.
| `max-favourites` | No | Provide to fetch remote replies to any posts you have favourited. Determines how many of your favourites you want to get replies to. Recommended value: `40`. Requires an access token with `read:favourites` scope.
| `max-followings` | No | Provide to backfill profiles for your most recent followings. Determines how many of your last followings you want to backfill. Recommended value: `80`.
| `max-followers` | No | Provide to backfill profiles for your most recent followers. Determines how many of your last followers you want to backfill. Recommended value: `80`.
| `max-follow-requests` | No | Provide to backfill profiles for the API key owner's most recent pending follow requests. Determines how many of your last follow requests you want to backfill. Recommended value: `80`.
| `from-notifications` | No | Provide to backfill profiles of anyone mentioned in your recent notifications. Determines how many hours of notifications you want to look at. Requires an access token with `read:notifications` scope. Recommended value: `1`, unless you run FediFetcher less than once per hour.
| `reply-interval-in-hours` | No | Provide to fetch remote replies to posts that have received replies from users on your own instance. Determines how far back in time we'll go to find posts that have received replies. You must be administrator on your instance to use this option, and this option is not supported on Pleroma / Akkoma and its forks. Recommend value: `0` (disabled). Requires an access token with `admin:read:accounts`.
|`backfill-with-context` | No | Set to `0` to disable fetching remote replies while backfilling profiles. This is enabled by default, but you can disable it, if it's too slow for you.
|`backfill-mentioned-users` | No | Set to `0` to disable backfilling any mentioned users when fetching the home timeline. This is enabled by default, but you can disable it, if it's too slow for you.
| `from-lists`| No | Set to `1` to fetch missing replies and/or backfill account from your lists. This is disabled by default. Requires an access token with `read:lists` scope. |
| `max-list-length` | No | Determines how many posts we'll fetch replies for in each list. Default value: `100`. This will be ignored, unless you also provide `from-lists = 1`. Set to `0` if you only want to backfill profiles in lists. |
| `max-list-accounts` | No | Determines how many accounts we'll backfill for in each list. Default value: `10`. This will be ignored, unless you also provide `from-lists = 1`. Set to `0` if you only want to fetch replies in lists. |
| `remember-users-for-hours` | No | How long between back-filling attempts for non-followed accounts? Defaults to `168`, i.e. one week.
| `remember-hosts-for-days` | No | How long should FediFetcher cache host info for? Defaults to `30`.
| `http-timeout` | No | The timeout for any HTTP requests to the Mastodon API in seconds. Defaults to `5`.
| `lock-hours` | No | Determines after how many hours a lock file should be discarded. Not relevant when running the script as GitHub Action, as concurrency is prevented using a different mechanism. Recommended value: `24`.
| `lock-file` | No | Location for the lock file. If not specified, will use `lock.lock` under the state directory. Not relevant when running the script as GitHub Action.
| `state-dir` | No | Directory storing persistent files, and the default location for lock file. Not relevant when running the script as GitHub Action.
| `on-start` | No | Optionally provide a callback URL that will be pinged when processing is starting. A query parameter `rid={uuid}` will automatically be appended to uniquely identify each execution. This can be used to monitor your script using a service such as healthchecks.io.
| `on-done` | No | Optionally provide a callback URL that will be called when processing is finished.  A query parameter `rid={uuid}` will automatically be appended to uniquely identify each execution. This can be used to monitor your script using a service such as healthchecks.io.
| `on-fail` | No | Optionally provide a callback URL that will be called when processing has failed.  A query parameter `rid={uuid}` will automatically be appended to uniquely identify each execution. This can be used to monitor your script using a service such as healthchecks.io.
|`log-level` | No | The severity of messages to log. Possible values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. Defaults to `DEBUG`. |
|`log-format` | No | The format used for logging. See the [documentation](https://docs.python.org/3/library/logging.html) for details. Defaults to `%(asctime)s: %(message)s` |

## Multi User support

If you wish to [run FediFetcher for multiple users on your instance](https://blog.thms.uk/2023/04/muli-user-support-for-fedifetcher?utm_source=github), you can supply the `access-token` as an array, with different access tokens for different users. That will allow you to fetch replies and/or backfill profiles for multiple users on your account.

This is only supported when running FediFetcher as cron job, or container. Multi-user support is not available when running FediFetcher as GitHub Action.

## Required Access Token Scopes

 - For all actions, your access token must include these scopes:
   - `read:search`
   - `read:statuses`
   - `read:accounts`
 - If you are supplying `reply-interval-in-hours` you must additionally enable this scope:
   - `admin:read:accounts`
 - If you are supplying `max-follow-requests` you must additionally enable this scope:
   - `read:follows`
 - If you are supplying `max-bookmarks` you must additionally enable this scope:
   - `read:bookmarks`
 - If you are supplying `max-favourites` you must additionally enable this scope:
   - `read:favourites`
 - If you are supplying `from-notifications` you must additionally enable this scope:
   - `read:notifications`
 - If you are supplying `from-lists` you must additionally enable this scope:
   - `read:lists`
