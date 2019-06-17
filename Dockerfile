FROM python:3

ADD https://github.com/aptible/supercronic/releases/download/v0.1.9/supercronic-linux-amd64 /usr/local/bin/supercronic

RUN chmod 755 /usr/local/bin/supercronic

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY crontab ./

COPY *.py ./

CMD [ "/usr/local/bin/supercronic", "./crontab" ]
