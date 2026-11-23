FROM python:3.12-slim-trixie@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jre-headless curl unzip git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL --retry 3 https://github.com/ontop/ontop/releases/download/ontop-5.5.0/ontop-cli-5.5.0.zip -o /tmp/ontop.zip \
    && echo '430dff312e68e8ad41d26e6113160ca2365c28c4fe911926193000a33299458f  /tmp/ontop.zip' | sha256sum -c - \
    && mkdir /opt/ontop && unzip -q /tmp/ontop.zip -d /opt/ontop \
    && chmod +x /opt/ontop/ontop && rm /tmp/ontop.zip
RUN curl -fsSL --retry 3 https://repo.maven.apache.org/maven2/org/postgresql/postgresql/42.7.8/postgresql-42.7.8.jar -o /opt/ontop/jdbc/postgresql-42.7.8.jar \
    && echo '2a32a9dcbc42d67a50ad3a0de5efd102c8d2be46720045f2cbd6689f160ab7c7  /opt/ontop/jdbc/postgresql-42.7.8.jar' | sha256sum -c -
WORKDIR /project
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 MVP_RUNTIME_MODE=docker
ENTRYPOINT ["python", "-m", "mvp"]
CMD ["serve"]
