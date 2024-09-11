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

There are many way to configure and run FediFetcher, including as GitHub Action, cron job, container, or even from a Windows computer using the Task Schedule. None of these require CLI/SSH access to your Mastodon server.

For full details please [see the Documentation](https://github.com/nanos/FediFetcher/wiki).

## Alternatives

If you don't want to run a python script, but still want to see missing replies in your timeline, the Chrome or FireFox extension [Substitoot](https://substitoot.kludge.guru) might be helpful.

## Contribute

Thank you for wanting to contribute to FediFetcher! Please have a look at our [Contributing to FediFetcher Guide](https://github.com/nanos/FediFetcher/wiki/Contribute-To-FediFetcher) to get started.

## Acknowledgments

The original inspiration of this script, as well as parts of its implementation were taken from [Abhinav Sarkar](https://notes.abhinavsarkar.net/2023/mastodon-context). Thank you Abhinav!
