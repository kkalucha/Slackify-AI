#!/bin/bash

echo Enter Slackify Username
read username
echo Enter Slackify Password
read password


export SLACKIFY_USERNAME=$username
export SLACKIFY_PASSWORD=$password

cd/tmp/
wget https://chromedriver.storage.googleapis.com/2.37/chromedriver_linux64.zip
unzip chromedriver_linux64.zip
sudo mv chromedriver /usr/bin/chromedriver

curl https://intoli.com/install-google-chrome.sh | bash
sudo mv /usr/bin/google-chrome-stable /usr/bin/google-chrome

sudo apt install python3-pip
pip install --upgrade pip
pip install -r requirements.txt

echo Setup Complete!
