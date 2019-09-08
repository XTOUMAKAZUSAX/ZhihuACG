import re
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyquery import PyQuery as pq
from Kianna.config import *
import pymongo
import pymongo.errors
import time
import re
import requests

options = webdriver.ChromeOptions()
p=r'C:\Users\21965\AppData\Local\Google\Chrome\User Data'
options.add_argument('--user-data-dir='+p)  # 设置成用户自己的数据目录
browser=webdriver.Chrome(chrome_options=options)
wait=WebDriverWait(browser,10)
client=pymongo.MongoClient(MONGO_URL)
db=client[MONGO_DB]

def search():
    #try:
    browser.get(ZHIHUURL)
    browser.maximize_window()
    input=wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#Popover1-toggle')))
    submit=wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,'#root > div > div:nth-child(2) > header > div.AppHeader-inner > div.SearchBar > div > form > div > div > div > div > button > span > svg')))
    input.send_keys(KEYWORD)
    submit.click()
    ##root > div > div:nth-child(2) > header > div.AppHeader-inner > div.SearchBar > div > form > div > div > div > div > button
    #     total=wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#J_bottomPage > span.p-skip > em:nth-child(1)')))
    #     total_text=total.text
    #     js = "var q=document.documentElement.scrollTop=100000"
    #     browser.execute_script(js)
    #     time.sleep(1)
    #     js = "var q=document.documentElement.scrollTop=100000"
    #     browser.execute_script(js)
    #     time.sleep(1)
    #     get_products()
    #     return total_text
    # except TimeoutException:
    #         return search()

def get_first_url():
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#SearchMain > div > div > div > div > div:nth-child(1) > div')))
    html = browser.page_source
    doc = pq(html)
    item = doc('.ContentItem-title div a').attr('href')
    #items = doc('.ContentItem-title div').item()
    url=ZHIHUURL+item[1:]
    return url

def enter_first_item(url):
    browser.get(url)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#root > div > main > div > div.Question-main > div.ListShortcut > div > div.Card.AnswerCard > div')))
    html = browser.page_source
    doc = pq(html)
    item= doc('.QuestionMainAction.ViewAll-QuestionMainAction').attr('href')
    url=ZHIHUURL+item[1:]
    browser.get(url)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#root > div > main > div > div:nth-child(10) > div.QuestionHeader > div.QuestionHeader-content > div.QuestionHeader-side > div > div > div > button > div > div')))
    js = "var q=document.documentElement.scrollTop=100000"
    browser.execute_script(js)
    time.sleep(1)
    js = "var q=document.documentElement.scrollTop=1"
    browser.execute_script(js)
    time.sleep(1)
    js = "var q=document.documentElement.scrollTop=100000"
    browser.execute_script(js)
    time.sleep(1)
    html = browser.page_source
    doc = pq(html)
    total=doc('.List-headerText span').text()
    total=total.replace(',','');total=total.replace('个回答','')
    total=int(total)
    number=html.count('List-item')
    while number<BASIC_NUMBER: #total
        browser.execute_script("window.scrollBy(0,1000000)")
        time.sleep(1)
        html = browser.page_source
        number = html.count('List-item')
    return html

def parse_answers(html):
    doc = pq(html)
    items=doc('.List-item').items()
    for item in items:
        product = {
            'name':item('.ContentItem.AnswerItem').attr('name'),
            'text': item.text(),
        }
        save_to_mongo(product)

def update_data():
    items=db[MONGO_TABLE].find()
    for item in items:
        data=item['text']
        if re.findall(r'赞同 (\d+)\n',data):
            agree_number=re.findall(r'赞同 (\d+)\n',data)[0]
            agree_number = int(agree_number) + 1
        else:
            agree_number = 1
        #works=re.findall(r'《(.*?)》',data)+re.findall(r'\d.(.*?)\n',data)+re.findall(r'\d、(.*?)\n',data)+re.findall(r'\d。(.*?)\n',data)+re.findall(r'<b>(.*?)</b>',data)
        if re.search(r'《(.*?)》',data):
            works=re.findall(r'《(.*?)》',data)
        elif re.search(r'\d.(.*?)\n',data):
            works=re.findall(r'\d.(.*?)\n',data)
        elif re.search(r'\d、(.*?)\n',data):
            works = re.findall(r'\d、(.*?)\n', data)
        elif re.search(r'\d。(.*?)\n',data):
            works = re.findall(r'\d。(.*?)\n', data)
        elif re.search(r'<b>(.*?)</b>',data):
            works=re.findall(r'<b>(.*?)</b>', data)
        else:
            continue
        parse_works(works,agree_number)

def parse_works(works,agree_number):
    works=list(set(works))
    for work in works:
        if work:
            work=work.replace(' ','')
            work = work.replace('《', '')
            work = work.replace('》', '')
            if work:
                if db[MONGO_DATA_TABLE].find_one({'name':work}):
                    number=db[MONGO_DATA_TABLE].find_one({'name':work})['number']
                    db[MONGO_DATA_TABLE].update_one({'name': work},{'$set': {'number':number+agree_number}})
                else:
                    db[MONGO_DATA_TABLE].update_one({'name': work}, {'$set': {'number':agree_number}}, True)

def adjust_data():
    items = db[MONGO_DATA_TABLE].find()
    for item in items:
        if 'name' in item and 'number' in item:
                url=BAIDU_URL.replace('key',item['name'])
                browser.get(url)
                html=browser.page_source
                if html.find('_百度百科'):
                    types=re.findall(r'<p>类型：(.*?)作品</p>',html)
                    if re.findall(r'<em>(.*?)</em>_百度百科',html):
                        only_name = re.findall(r'<em>(.*?)</em>_百度百科', html)[0]
                    elif re.findall(r'>(.*?)_百度百科', html):
                        only_name = re.findall(r'>(.*?)_百度百科', html)[0]
                    else:
                        print('!!!'+item['name'])
                    for type in types:
                        if type=='动画' or type=='游戏' or type=='漫画' or type=='轻小说':
                            if db[MONGO_LAST_TABLE].find_one({'name': only_name}):
                                number = db[MONGO_LAST_TABLE].find_one({'name': only_name})['number']
                                db[MONGO_LAST_TABLE].update_one({'name': only_name},{'$set': {'number': number + item['number']}})
                            else:
                                db[MONGO_LAST_TABLE].update_one({'name': only_name}, {'$set': {'number': item['number']}},True)
                        break
    db[MONGO_LAST_TABLE].find().sort('number',-1)

def save_to_mongo(result):
    try:
        if db[MONGO_TABLE].update({'text':result['text']},{'$set':result},True):  #.update({'title':data['title']},{'$set':data},True)
            pass
    except Exception:
        pass

def main():
    search()
    url=get_first_url()
    html=enter_first_item(url)
    parse_answers(html)
    update_data()
    adjust_data()

if __name__=='__main__':
    main()

#<em>Muv-Luv Alternative</em>_百度百科