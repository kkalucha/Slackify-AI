#!/bin/bash

echo Enter Slackify Username
read username
echo Enter Slackify Password
read password


export SLACKIFY_USERNAME=$username
export SLACKIFY_PASSWORD=$password

sudo apt-get update
sudo apt update

sudo apt install python3-pip
pip3 install --upgrade pip
pip3 install -r requirements.txt

echo Setup Complete!
