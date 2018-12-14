
from selenium import webdriver # To interact with browser
from selenium.webdriver.common.by import By # For waiting for page to load
from selenium.webdriver.support.ui import WebDriverWait # For waiting for page to load
from selenium.webdriver.support import expected_conditions as EC # For waiting for page to load
from selenium.common.exceptions import TimeoutException # For waiting for page to load
import json # for loading configs
import pandas as pd # for dataframes
import math # for checking for nan
import itertools # for list manipulations
from tqdm import tqdm # for adding a progress bar to loops

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
    offense['TEAM'] = list(map(lambda info: str(info.split(',')[1].split(u'\xa0')[0].decode('ascii')).strip() if type(info) != float else '', offense['PLAYER, TEAM POS']))
    offense['POS'] = list(map(lambda info: str(info.split(',')[1].split(u'\xa0')[1].decode('ascii')).strip() if type(info) != float else '', offense['PLAYER, TEAM POS']))
    offense['OPP'] = list(map(lambda x: x.replace('*', '').strip() if type(x) != float else '', offense['OPP']))
    offense = offense.drop('PLAYER, TEAM POS', axis=1)
    offense['STATUS ET'] = list(map(lambda x: str(x.replace(u'\xbb', '')).strip() if type(x) != float else '', offense['STATUS ET']))
    offense['FANTASY TEAM'] = team_name
    offense['WEEK'] = week
    l = len(offense.columns)
    fields = [offense.columns[l-1], offense.columns[l-2]] + [offense.columns[0]] + list(offense.columns[l-5:l-3]) + list(offense.columns[1:l-5])
    offense = offense[fields]
    
    return(offense)

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

        home_tables = pd.read_html(browser.find_element_by_xpath('//*[@id="content"]/div/div[4]/div/div/div/div[5]').get_attribute("innerHTML"))
        away_tables = pd.read_html(browser.find_element_by_xpath('//*[@id="content"]/div/div[4]/div/div/div/div[6]').get_attribute("innerHTML"))
        offenses.append(clean_offense(home_tables[0], week))
        offenses.append(clean_offense(away_tables[0], week))
    offenses = pd.concat(offenses)
    return([offenses, defenses, kickers])
    
# Set browser options for incognito (for consistency) and headless
option = webdriver.ChromeOptions()
option.add_argument("incognito")
option.add_argument("headless")

# Load league configs ('May need to change directory')
configs = json.load(open('config.json'))

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
# defense = pd.concat([x[1] for x in stats])
# kicking = pd.concat([x[2] for x in stats])

print(offense)
