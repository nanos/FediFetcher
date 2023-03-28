# FediFetcher for Mastodon

This GitHub repository provides a simple script that can pull missing posts into Mastodon using the Mastodon API. FediFetcher has no further dependencies, and can be run as either a GitHub Action, as a scheduled cron job, or a pre-packaged container. Here is what FediFetcher can do:

1. It can pull missing remote replies to posts that are already on your server into your server. It can
   1. fetch missing replies to posts that users on your instance have already replied to,
   2. fetch missing replies to the most recent posts in your home timeline,
   3. fetch missing replies to your bookmarks.
2. It can also backfill profiles on your instance. In particular it can
   1. fetch missing recent posts from users that have recently appeared in your notifications,
   1. fetch missing recent posts from users that you have recently followed,
   2. fetch missing recent posts form users that have recently followed you,
   3. fetch missing recent posts form users that have recently sent you a follow request.

Each part of this script is fully configurable, and you can completely disable parts that you are not interested in.

FediFetcher will store posts it has already pulled in, as well as profiles it has already backfilled on disk, to prevent re-fetching the same info in subsequent executions.

**Be aware, that this script may run for a *very* long time.** This is particularly true, the first time this script runs, and/or if you enable all parts of this script. You should ensure that you take steps to prevent multiple overlapping executions of this script, as that will lead to unpleasant results.

## Setup

You can run FediFetcher either as a GitHub Action, as a scheduled cron job on your local machine/server, or from a pre-packed container.
### 1) Get the required access token:

Regardless of how you want to run FediFetcher, you must first get an access token:

1. In Mastodon go to Preferences > Development > New Application
   1. give it a nice name
   2. Enable the required scopes for your options. You could tick `read` and `admin:read:accounts`, or see below for a list of which scopes are required for which options.
   3. Save
   4. Copy the value of `Your access token`

### 2.1) Configure and run the GitHub Action

To run FediFetcher as a GitHub Action:

1. Fork this repository
2. Add your access token:
   1.  Go to Settings > Secrets and Variables > Actions
   2.  Click New Repository Secret
   3.  Supply the Name `ACCESS_TOKEN` and provide the Token generated above as Secret
3. Provide the required environment variables, to configure your Action:
   1. Go to Settings > Environments
   2. Click New Environment
   3. Provide the name `Mastodon`
   4. Add environment variables to configure your action as described below.
4. Finally go to the Actions tab and enable the action. The action should now automatically run approximately once every 10 min. 

Keep in mind that [the schedule event can be delayed during periods of high loads of GitHub Actions workflow runs](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule).

### 2.2) Run FediFetcher locally as a cron job

If you want to, you can of course also run FediFetcher locally as a cron job:

1. To get started, clone this repository.
2. Install requirements: `pip install -r requirements.txt`
3. Then simply run this script like so: `python find_posts.py --access-token=<TOKEN> --server=<SERVER>` etc. An example script can be found in the [`examples`](https://github.com/nanos/FediFetcher/tree/main/examples) folder (Read below, or run `python find_posts.py -h` to get a list of all options)

When using a cronjob, we are using file based locking to avoid multiple overlapping executions of the script. The timeout period for the lock can be configured using `--lock-hours`.

If you are running FediFetcher locally, my recommendation is to run it manually once, before turning on the cron job: The first run will be significantly slower than subsequent runs, and that will help you prevent overlapping during that first run.

### 2.3) Run FediFetcher from a container

FediFetcher is also available in a pre-packaged container, [FediFetcher](https://github.com/nanos/FediFetcher/pkgs/container/fedifetcher) - Thank you [@nikdoof](https://github.com/nikdoof).

1. Pull the container from `ghcr.io`, using Docker or your container tool of choice: `docker pull ghcr.io/nanos/FediFetcher:latest`
2. Run the container, passing the command line arguments like running the script directly: `docker run -it ghcr.io/nanos/FediFetcher:latest --access-token=<TOKEN> --server=<SERVER>`

The same rules for running this as a cron job apply to running the container: don't overlap any executions.

Persistent files are stored in `/app/artifacts` within the container, so you may want to map this to a local folder on your system.

An example Kubernetes CronJob for running the container is included in the [`examples`](https://github.com/nanos/FediFetcher/tree/main/examples) folder.

### Configuration options

FediFetcher has quite a few configuration options, so here is my quick configuration advice, that should probably work for most people (use the *Environment Variable Name* if you are running FediFetcher has a GitHub Action, otherwise use the *Command line flag*):

| Environment Variable Name | Command line flag | Recommended Value |
|:-------------------------|:-------------------|:-----------|
| -- | `--access-token` | (Your access token) |
| `MASTODON_SERVER`|`--server` | (your Mastodon server name) |
| `HOME_TIMELINE_LENGTH` | `--home-timeline-length` | `200` |
| `MAX_FOLLOWINGS` | `--max-followings` | `80` |
| `FROM_NOTIFICATIONS` | `--from-notifications` | `1` |

If you configure FediFetcher this way, it'll fetch missing remote replies to the last 200 posts in your home timeline. It'll additionally backfill profiles of the last 80 people you followed, and of every account who appeared in your notifications during the past hour.

#### Advanced Options

Please find the list of all configuration options, including descriptions, below:

| Environment Variable Name | Command line flag | Required? | Notes |
|:---------------------------------------------------|:----------------------------------------------------|-----------|:------|
| -- | `--access-token` | Yes | The access token. If using GitHub action, this needs to be provided as a Secret called  `ACCESS_TOKEN` |
|`MASTODON_SERVER`|`--server`|Yes|The domain only of your mastodon server (without `https://` prefix) e.g. `mstdn.thms.uk`. |
| `HOME_TIMELINE_LENGTH` | `--home-timeline-length` | No | Provide to fetch remote replies to posts in the API-Key owner's home timeline. Determines how many posts we'll fetch replies for. Recommended value: `200`.
| `REPLY_INTERVAL_IN_HOURS` | `--reply-interval-in-hours` | No | Provide to fetch remote replies to posts that have received replies from users on your own instance. Determines how far back in time we'll go to find posts that have received replies. Recommend value: `0` (disabled). Requires an access token with `admin:read:accounts`.
| `MAX_BOOKMARKS` | `--max-bookmarks` | No | Provide to fetch remote replies to any posts you have bookmarked. Determines how many of your bookmarks you want to get replies to. Recommended value: `80`. Requires an access token with `read:bookmarks` scope.
| `MAX_FOLLOWINGS` | `--max-followings` | No | Provide to backfill profiles for your most recent followings. Determines how many of your last followings you want to backfill. Recommended value: `80`.
| `MAX_FOLLOWERS` | `--max-followers` | No | Provide to backfill profiles for your most recent followers. Determines how many of your last followers you want to backfill. Recommended value: `80`.
| `MAX_FOLLOW_REQUESTS` | `--max-follow-requests` | No | Provide to backfill profiles for the API key owner's most recent pending follow requests. Determines how many of your last follow requests you want to backfill. Recommended value: `80`.
| `FROM_NOTIFICATIONS` | `--from-notifications` | No | Provide to backfill profiles of anyone mentioned in your recent notifications. Determines how many hours of notifications you want to look at. Requires an access token with `read:notifications` scope. Recommended value: `1`, unless you run FediFetcher less than once per hour.
| `REMEMBER_USERS_FOR_HOURS` | `--remember-users-for-hours` | No | How long between back-filling attempts for non-followed accounts? Defaults to `168`, i.e. one week.
| `HTTP_TIMEOUT` | `--http-timeout` | No | The timeout for any HTTP requests to the Mastodon API in seconds. Defaults to `5`.
| -- | `--lock-hours` | No | Determines after how many hours a lock file should be discarded. Not relevant when running the script as GitHub Action, as concurrency is prevented using a different mechanism. Recommended value: `24`.
| `ON_START` | `--on-start` | No | Optionally provide a callback URL that will be pinged when processing is starting. A query parameter `rid={uuid}` will automatically be appended to uniquely identify each execution. This can be used to monitor your script using a service such as healthchecks.io.
| `ON_DONE` | `--on-done` | No | Optionally provide a callback URL that will be called when processing is finished.  A query parameter `rid={uuid}` will automatically be appended to uniquely identify each execution. This can be used to monitor your script using a service such as healthchecks.io.
| `ON_FAIL` | `--on-fail` | No | Optionally provide a callback URL that will be called when processing has failed.  A query parameter `rid={uuid}` will automatically be appended to uniquely identify each execution. This can be used to monitor your script using a service such as healthchecks.io.

#### Required Access Token Scopes

 - For all actions, your access token must include these scopes:
   - `read:search`
   - `read:statuses` 
   - `read:accounts`
 - If you are supplying `REPLY_INTERVAL_IN_HOURS` / `--reply-interval-in-hours` you must additionally enable this scope:
   - `admin:read:accounts`
 - If you are supplying `MAX_FOLLOW_REQUESTS` / `--max-follow-requests` you must additionally enable this scope:
   - `read:follows`
 - If you are supplying `MAX_BOOKMARKS` / `--max-bookmarks` you must additionally enable this scope:
   - `read:bookmarks`
 - If you are supplying `FROM_NOTIFICATIONS` / `--from-notifications` you must additionally enable this scope:
   - `read:notifications`

## Acknowledgments

The original inspiration of this script, as well as parts of its implementation are taken from [Abhinav Sarkar](https://notes.abhinavsarkar.net/2023/mastodon-context). Thank you Abhinav!
