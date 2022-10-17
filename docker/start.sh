#!/bin/sh

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

cd ./backend && flask run &

nginx -g "daemon off;"

