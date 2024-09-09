# FediFetcher for Mastodon

This GitHub repository provides a simple script that can pull missing posts into Mastodon using the Mastodon API. FediFetcher has no further dependencies, and can be run as either a GitHub Action, a scheduled cron job, or a pre-packaged container. Here is what FediFetcher can do:

1. It can pull missing remote replies to posts that are already on your server into your server. Specifically, it can
   1. fetch missing replies to posts that users on your instance have already replied to
   2. fetch missing replies to the most recent posts in your home timeline
   3. fetch missing replies to your bookmarks
   4. fetch missing replies to your favourites
   5. fetch missing replies to the most recent posts in your lists
2. It can also backfill profiles on your instance. In particular it can
   1. fetch missing posts from users that have recently appeared in your notifications
   2. fetch missing posts from users that you have recently followed
   3. fetch missing posts from users that have recently followed you
   4. fetch missing posts from users that have recently sent you a follow request
   5. fetch missing posts from users that have recently been added to your lists

Each part of this script is fully configurable and you can disable parts that you are not interested in.

FediFetcher will store posts and profiles it has already pulled in on disk, to prevent re-fetching the same info in subsequent executions.

**Be aware, that this script may run for a *very* long time.** This is particularly true for the first time this script runs and/or if you enable all parts of this script. You should ensure that you take steps to prevent multiple overlapping executions of this script, as that will lead to unpleasant results. There are detailed instructions for this below.

For detailed information on the how and why, please read the [FediFetcher for Mastodon page](https://blog.thms.uk/fedifetcher?utm_source=github).

## Supported servers

FediFetcher makes use of the Mastodon API. It'll run against any instance implementing this API, and whilst it was built for Mastodon, it's been [confirmed working against Pleroma](https://fed.xnor.in/objects/6bd47928-704a-4cb8-82d6-87471d1b632f) as well.

FediFetcher will pull in posts and profiles from any servers running the following software: 

- Servers that implement the Mastodon API: Mastodon, Pleroma, Akkoma, Pixelfed, Hometown, Iceshrimp, Iceshrimp.NET
- Servers that implement the Misskey API: Misskey, Calckey, Firefish, Foundkey, Sharkey
- Lemmy
- Peertube

## Setup

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

Once you have to your access token, there are multiple ways of running FediFetcher. These include, but aren't limited to:

1. [Running FediFetcher as a GitHub Action](./docs/github-actions.md)<br>
   Ideal if you don't have your own hardware, and/or have little experience running servers. This is all point and click within GitHub's interface.
2. [Running FediFetcher as a cron job](./docs/cron-job.md)<br>
   Ideal if you already have a linux device, and want to simply run FediFetcher on there.
3. [Running FediFetcher from a container](./docs/container.md)<br>
   Ideal if you are familiar with containers.
4. [Running FediFetcher as a systemd timer](./docs/systemd.md)<br>
   Ideal if you have a linux device somewhere, but don't like cron jobs.
5. Running FediFetcher as a Scheduled Task in Windows<br>
   Ideal if you are a Windows User and your main device is (almost) always running.

### Configuration options

FediFetcher has quite a few configuration options, so here is my quick configuration advice, that should probably work for most people:

> [!CAUTION]
>
> **Remove the `access-token` from the `config.json`** when running FediFetcher as GitHub Action. When running FediFetcher as GitHub Action **ALWAYS** [set the Access Token as an Action Secret](#to-run-fedifetcher-as-a-github-action).

```json
{
  "access-token": "Your access token",
  "server": "your.mastodon.server",
  "home-timeline-length": 200,
  "max-followings": 80,
  "from-notifications": 1
}
```

For full configuration options and the required access token scopes, please see the [FediFetcher Configuration Options Documentation](./docs/config.md).

## Acknowledgments

The original inspiration of this script, as well as parts of its implementation were taken from [Abhinav Sarkar](https://notes.abhinavsarkar.net/2023/mastodon-context). Thank you Abhinav!
