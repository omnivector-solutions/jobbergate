#!/usr/bin/env bash

sleep 10
createsuperuser --email="$EMAIL" --password="$PASSWORD" --full-name=admin
