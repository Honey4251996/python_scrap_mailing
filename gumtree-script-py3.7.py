# -*- coding: utf-8 -*-
#!/usr/bin/python3.7
import time
import os
import json
import csv
import random
import requests
import email
import smtplib
import datetime
import string
import re
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from difflib import SequenceMatcher
from http.cookiejar import CookieJar
import html as HTMLParser
from playsound import playsound




def email_notification(text,title,profile_email,item_type):
    global email_server, server_email_id
    print ("Sending Notification")
    msg = email.message_from_bytes(text)
    
    msg['To'] = profile_email
    msg['From'] = server_email_id
    msg['Subject'] = "Gumtree Latest < %s > Item : %s"%(item_type,title.decode('utf-8'))
    print (msg['Subject'])

    email_server.sendmail(server_email_id, profile_email, msg.as_string())
    time.sleep(2)
    
def is_day_time():
    timestamp = datetime.datetime.now().time()
    start = datetime.time(6, 30)
    end = datetime.time(22,30)
    return (start <= timestamp <= end)

def construct_json_url(profile_url):
    global page_size
    SORT_TYPES = {'rank':'rank', 'price_asc':'price_asc', 'price_desc':'price_desc', 'closest':'nearest'}
    PRICE_TYPES = {'fixed':'FIXED', 'negotiable':'NEGOTIABLE', 'free':'GIVE_AWAY', 'swap-trade':'SWAP_TRADE', 'driveaway':'DRIVE_AWAY'}
    OFFER_TYPES = {'offering':'OFFER', 'wanted':'WANTED'}
                   
    slug = list(filter(None,[s.strip() for s in profile_url.split('/')]))[-1].split('?')[0]
    search_filters = parse_qs(urlparse(profile_url).query)
    
    catID,rad = '',''
    if 'c' in slug:
        catID = slug[slug.find('c')+1:slug.find('l')]
    if 'r' in slug:
        locID = slug[slug.find('l')+1:slug.find('r')]
        rad = slug[slug.find('r')+1:]
    else:
        locID = slug[slug.find('l')+1:]
    
    query_params = {'locationId' : locID,
                    'locationStr' : '',
                    'pageSize' : page_size,
                    'previousCategoryId' : '',
                    'sortByName':'date'
                    }
    if rad:
        query_params['radius']=rad
    if catID:
        query_params['categoryId']=catID
    
    if 'price-type' in search_filters.keys():
        query_params['priceType'] = PRICE_TYPES[search_filters['price-type'][0]]
    
    if 'ad' in search_filters.keys():
        query_params['offerType'] = OFFER_TYPES[search_filters['ad'][0]]
      
    if 'sort' in search_filters.keys():
        query_params['sortByName'] = SORT_TYPES[search_filters['sort'][0]]

    json_url = 'https://www.gumtree.com.au/ws/search.json?' + urlencode(query_params)    
    return json_url

def scrape_new_results(json_url,page_no):
    global opener,headers,base_url,page_size
    page_url = json_url+'&pageNum=%d'%(page_no)
    resp = opener.get(page_url,headers=headers).text.encode('utf-8')
    json_obj = json.loads(resp)
    results = json_obj['data']['results']
    new_results = {}
    if results['resultList']:
        total_count = results['numberFound']
        keys=['title','url','age','description','priceText','location','distance','isFree']
        for result in results['resultList']:
            newitem={}
            for key in keys:
                try:
                    newitem[key]=result[key]
                except:
                    newitem[key]=''
            newitem['url'] = urljoin(base_url, newitem['url'])
            new_results[result['id']] = newitem
    return new_results
            
def save_to_database(profile_id,profile_database):
    db = json.dumps(profile_database)
    profile_db_path = 'database/profile-%s.json'%(profile_id)
    with open(profile_db_path,'w') as dbfile:
        dbfile.write(db)
    
def read_input_csv(csv_file_path):
    profiles=[]
    if os.path.isfile(csv_file_path):
        with open(csv_file_path) as csvfile:
            for line in csv.reader(csvfile, quotechar='"', delimiter=',', quoting=csv.QUOTE_ALL, skipinitialspace=True):
                if line:
                    profiles.append(line)
    return profiles

def read_profile_database(profile_id):
    profile_database = []
    profile_db_path = 'database/profile-%s.json'%(profile_id)
    if os.path.isfile(profile_db_path):
        with open(profile_db_path) as json_file:
            profile_database = json.loads(json_file.read())
    return profile_database

def do_scrape_cycle(profiles_list):
    for profile in profiles_list:
        profile = [f.strip() for f in profile]
        profile_id = profile[0]
        profile_name = profile[1]
        profile_email = profile[2]
        profile_url = profile[3]
        profile_keywords = [keyword.lower().strip() for keyword in profile[4].split(',')]
        profile_free_items_check = True if profile[5]=='1' else False
                        
        profile_database = read_profile_database(profile_id)
        
        json_url = construct_json_url(profile_url)
        
        page_no=1
        keep_fetching = True
        while keep_fetching and page_no<=max_pages_to_scrape:  #13
            
            print ('Scraping Page (%d) for Profile (%s)'%(page_no,profile_name))
            
            new_results = scrape_new_results(json_url,page_no)

            for resid in new_results:
                
                if resid in profile_database:  #found first match with database
                    keep_fetching = False
                    break
                
                else:  #unique id check + keywords match + optional free items check
                    restitle = new_results[resid]['title']
                    
                    if keyword_match(restitle, profile_keywords) or (profile_free_items_check and new_results[resid]['isFree']):
                        playsound('Kaching.mp3')
                        
                        item_price, msgbody = '',''

                        msgtitle = HTMLParser.unescape(restitle).encode('utf-8')

                        keys=['title','url','age','description','location','distance']
                        for key in keys:
                            msgbody += '%s : %s\n'%(key,new_results[resid][key])

                        item_price = "FREE" if new_results[resid]['isFree'] else new_results[resid]['priceText']
                        msgbody += '\nprice : %s\n'%(item_price)
                        msgbody = HTMLParser.unescape(msgbody).encode('utf-8')

                        item_type = "FREE" if new_results[resid]['isFree'] else "TREASURE" 

                        email_notification(msgbody,msgtitle,profile_email,item_type)
                        
                        profile_database.append(resid)

            page_no+=1

        #at last, update database             
        save_to_database(profile_id,profile_database)
        
def keyword_match(title,profile_keywords):
    global keyword_match_ratio, punctuation_regex
    title = punctuation_regex.sub('', title)
    for word in title.lower().split():
        word = word.strip()
        for keyword in profile_keywords:
            if keyword in word:
                match_ratio = SequenceMatcher(None, keyword, word).ratio()
                if match_ratio >= keyword_match_ratio:
                    return True
    return False

def start_email_server():
    global email_server, server_email_id, server_email_pass

    email_server = smtplib.SMTP("smtp.outlook.com",587)
    #email_server = smtplib.SMTP_SSL('smtp.gmail.com',465)

    email_server.ehlo()
    email_server.starttls() #Puts connection to SMTP server in TLS mode
    email_server.ehlo()
    email_server.login(server_email_id, server_email_pass)

#################################################################
#################################################################    
opener = requests.Session() 
headers = { 'host': 'www.gumtree.com.au',
            'user-agent':'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36' }

page_size = 24              #(can be 24,48,96)
max_pages_to_scrape = 1     #(where maximum==13)
base_url = 'https://www.gumtree.com.au/'
input_path = 'profiles.csv'
email_server = None
server_email_id, server_email_pass = 'healerirl@hotmail.com', 'health888'
keyword_match_ratio=0.9
punctuation_regex = re.compile('[%s]'%re.escape(string.punctuation))

if __name__=="__main__":
    if not os.path.exists('database/'):
        os.makedirs('database/')

    print ('\n\t >> .. Gumtree Ads Scraper.. <<\n')

    runningtime = 0
    profiles_list = read_input_csv(input_path)

    if profiles_list:
        profiles_list = profiles_list[1:]   #skip headers
        print ("Number of Profiles : %d\n"%len(profiles_list))
        
        while is_day_time():

            try:
                start_email_server()
            
                do_scrape_cycle(profiles_list)

                email_server.quit()
            except Exception as e:
                print ('\n>> ERROR: %s\n'%(e))
                    
            wait_time_sec = random.randint(5, 10) * random.randint(55, 65)
            print ("Waiting for :> %d Minutes"%(wait_time_sec/60))

            #divide by 100 to wait less for testing purposes
            #remove /100 for real time testing
            time.sleep(wait_time_sec)
            #time.sleep(wait_time_sec/100)
            
            runningtime = runningtime + wait_time_sec/60
            if runningtime < 60:
                print ("Total Running Time :> %d Minutes"%(runningtime))
            else:
                print ("Total Running Time :> %d Hours and %d Minutes"%(runningtime/60,runningtime%60))
            print("\n##########################################\n")

    print ('\n..Exiting..')
