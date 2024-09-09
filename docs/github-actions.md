# Running FediFetcher as a GitHub Action

Running FediFetcher as a GitHub Action is probably the simplest way of running FediFetcher if you don't have Linux admin experience. You do not need any 'server' or other hardware to use GitHub Actions, as everything runs on GitHub's servers.

The disadvantage is that you have limited control over this, and that you cannot run FediFetcher more frequently than every 10/15 minutes.

To run FediFetcher as a GitHub ActionL

1. [Fork this repository](https://github.com/nanos/FediFetcher/fork)
2. Add your [access token](../README.md#1-get-the-required-access-token) as a Secret:
   1.  Go to Settings > Secrets and Variables > Actions
   2.  Click New Repository Secret
   3.  Supply the Name `ACCESS_TOKEN` and provide the Token generated above as Secret
3. Create a file called `config.json` with your [configuration options](./config.md) in the repository root. **Do NOT include the Access Token in your `config.json`!**
4. Finally go to the Actions tab and enable the action. The action should now automatically run approximately once every 10 min.

> [!NOTE]
>
> Keep in mind that [the schedule event can be delayed during periods of high loads of GitHub Actions workflow runs](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule).

For other options of running FediFetcher see the [README file](../README.md).
