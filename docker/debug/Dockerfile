FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ssh-keygen -A \
    && useradd --uid 50000 --user-group --create-home --shell /bin/bash debugger \
    && usermod -p '*' debugger

COPY sshd_config /etc/ssh/sshd_config.d/debugger.conf
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
