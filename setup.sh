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

sudo wget -N https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -P ~/
sudo dpkg -i --force-depends ~/google-chrome-stable_current_amd64.deb
sudo apt-get -f install -ydpkg -i --force-depends ~/google-chrome-stable_current_amd64.deb

echo Google Chrome installed!

sudo wget -N https://chromedriver.storage.googleapis.com/2.9/chromedriver_linux64.zip -P ~/
sudo unzip ~/chromedriver_linux64.zip -d ~/
sudo rm ~/chromedriver_linux64.zip
sudo mv -f ~/chromedriver /usr/local/share/
sudo chmod +x /usr/local/share/chromedriver
sudo ln -s /usr/local/share/chromedriver /usr/local/bin/chromedriver

echo ChromeDriver installed!

sudo apt install python3-pip
sudo pip3 install selenium
pip3 install --upgrade pip
pip3 install -r requirements.txt

echo Setup Complete!
