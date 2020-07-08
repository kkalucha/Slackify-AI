#!/bin/bash

echo Enter Slackify Username
read username
echo Enter Slackify Password
read password


export SLACKIFY_USERNAME=$username
export SLACKIFY_PASSWORD=$password

sudo apt-get update
sudo apt update
sudo apt -y dist-upgrade
sudo apt-get install -y openjdk-8-jre-headless xvfb libxi6 libgconf-2-4 zip

sudo curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add
sudo echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
sudo apt-get -y update
sudo apt-get -y install google-chrome-stable

echo Google Chrome installed!

wget -N https://chromedriver.storage.googleapis.com/79.0.3945.36/chromedriver_linux64.zip -P ~/
unzip ~/chromedriver_linux64.zip -d ~/
rm ~/chromedriver_linux64.zip
sudo mv -f ~/chromedriver /usr/local/bin/chromedriver
sudo chown root:root /usr/local/bin/chromedriver
sudo chmod 0755 /usr/local/bin/chromedriver

echo ChromeDriver installed!

sudo apt-get --fix-broken-install
sudo apt install python3-pip
pip3 install --upgrade pip
pip3 install -r requirements.txt

echo Setup Complete!
