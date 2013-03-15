#!/bin/bash

ARGS=$@

# Translate script exit into SIGINT for all children
trap 'kill -INT $(jobs -p)' EXIT
bin/uwsgi  parts/uwsgi/uwsgi.xml $ARGS
