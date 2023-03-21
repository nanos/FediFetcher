# Pull missing responses into Mastodon

This GitHub repository provides a GitHub action that runs every 10 mins, doing the following:

1. It can [pull remote replies into your instance](https://blog.thms.uk/2023/03/pull-missing-responses-into-mastodon?utm_source=github), using the Mastodon API. That part itself has two parts:
   1. It gets remote replies to posts that users on your instance have already replied to during the last `REPLY_INTERVAL_IN_HOURS` hours, and adds them to your own server.
   2. It gets remote replies to the last `HOME_TIMELINE_LENGTH` posts from your home timeline, and adds them to your own server.
2. It can also [backfill posts](https://blog.thms.uk/2023/03/backfill-recently-followed-accounts?utm_source=github):
   1. from the last `MAX_FOLLOWINGS` users that you have followed.
   2. form the last `MAX_FOLLOWERS` users that have followed you.
   3. form the last `MAX_FOLLOW_REQUESTS` users that have sent you a follow request.

Each part can be disabled completely, and all of the parameters are configurable.

**Be aware, that this script may run for a long time, if these values are too high.** Experiment a bit with what works for you, by starting with fairly small numbers (maybe `HOME_TIMELINE_LENGTH = 200`, `REPLY_INTERVAL_IN_HOURS = 12`) and increase the numbers as you see fit.

For full context and discussion on why this is needed, read the following two blog posts: 

- The original announcement post: [Pull missing responses into Mastodon](https://blog.thms.uk/2023/03/pull-missing-responses-into-mastodon?utm_source=github)
- The announcement for v3.0.0: [Pull missing posts from recently followed accounts into Mastodon](https://blog.thms.uk/2023/03/backfill-recently-followed-accounts?utm_source=github)

## Setup

You can run this script either as a GitHub Action, as a scheduled cron job on your local machine, or from a pre-packed container.
### 1) Get the required access token:

Regardless of how you want to run this script, you must first get an access token:

1. In Mastodon go to Preferences > Development > New Application
   1. give it a nice name
   2. enable `read:search`, `read:statuses`, `read:follows`, and `admin:read:accounts`
   3. Save
   4. Copy the value of `Your access token`

### 2.1) Configure and run the GitHub Action

To run this script as a GitHub Action:

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

Keep in mind that [the schedule event can be delayed during periods of high loads of GitHub Actions workflow runs](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule), and that [scheduled workflows are automatically disabled when no repository activity has occurred in 60 days](https://github.com/nanos/mastodon_get_replies/issues/17).

### 2.2) Run this script locally as a cron job

If you want to, you can of course also run this script locally as a cron job:

1. To get started, clone this repository. (If you'd rather not clone the full repository, you can simply download the `find_posts.py` file, but don't forget to create a directory called `artifacts` in the same directory: The script expects this directory to be present, and stores information about posts it has already pushed into your instance in that directory, to avoid pushing the same posts over and over again.)
2. Then simply run this script like so: `python find_posts.py --access-token=<TOKEN> --server=<SERVER>` etc. (run `python find_posts.py -h` to get a list of all options)

When setting up your cronjob, we are using file based locking to avoid multiple overlapping executions of the script. The timeout period for the lock can be configured using `--lock-hours`.

If you are running this script locally, my recommendation is to run it manually once, before turning on the cron job: The first run will be significantly slower than subsequent runs, and that will help you prevent overlapping during that first run.

### 2.3) Run this script from a container

This script is also available in a pre-packaged container, [mastodon_get_replies](https://github.com/nanos/mastodon_get_replies/pkgs/container/mastodon_get_replies) - Thank you [@nikdoof](https://github.com/nikdoof).

1. Pull the container from `ghcr.io`, using Docker or your container tool of choice: `docker pull ghcr.io/nanos/mastodon_get_replies:latest`
2. Run the container, passing the command line arguments like running the script directly: `docker run -it ghcr.io/nanos/mastodon_get_replies:latest --access-token=<TOKEN> --server=<SERVER>`

The same rules for running this as a cron job apply to running the container, don't overlap any executions.

An example Kubernetes CronJob for running the container is included in the [`examples`](https://github.com/nanos/mastodon_get_replies/tree/main/examples) folder.

### Configuration options

Please see below for a list of configuration options.

| Environment Variable Name (if using GitHub Action) | Command line flag (if using cron, or the container) | Required? | Notes |
|:---------------------------------------------------|:----------------------------------------------------|-----------|:------|
| -- | `--access-token` | Yes | The access token. If using GitHub action, this needs to be provided as a Secret called  `ACCESS_TOKEN` |
|`MASTODON_SERVER`|`--server`|Yes|The domain only of your mastodon server (without `https://` prefix) e.g. `mstdn.thms.uk`. |
| `HOME_TIMELINE_LENGTH` | `--home-timeline-length` | No | Provide to fetch remote replies to posts in the API-Key owner's home timeline. Determines how many posts we'll fetch replies for. (An integer number, e.g. `200`)
| `REPLY_INTERVAL_IN_HOURS` | `--reply-interval-in-hours` | No | Provide to fetch remote replies to posts that have received replies from users on your own instance. Determines how far back in time we'll go to find posts that have received replies. (An integer number, e.g. `24`.) Requires an access token with `admin:read:accounts`
| `USER` | `--user` | See Notes | Required together with `MAX_FOLLOWERS` or `MAX_FOLLOWINGS`: The username of the user whose followers or followings you want to backfill (e.g. `michael` for the user `@michael@thms.uk`).
| `MAX_FOLLOWINGS` | `--max-followings` | No | Provide to backfill profiles for your most recent followings. Determines how many of your last followings you want to backfill. (An integer number, e.g. `80`. Ensure you also provide `USER`).
| `MAX_FOLLOWERS` | `--max-followers` | No | Provide to backfill profiles for your most recent followers. Determines how many of your last followers you want to backfill. (An integer number, e.g. `80`. Ensure you also provide `USER`).
| `MAX_FOLLOW_REQUESTS` | `--max-follow-requests` | No | Provide to backfill profiles for the API key owner's most recent pending follow requests. Determines how many of your last follow requests you want to backfill. (An integer number, e.g. `80`.). Requires an access token with `read:follows` scope.
| `HTTP_TIMEOUT` | `--http-timeout` | No | The timeout for any HTTP requests to the Mastodon API in seconds. Defaults to `5`.
| -- | `--lock-hours` | No | Determines after how many hours a lock file should be discarded. Not required when running the script as GitHub Action, as concurrency is prevented using a different mechanism.

#### Required Access Token Scopes

 - For all actions, your access token must include these scopes:
   - `read:search`
   - `read:statuses` 
 - If you are supplying `REPLY_INTERVAL_IN_HOURS` / `--reply-interval-in-hours` you must additionally enable this scope:
   - `admin:read:accounts`
 - If you are supplying `MAX_FOLLOW_REQUESTS` / `--max-follow-requests` you must additionally enable this scope:
   - `read:follows`

## Acknowledgments

This script is mostly taken from [Abhinav Sarkar](https://notes.abhinavsarkar.net/2023/mastodon-context), with just some additions and alterations. Thank you Abhinav!
