FROM python:3.12-alpine

RUN apk add --no-cache bash tini

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x create_cron.sh

ENTRYPOINT ["/sbin/tini", "--", "./create_cron.sh"]