# Running FediFetcher from a container

FediFetcher is also available in a pre-packaged container, [FediFetcher](https://github.com/nanos/FediFetcher/pkgs/container/fedifetcher) - Thank you [@nikdoof](https://github.com/nikdoof).

1. Pull the container from `ghcr.io`, using Docker or your container tool of choice: `docker pull ghcr.io/nanos/fedifetcher:latest`
2. Run the container, passing the configurations options as command line arguments: `docker run -it ghcr.io/nanos/fedifetcher:latest --access-token=<TOKEN> --server=<SERVER>`, or using Environment variables.

See the [configuration options docs](./config.md) for full details on how to configure FediFetcher.

> [!IMPORTANT]
>
> The same rules for running this as a cron job apply to running the container: don't overlap any executions.

Persistent files are stored in `/app/artifacts` within the container, so you may want to map this to a local folder on your system.

An [example Kubernetes CronJob](../examples/k8s-cronjob.md) for running the container is included in the `examples` folder.

An [example Docker Compose Script](../examples/docker-compose.yaml) for running the container periodically is included in the `examples` folder.

For other options of running FediFetcher see the [README file](../README.md).