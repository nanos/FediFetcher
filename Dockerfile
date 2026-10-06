FROM python:3.14-alpine
LABEL org.opencontainers.image.source=https://github.com/nanos/FediFetcher \
      org.opencontainers.image.description="Pull missing posts into Mastodon" \
      org.opencontainers.image.licenses=MIT
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
RUN mkdir -p /app/artifacts/
COPY ./find_posts.py /app/
COPY ./fedifetcher /app/fedifetcher
ARG VERSION=dev
ARG REVISION=unknown
LABEL org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$REVISION
ENTRYPOINT ["python", "find_posts.py"]
