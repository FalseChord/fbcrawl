#!/usr/bin/env bash
source ./env/bin/activate
python selenium/run.py

# for Linux 
# DATE = "$(date --date='7 days ago' '+%y%m%d')"

# for mac
DATE="$(date -v -7d '+%y%m%d')"

scrapy crawl fb -a lang="en" -o data/${DATE}/posts.csv
scrapy crawl comments -a lang="en" -o data/${DATE}/comments.csv
