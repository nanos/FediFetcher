# FediFetcher for Mastodon

This GitHub repository provides a simple script that can pull missing posts into Mastodon using the Mastodon API. FediFetcher has no further dependencies, and can be run as either a GitHub Action, as a scheduled cron job, or a pre-packaged container. Here is what FediFetcher can do:

1. It can pull missing remote replies to posts that are already on your server into your server. Specifically, it can
   1. fetch missing replies to posts that users on your instance have already replied to,
   2. fetch missing replies to the most recent posts in your home timeline,
   3. fetch missing replies to your bookmarks.
   4. fetch missing replies to your favourites.
2. It can also backfill profiles on your instance. In particular it can
   1. fetch missing posts from users that have recently appeared in your notifications,
   1. fetch missing posts from users that you have recently followed,
   2. fetch missing posts form users that have recently followed you,
   3. fetch missing posts form users that have recently sent you a follow request.

Each part of this script is fully configurable, and you can completely disable parts that you are not interested in.

FediFetcher will store posts and profiles it has already pulled in on disk, to prevent re-fetching the same info in subsequent executions.

**Be aware, that this script may run for a *very* long time.** This is particularly true, the first time this script runs, and/or if you enable all parts of this script. You should ensure that you take steps to prevent multiple overlapping executions of this script, as that will lead to unpleasant results. There are detailed instructions for this below.

For detailed information on the how and why, please read the [FediFetcher for Mastodon page](https://blog.thms.uk/fedifetcher?utm_source=github).

## Supported servers

FediFetcher makes use of the Mastodon API. It'll run against any instance implementing this API, and whilst it was built for Mastodon, it's been [confirmed working against Pleroma](https://fed.xnor.in/objects/6bd47928-704a-4cb8-82d6-87471d1b632f) as well.

FediFetcher will pull in posts and profiles from any servers running the following software: Mastodon, Pleroma, Akkoma, Pixelfed, Hometown, Misskey, Firefish (Calckey), Foundkey, and Lemmy.

## Setup

You can run FediFetcher either as a GitHub Action, as a scheduled cron job on your local machine/server, or from a pre-packed container.

### 1) Get the required access token:

Regardless of how you want to run FediFetcher, you must first get an access token:

#### If you are an Admin on your instance

1. In Mastodon go to Preferences > Development > New Application
   1. Give it a nice name
   2. Enable the required scopes for your options. You could tick `read` and `admin:read:accounts`, or see below for a list of which scopes are required for which options.
   3. Save
   4. Copy the value of `Your access token`

#### If you are not an Admin on your Instance

1. Go to [GetAuth for Mastodon](https://getauth.thms.uk?scopes=read&client_name=FediFetcher)
2. Type in your Mastodon instance's domain
3. Copy the token.

### 2) Configure and run FediFetcher

Run FediFetcher as a GitHub Action, a cron job, or a container:

#### To run FediFetcher as a GitHub Action:

1. Fork this repository
2. Add your access token:
   1.  Go to Settings > Secrets and Variables > Actions
   2.  Click New Repository Secret
   3.  Supply the Name `ACCESS_TOKEN` and provide the Token generated above as Secret
3. Create a file called `config.json` with your [configuration options](#configuration-options) in the repository root. **Do NOT include the Access Token in your `config.json`!**
4. Finally go to the Actions tab and enable the action. The action should now automatically run approximately once every 10 min.

> **Note**
>
> Keep in mind that [the schedule event can be delayed during periods of high loads of GitHub Actions workflow runs](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule).

#### To run FediFetcher as a cron job:

1. Clone this repository.
2. Install requirements: `pip install -r requirements.txt`
3. Create a `json` file with [your configuration options](#configuration-options). You may wish to store this in the `./artifacts` directory, as that directory is `.gitignore`d
4. Then simply run this script like so: `python find_posts.py -c=./artifacts/config.json`.

If desired, all configuration options can be provided as command line flags, instead of through a JSON file. An [example script](./examples/FediFetcher.sh) can be found in the `examples` folder.

When using a cronjob, we are using file based locking to avoid multiple overlapping executions of the script. The timeout period for the lock can be configured using `lock-hours`.

> **Note**
>
> If you are running FediFetcher locally, my recommendation is to run it manually once, before turning on the cron job: The first run will be significantly slower than subsequent runs, and that will help you prevent overlapping during that first run.

#### To run FediFetcher from a container:

FediFetcher is also available in a pre-packaged container, [FediFetcher](https://github.com/nanos/FediFetcher/pkgs/container/fedifetcher) - Thank you [@nikdoof](https://github.com/nikdoof).

1. Pull the container from `ghcr.io`, using Docker or your container tool of choice: `docker pull ghcr.io/nanos/fedifetcher:latest`
2. Run the container, passing the configurations options as command line arguments: `docker run -it ghcr.io/nanos/fedifetcher:latest --access-token=<TOKEN> --server=<SERVER>`

> **Note**
>
> The same rules for running this as a cron job apply to running the container: don't overlap any executions.

Persistent files are stored in `/app/artifacts` within the container, so you may want to map this to a local folder on your system.

An [example Kubernetes CronJob](./examples/k8s-cronjob.yaml) for running the container is included in the `examples` folder.

An [example Docker Compose Script](./examples/docker-compose.yaml) for running the container periodically is included in the `examples` folder.

#### To run FediFetcher with systemd-timer:

See [systemd.md](./examples/systemd.md)

### Configuration options

FediFetcher has quite a few configuration options, so here is my quick configuration advice, that should probably work for most people:

> **Warning**
>
> **Do NOT** include your `access-token` in the `config.json` when running FediFetcher as GitHub Action. When running FediFetcher as GitHub Action **ALWAYS** [set the Access Token as an Action Secret](#to-run-fedifetcher-as-a-github-action).

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

#### Advanced Options

Please find the list of all configuration options, including descriptions, below:

Option | Required? | Notes |
|:----------------------------------------------------|-----------|:------|
|`log-level` | No | The severity of messages to log. Possible values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. Defaults to `DEBUG`. |
|`access-token` | Yes | The access token. If using GitHub action, this needs to be provided as a Secret called  `ACCESS_TOKEN`. If running as a cron job or a container, you can supply this option as array, to [fetch posts for multiple users](https://blog.thms.uk/2023/04/muli-user-support-for-fedifetcher) on your instance. |
|`server`|Yes|The domain only of your mastodon server (without `https://` prefix) e.g. `mstdn.thms.uk`. |
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
| `remember-users-for-hours` | No | How long between back-filling attempts for non-followed accounts? Defaults to `168`, i.e. one week.
| `remember-hosts-for-days` | No | How long should FediFetcher cache host info for? Defaults to `30`.
| `http-timeout` | No | The timeout for any HTTP requests to the Mastodon API in seconds. Defaults to `5`.
| `lock-hours` | No | Determines after how many hours a lock file should be discarded. Not relevant when running the script as GitHub Action, as concurrency is prevented using a different mechanism. Recommended value: `24`.
| `lock-file` | No | Location for the lock file. If not specified, will use `lock.lock` under the state directory. Not relevant when running the script as GitHub Action.
| `state-dir` | No | Directory storing persistent files, and the default location for lock file. Not relevant when running the script as GitHub Action.
| `on-start` | No | Optionally provide a callback URL that will be pinged when processing is starting. A query parameter `rid={uuid}` will automatically be appended to uniquely identify each execution. This can be used to monitor your script using a service such as healthchecks.io.
| `on-done` | No | Optionally provide a callback URL that will be called when processing is finished.  A query parameter `rid={uuid}` will automatically be appended to uniquely identify each execution. This can be used to monitor your script using a service such as healthchecks.io.
| `on-fail` | No | Optionally provide a callback URL that will be called when processing has failed.  A query parameter `rid={uuid}` will automatically be appended to uniquely identify each execution. This can be used to monitor your script using a service such as healthchecks.io.

### Multi User support

If you wish to [run FediFetcher for multiple users on your instance](https://blog.thms.uk/2023/04/muli-user-support-for-fedifetcher?utm_source=github), you can supply the `access-token` as an array, with different access tokens for different users. That will allow you to fetch replies and/or backfill profiles for multiple users on your account.

This is only supported when running FediFetcher as cron job, or container. Multi-user support is not available when running FediFetcher as GitHub Action.

### Required Access Token Scopes

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

## Acknowledgments

The original inspiration of this script, as well as parts of its implementation are taken from [Abhinav Sarkar](https://notes.abhinavsarkar.net/2023/mastodon-context). Thank you Abhinav!
