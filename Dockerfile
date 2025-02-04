FROM python:3.11-alpine
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
RUN mkdir -p /app/artifacts/
COPY ./src/nanos/fedi_fetcher/find_posts.py /app/
ENTRYPOINT ["python", "find_posts.py"]
