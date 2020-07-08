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

wget -N https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -P ~/
dpkg -i --force-depends ~/google-chrome-stable_current_amd64.deb
apt-get -f install -ydpkg -i --force-depends ~/google-chrome-stable_current_amd64.deb

echo Google Chrome installed!

wget -N https://chromedriver.storage.googleapis.com/2.9/chromedriver_linux64.zip -P ~/
unzip ~/chromedriver_linux64.zip -d ~/
rm ~/chromedriver_linux64.zip
mv -f ~/chromedriver /usr/local/share/
chmod +x /usr/local/share/chromedriver
ln -s /usr/local/share/chromedriver /usr/local/bin/chromedriver

echo ChromeDriver installed!

sudo apt install python3-pip
pip3 install --upgrade pip
pip3 install -r requirements.txt


echo Setup Complete!
