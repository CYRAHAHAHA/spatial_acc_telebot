#Set up guide

#functions to add in and document

#Modularising Branch
1) cd C:\Users\User\Documents\GitHub\spatial_acc_telebot
2) Create python venv python -m venv .venv (Should be okay as long as >Python3.10)
3) pip install -r requirements.txt
4) cd C:\Users\User\Documents\GitHub\spatial_acc_telebot\backend
5) Add your own environment variables in .env (havent git ignore LOL)
6) Run python .\main.py
6) Follow instructions on the webpage to switch user (For e.g. Yirong's case, switch to YR)
7) Can press button to retrieve all stats about assets
8) MODULARISED because, auth and everyt else settled, refer to routes, just need run 
    @require_access_token("/fetch_assets_config") prior to putting your own route and function

1) Starting up a telebot

2) Authorization Call (dict: all the relevant clients)

3) Update Issues (int: GUID, str:ISSUE_ID, int: ISSUE_NAME)

4) Update Status (int: GUID, str:STATUS_NAME, str:STATUS_SET) - Yirong

5) Create Custom Fields - Yirong

6) Create Status Sets 

7) Create Categories

8) NLP function (telegram text to useful parameters) (preferably GUID and some kind of value parameter)

9) Frontend to customize all initial setting up of 
