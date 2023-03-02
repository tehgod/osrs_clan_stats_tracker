FROM python:3

ENV discord_webhook=""

ADD main.py /
ADD config ./config /
ADD requirements.txt /

RUN pip install -r requirements.txt
RUN mkdir daily_stats
RUN mkdir daily_stats_comparisons

CMD [ "python", "-u", "./main.py"]