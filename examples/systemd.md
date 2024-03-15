1. Navigate to the directory `/opt`:
    ```bash
    cd /opt
    ```

2. Clone the FediFetcher repository from GitHub:
    ```bash
    git clone https://github.com/nanos/FediFetcher.git
    ```

3. Create a Python Virtual Environment named `fedifetcher`:
    ```bash
    python3 -m venv fedifetcher
    ```

4. Change to the FediFetcher directory:
    ```bash
    cd FediFetcher
    ```

5. Activate the virtual environment:
    ```bash
    source /opt/fedifetcher/bin/activate
    ```

6. Install the required Python packages from the `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```

7. Deactivate the virtual environment:
    ```bash
    deactivate
    ```

8. Configure FediFetcher according to the instructions provided at: [Configuration Options](https://github.com/nanos/FediFetcher?tab=readme-ov-file#configuration-options).

9. Run FediFetcher for the first time:
    ```bash
    /opt/fedifetcher/bin/python3 find_posts.py -c=artifacts/config.json
    ```

10. Create a systemd service file for FediFetcher:
    ```bash
    nano /etc/systemd/system/fedifetcher.service
    ```
    Paste the following content:
    ```
    [Unit]
    Description=FediFetcher Service
    After=network.target

    [Service]
    Type=simple
    User=root
    WorkingDirectory=/opt/FediFetcher
    ExecStart=/opt/fedifetcher/bin/python find_posts.py -c=artifacts/config.json

    [Install]
    WantedBy=multi-user.target
    ```

11. Create a systemd timer file for FediFetcher:
    ```bash
    nano /etc/systemd/system/fedifetcher.timer
    ```
    Paste the following content:
    ```
    [Unit]
    Description=FediFetcher Timer

    [Timer]
    OnCalendar=*-*-* *:*:00
    Persistent=true

    [Install]
    WantedBy=timers.target
    ```

    Explanation:
    - `OnCalendar`: This option defines when the timer should elapse. The format is `YYYY-MM-DD HH:MM:SS`. `*-*-* *:00:00` means every hour, `*-*-* *:*:00` means at the start of every minute. So, the timer will trigger every minute. [More informations](https://silentlad.com/systemd-timers-oncalendar-(cron)-format-explained).
    - `Persistent=true`: This option ensures that if the system is unable to trigger the timer at the specified time (e.g., if the system is asleep or powered off), it will run the missed events when the system is next awake or powered on.
    - `WantedBy=timers.target`: This specifies that the timer should be enabled when the `timers.target` is active, which is usually during system startup.

12. Reload the systemd daemon configuration:
    ```bash
    systemctl daemon-reload
    ```

13. Start the FediFetcher timer and enable it to start at every system boot:
    ```bash
    systemctl start --now fedifetcher.timer
    ```

With these steps, FediFetcher should be successfully set up on your system and automatically started to fetch posts regularly.