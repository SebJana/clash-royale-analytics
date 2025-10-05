FROM alpine:3.20

RUN apk add --no-cache bash ca-certificates curl dcron mongodb-tools tzdata
RUN cp /usr/share/zoneinfo/Europe/Berlin /etc/localtime && echo "Europe/Berlin" > /etc/timezone

WORKDIR /app
COPY backup.sh /app/backup.sh
RUN chmod +x /app/backup.sh

CMD ["/bin/bash", "-c", "/app/backup.sh"]
