# coding: utf-8
import json
import re
import time
import os
import traceback
#from selenium import webdriver
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

def parse_pub_meta(browser):
	WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.XPATH, "//div[@class='_2v-2']")))
	member = int(browser.find_element(By.XPATH, "//div[@class='_2v-2'][1]").text.split('·')[1].strip().replace(',',''))
	return {
		"member_total": member
	}

def parse_history(browser):

	history_tab_path = "//div[@id='rhc_col']//a[text()='See More'][1]"
	history_btn = browser.find_element(By.XPATH, history_tab_path)
	history_btn.click()
	time.sleep(5)

	dialog_path = "//div[@id='name_list']"
	WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.XPATH, dialog_path)))
	history_list = browser.find_element(By.XPATH, dialog_path)

	result = []
	for i, text in enumerate(history_list.text.split('\n')):
		if i % 2 == 0:
			if "Changed" in text or "changed" in text:
				result.append({"type":"change", "name": text.replace("Changed name to", "").strip()})
			elif "Created" in text or "created" in text:
				result.append({"type":"create", "name": text})
		else:
			result[-1]["date"] = text

	return result

def parse_pri_meta(browser):
	WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.XPATH, "//span[text()='Activity']/../..")))
	meta_posts = browser.find_element(By.XPATH, "//span[text()='Activity']/../..//div[@class='_4bl9']").text.split('\n')
	meta_members = browser.find_element(By.XPATH, "//span[text()='Activity']/../..//div[@class='_4bl7']").text.split('\n')
	
	return {
		"post_today": int(meta_posts[0].replace(",", "")),
		"post_30day": meta_posts[2],
		"member_total": int(meta_members[0].replace(",", "")),
		"member_30day": meta_members[2]
	}

def run(browser, filename, urls):

	with open(filename, 'a') as f:
		for url in urls:		
			url = url.strip()

			result = {
				'url': url
			}

			try:
				browser.get(url)
				WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.XPATH, "//div[@class='_19s_']")))
				public_string = browser.find_element(By.XPATH, ".//div[@class='_19s_']").text

				if public_string == 'Closed group':
					result["meta"] = parse_pri_meta(browser)
					result["history"] = parse_history(browser)
				elif public_string == 'Public group':
					browser.get(url + 'about')
					result["meta"] = parse_pub_meta(browser)
					result["history"] = parse_history(browser)
				else:
					raise Exception('Wrong group type')
			
			except Exception as e:
				browser.save_screenshot(os.path.join(os.path.dirname(filename), url.split('?')[0].split('/')[-2] + '.png'))
				traceback.print_exc()
				pass

			f.write(json.dumps(result) + '\n')
