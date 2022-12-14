# BUILD STAGE
FROM python:slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT [ "python3", "migrate.py" ]

CMD [ "python3", "migrate.py", "--help" ]