from datetime import datetime
from seleniumwire import webdriver

import os
import json
import fp_crawl, group_crawl

DATE = datetime.now().strftime('%y%m%d')
DATADIR = '../data/'+DATE

FP_OUT = 'fanpage'
GROUP_OUT = 'group'

FP_URLS = '../fp_urls'
GROUP_URLS = '../group_urls'

def related_path(path):
	return os.path.join(os.path.dirname(__file__), path)

if not os.path.exists(related_path(DATADIR)):
    os.makedirs(related_path(DATADIR))

def save_cookies(driver, file_path):
  with open(file_path, 'w') as file:
    cookies = driver.get_cookies()
    json.dump(cookies, file, indent=2)

def load_cookies(browser, file_path):
	with open(file_path, 'r') as file:
		cookies = json.load(file)

	for cookie in cookies:
		browser.add_cookie(cookie);

def read_urls(file_path):
	with open(file_path, 'r') as file:
		return file.readlines()

if __name__ == '__main__':
	chrome_options = webdriver.ChromeOptions()
	chrome_options.add_argument('--headless')
	chrome_options.add_argument('--disable-gpu')
	chrome_options.add_argument('--no-sandbox')
	chrome_options.add_argument('--disable-notifications');
	chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36")
	browser = webdriver.Chrome('/usr/local/bin/chromedriver', chrome_options=chrome_options)#, seleniumwire_options={'verify_ssl': False})#, desired_capabilities=caps)    # 如果没有把chromedriver加入到PATH中，就需要指明路径

	browser.get("https://www.facebook.com")
	browser.delete_all_cookies()
	load_cookies(browser, "cookie.json")

	try:
		fp_crawl.run(browser, os.path.join(os.path.dirname(__file__), DATADIR, FP_OUT), read_urls(related_path(FP_URLS)))
		group_crawl.run(browser, os.path.join(os.path.dirname(__file__), DATADIR, GROUP_OUT), read_urls(related_path(GROUP_URLS)))
	except Exception as e:
		print(e)
		pass

	save_cookies(browser, "cookie.json")
	browser.quit()
