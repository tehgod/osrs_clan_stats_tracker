#!/bin/bash
git pull
docker stop skilling_gainz_bot
docker container rm skilling_gainz_bot
docker build -t skilling_gainz_bot_image .