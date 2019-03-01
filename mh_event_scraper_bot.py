# INFORMATION
# Copyright Laxaria, 2018 - 2019
# 
# PURPOSE
# Scrapes the event page(s) for Monster Hunter World, parses them
# and formats them into a Reddit submission
#
# Version History
# Aug 14 2018 - Finalizing for live production
# Feb 02 2019 - Fixed some formatting issues for flavour text
# Mar 01 2019 - Updated some code 

import praw
from bs4 import BeautifulSoup
import requests

import re
from pprint import pprint as pp
import json
import datetime


SUBREDDIT = 'laxaria'
CONFIG = {
    'client_id': 'CLIENT ID HERE',
    'client_secret': 'CLIENT SECRET HERE',
    'username': 'USERNAME HERE',
    'password': 'PASSWORD HERE',
    'user_agent': 'USER AGENT HERE',
}

class MH_World_Event_Quest_Scraper_Bot():

    def __init__(self, config):
        reddit = praw.Reddit(client_id=config['client_id'],
                    client_secret=config['client_secret'],
                    username=config['username'],
                    password=config['password'],
                    user_agent=config['user_agent'])

        self.subreddit = reddit.subreddit(SUBREDDIT)

        self.dict_for_event_quest_data = {
            'PC': {},
            'CONSOLE': {}
        }
        self.HTML_TABLES = {
            'Kulve Taroth Siege': 1,
            'Event Quests': 2,
            'Challenge Quests': 3,
        }
    
    def parse_website(self, website, source_data_dict):
        response = requests.get(website)
        soup = BeautifulSoup(response.content, features="html.parser")

        # Identify Quest Types
        # MH Event Quests are split into KT Siege, Event, and Challenge
        # This picks out the tables
        # Then cleans the data to only get the needed table headers
        quest_types = soup.find_all('h4', class_='tableTitle')
        quest_types = [quest_type.text.split('\n')[0] for quest_type in quest_types]
        
        #Parse HTML Tables
        for quest_type in quest_types:
            _tmp_dict = {quest_type:{}}
            css_table_class_num = self.HTML_TABLES[quest_type]
            table = soup.find('table', class_=f'table{css_table_class_num}')
            table_rows = table.find_all('tr')
            for row in table_rows:
                # Skip rows containing little to no data
                if len(row) < 15:
                    continue
                
                # Some quest data is underneath a pop-up-hover
                # 'quest_data' seeks to get at this data which is in a list
                quest_data = row.find('div', class_='pop').find_all('li')

                quest_favour_text = ' '.join(row.find('p', class_='txt').text.splitlines())
                quest_favour_text = quest_favour_text.replace('update!Note:', 'update! Note:')

                available = row.find('td', class_='term current').text
                if re.search(r'\bAvailable\b', available):
                    quest_dict = {
                        f"quest_{table_rows.index(row)}" : {
                            "quest_title": row.find('div', class_='title').text.strip('\n'),
                            "level": row.find('td', class_='level').text,
                            "quest_flavour_text": quest_favour_text,
                            "locale": quest_data[0].find('span').text,
                            "requirements": quest_data[1].find('span').text.strip(),
                            "success condition": quest_data[2].find('span').text.strip(),
                            "available": 'Available'                   
                        }
                    }
                    _tmp_dict[quest_type].update(quest_dict)
        
            source_data_dict.update(_tmp_dict)
        
        # Get Quest Period

        current_time = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        quest_period_start = current_time
        quest_period_end = current_time + datetime.timedelta(days=7) - datetime.timedelta(seconds=1)

        source_data_dict.update({
            "time data": {
                "start date": quest_period_start.strftime("%Y-%m-%d %H-%M"),
                "end date": quest_period_end.strftime("%Y-%m-%d %H-%M"),
            }
        })

    def post_to_reddit(self):

        # Formatting submission to reddit

        body = []

        body_top = f'## Patch Notes \n\n' \
                   f'* [Most Recent Patch Notes (console)](http://monsterhunterworld.com/us/topics/update_ver/)\n' \
                   f'* [Game Announcements (PC)](https://steamcommunity.com/app/582010/announcements/)' \
                   f'\n\n' \
        
        body.append(body_top)

        for platform, platform_data in self.dict_for_event_quest_data.items():
            section_header = f'## Platform: {platform} \n\n'
            body.append(section_header)
            for quest_type, quest_data in platform_data.items():
                if quest_type == "time data":
                    continue
                if len(quest_data) == 0:
                    continue
                if platform == "PC":
                    section_header = f'### [{quest_type}](http://game.capcom.com/world/steam/us/schedule.html?utc=0) \n\n'
                    body.append(section_header)
                elif platform == "CONSOLE":
                    section_header = f'### [{quest_type}](http://game.capcom.com/world/us/schedule.html?utc=0) \n\n'
                    body.append(section_header)

                section_table = f'**Quest Name** | **Level** | **Locale** | **Requirements** | **Objective** | **Quest Flavor Text**\n' \
                                f':--:|:--:|:--:|:--:|:--:|:--:\n'
                body.append(section_table)
                for quest_number, quest_info in quest_data.items():
                    if len(quest_info) == 0:
                        continue
                    if quest_info['quest_title'] in ['Lessons of the Wild', 'The Proving', 'The Heart of the Nora']:
                        quest_info['quest_title'] = quest_info['quest_title'] + ' (PS4 Only)'
                    row_text = f"{quest_info['quest_title']}|{quest_info['level']}|{quest_info['locale']}|{quest_info['requirements']}|{quest_info['success condition']}|{quest_info['quest_flavour_text']}\n"
                    body.append(row_text)
                body.append('\n\n')
            body.append('\n\n')

        body.append('---\n\n')
        body.append(f'This was done automatically; expect errors\n\n')
        body.append(f'[Link to PC Event Quest Schedule](http://game.capcom.com/world/steam/us/schedule.html?utc=0)\n\n')
        body.append(f'[Link to PS4 & XBox One Event Quest Schedule](http://game.capcom.com/world/us/schedule.html?utc=0)\n\n')
        body.append('---\n\n')
        body.append('Bot created by /u/Laxaria | [Open Source](https://github.com/Laxaria/MH_Event_Quest_Scraper_Reddit_Bot)\n\n')
        submission = ''.join(body)
        print(submission)

        title = f"MHWorld Weekly Reset - {datetime.datetime.utcnow().strftime('%b %d, %Y')}"

        self.subreddit.submit(title, selftext=submission, send_replies=False)

   
    def main(self):
        WEBSITE_CONSOLE = "http://game.capcom.com/world/us/schedule.html?utc=0"
        WEBSITE_STEAM = "http://game.capcom.com/world/steam/us/schedule.html?utc=0"
        self.parse_website(WEBSITE_CONSOLE, self.dict_for_event_quest_data['CONSOLE'])
        self.parse_website(WEBSITE_STEAM, self.dict_for_event_quest_data['PC'])
        with open(f'{datetime.datetime.utcnow().strftime("%Y-%m-%d")}.json', "w") as open_file:
            json.dump(self.dict_for_event_quest_data, open_file, indent = 4)
        self.post_to_reddit()
        
if __name__ == '__main__':
    bot = MH_World_Event_Quest_Scraper_Bot(CONFIG)
    bot.main()
