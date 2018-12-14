
# coding: utf-8

# In[1]:


from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC 
from selenium.common.exceptions import TimeoutException
import json
import pandas as pd
import math
import itertools
from tqdm import tqdm
import numpy as np


# In[2]:


# Clean the offense dataframe
def clean_offense(offense, week):
    team_name = offense[0][0].replace(' Box Score', '')
    offense.columns = offense.iloc[2]
    names = [list(y) for x, y in itertools.groupby(map(lambda x: '|' if type(x) == float else x ,list(offense.iloc[2])), lambda z: z == '|') if not x]
    offense_tags = ['', 'Passing ', 'Rushing ', 'Receiving ', 'Misc ', '']
    names = list(map(lambda x: list(map(lambda y: x[1] + y, x[0])) ,zip(names, offense_tags)))
    columns = []
    sep = ''
    for sublist in names:
        if(sep != ''):
            columns.append(sep)
        for item in sublist:
            columns.append(item)
        sep = '|'
    offense.columns = columns
    offense = offense.drop('|', axis=1).drop([0,1,2])
    offense['PLAYER'] = list(map(lambda info: info.split(',')[0].replace('*', '') if type(info) != float else '', offense['PLAYER, TEAM POS']))
    offense['TEAM'] = list(map(lambda info: str(info.split(',')[1].split(u'\xa0')[0]).strip() if type(info) != float else '', offense['PLAYER, TEAM POS']))
    offense['POS'] = list(map(lambda info: str(info.split(',')[1].split(u'\xa0')[1]).strip() if type(info) != float else '', offense['PLAYER, TEAM POS']))
    offense['OPP'] = list(map(lambda x: x.replace('*', '').strip() if type(x) != float else '', offense['OPP']))
    offense = offense.drop('PLAYER, TEAM POS', axis=1)
    offense['STATUS ET'] = list(map(lambda x: str(x.replace(u'\xbb', '')).strip() if type(x) != float else '', offense['STATUS ET']))
    offense['FANTASY TEAM'] = team_name
    offense['WEEK'] = week
    l = len(offense.columns)
    fields = [offense.columns[l-1], offense.columns[l-2]] + [offense.columns[0]] + list(offense.columns[l-5:l-3]) + list(offense.columns[1:l-5])
    offense = offense[fields]
    
    return(offense)


# In[3]:


def clean_defense(defense, team, week):
    names = list(filter(lambda x: str(x) != 'nan', list(defense.iloc[1])))
    defense = defense.drop([0,1]).drop(defense.columns[4], axis=1).drop(defense.columns[12], axis=1)
    defense.columns = names
    defense['FANTASY TEAM'] = team
    defense['WEEK'] = week
    defense['STATUS ET'] = list(map(lambda x: str(x.replace(u'\xbb', '')).strip() if type(x) != float else '', defense['STATUS ET']))
    defense['POS'] = 'D/ST'
    defense['PLAYER'] = list(map(lambda x: x.split(u'\xa0')[0], defense['PLAYER, TEAM POS']))
    defense = defense[['WEEK', 'FANTASY TEAM', 'SLOT', 'PLAYER', 'POS'] + list(defense.columns)[2:len(defense.columns)-4]]
    return(defense)


# In[4]:


def clean_kicking(kicking, team, week):
    names = list(filter(lambda x: str(x) != 'nan', list(kicking.iloc[1])))
    kicking = kicking.drop([0,1]).drop([4,10], axis=1)
    kicking.columns = names
    kicking['PLAYER'] = list(map(lambda x: x.split(',')[0], kicking['PLAYER, TEAM POS']))
    kicking['TEAM'] = list(map(lambda x: str(x.split(',')[1].split(u'\xa0')[0]).strip(), kicking['PLAYER, TEAM POS']))
    kicking['POS'] = 'K'
    kicking['STATUS ET'] = list(map(lambda x: str(x.replace(u'\xbb', '')).strip() if type(x) != float else '', kicking['STATUS ET']))
    kicking['WEEK'] = week
    kicking['FANTASY TEAM'] = team
    kicking = kicking[['WEEK', 'FANTASY TEAM', 'SLOT', 'PLAYER', 'TEAM', 'POS'] + list(kicking.columns)[2:len(kicking.columns)-5]]
    return(kicking)


# In[5]:


# Get all the stats for the week
def get_stats(week):
    offenses = []
    defenses = []
    kickers = []
    for url in score_urls:
        try:
            browser.get(url)
            WebDriverWait(browser, timeout).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="content"]/div/div[4]/div/div/div/div[5]')))
        except TimeoutException:
            print("Timed out waiting for page to laod")
            browser.quit()
            
        home_team = browser.find_element_by_xpath('//*[@id="teamInfos"]/div[1]/div/div[2]/div[1]/b').text
        away_team = browser.find_element_by_xpath('//*[@id="teamInfos"]/div[2]/div/div[2]/div[1]/b').text

        home_tables = pd.read_html(browser.find_element_by_xpath('//*[@id="content"]/div/div[4]/div/div/div/div[5]').get_attribute("innerHTML"))
        away_tables = pd.read_html(browser.find_element_by_xpath('//*[@id="content"]/div/div[4]/div/div/div/div[6]').get_attribute("innerHTML"))
        offenses.append(clean_offense(home_tables[0], week))
        offenses.append(clean_offense(away_tables[0], week))
        defenses.append(clean_defense(home_tables[2], home_team, week))
        defenses.append(clean_defense(away_tables[2], away_team, week))
        kickers.append(clean_kicking(home_tables[1], home_team, week))
        kickers.append(clean_kicking(away_tables[1], away_team, week))
    offenses = pd.concat(offenses)
    defenses = pd.concat(defenses)
    kickers = pd.concat(kickers)
    return([offenses, defenses, kickers])
    


# In[6]:


# Set browser options for incognito (for consistency) and headless
option = webdriver.ChromeOptions()
option.add_argument("incognito")
option.add_argument("headless")


# In[7]:


# Load league configs ('May need to change directory')
configs = json.load(open('config.json'))


# In[8]:


# Log in to espn
browser = webdriver.Chrome(executable_path='/Users/datalabs1/Downloads/chromedriver', options=option)
timeout = 20
try:
    browser.get("https://www.espn.com/login")
    WebDriverWait(browser, timeout).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="disneyid-iframe"]')))
    browser.switch_to.frame(browser.find_element_by_xpath('//*[@id="disneyid-iframe"]'))
except TimeoutException:
    print("Timed out waiting for page to load")
    browser.quit()
username_text_box = browser.find_element_by_xpath('//*[@id="did-ui-view"]/div/section/section/form/section/div[1]/div/label/span[2]/input')
username_text_box.send_keys(configs['username'])
password_text_box = browser.find_element_by_xpath('//*[@id="did-ui-view"]/div/section/section/form/section/div[2]/div/label/span[2]/input')
password_text_box.send_keys(configs['password'])
login = browser.find_element_by_xpath('//*[@id="did-ui-view"]/div/section/section/form/section/div[3]/button')
login.click()


# In[9]:


# Get the weeks that have been played (Only regular season for now)
weeks_path = '//*[@id="content"]/div/div[4]/div/div/div[2]/div[4]/a[contains(@title, "Week")]'
try:
    browser.get("http://games.espn.com/ffl/scoreboard?leagueId={}&matchupPeriodId=1".format(configs['league_id']))
    WebDriverWait(browser, timeout).until(EC.visibility_of_element_located((By.XPATH, weeks_path)))
except TimeoutException:
    print("Timed out waiting for page to load")
    browser.quit()

weeks = browser.find_elements_by_xpath(weeks_path)
weeks = ['1'] + list(map(lambda x: str(x.text), weeks))


# In[10]:


# Collect stats for every week and combine
stats = []
for week in tqdm(weeks):
    score_path = '//*[@class="ptsBased matchup"]/tbody/tr[3]/td/div/a[2]'
    try:
        browser.get("http://games.espn.com/ffl/scoreboard?leagueId={}&matchupPeriodId={}".format(configs['league_id'], week))
        WebDriverWait(browser, timeout).until(EC.visibility_of_element_located((By.XPATH, score_path)))
    except TimeoutException:
        print("Timed out waiting for page to load")
        browser.quit()

    score_urls = list(map(lambda x: str(x.get_attribute('href')), browser.find_elements_by_xpath(score_path)))
    stats.append(get_stats(week))
offense = pd.concat([x[0] for x in stats])
defense = pd.concat([x[1] for x in stats])
kicking = pd.concat([x[2] for x in stats])

writer = pd.ExcelWriter('FantasyStats.xlsx', engine='xlsxwriter')

offense.to_excel(writer, sheet_name = 'Offense')
defense.to_excel(writer, sheet_name = 'Defense')
kicking.to_excel(writer, sheet_name = 'Kicking')

writer.save()

