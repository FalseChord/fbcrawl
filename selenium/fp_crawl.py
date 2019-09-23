# coding: utf-8
import json
import re
import time
import os
#from selenium import webdriver
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

def ad_repeated(result, ad_obj):
	for ad in result:
		if ad == ad_obj:
			return True
	return False

def process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response

def try_find_element(element, xpath):
	try:
		element.find_element(By.XPATH, xpath)
	except NoSuchElementException:
		return False
	return True

#get logs after specified timestamp
def get_log(ts=0):
	pass

#should be in main page
def parse_fp_meta(browser):
	meta_strings = browser.find_elements(By.XPATH, "//span[@class='_38my' and text()='Community']/../..//div[@class='_4bl9']")
	fp_like = meta_strings[0].text.split(" ")[0].replace(",","")
	fp_follow = meta_strings[1].text.split(" ")[0].replace(",","")
	result = {
		"like": int(fp_like),
		"follow": int(fp_follow)
	}

	return result

#should be in transparency page
def parse_fp_history(browser):

	WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//ul[@role='tablist']/li[2]")))
	time.sleep(5)

	btn = browser.find_element(By.XPATH, "//div[@role='dialog']//ul[@role='tablist']/li[2]/a")
	btn.click()

	WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.XPATH, "//div[@class='_7jxk _7jxl']")))
	history_list = browser.find_element(By.XPATH, "//div[@class='_7jxj']")

	result = []
	for i, text in enumerate(history_list.text.split('\n')):
		if i % 2 == 0:
			if "Changed" in text or "changed" in text:
				result.append({"type":"change", "name": text.replace("Changed name to", "").strip()})
			elif "Created" in text or "created" in text:
				result.append({"type":"create", "name": text.replace("Page created -", "").strip()})
		else:
			result[-1]["date"] = text

	return result

#should be in transparency page
def parse_fp_managers(browser):
	try:
		btn = browser.find_element(By.XPATH, "//div[@role='dialog']//ul[@role='tablist']/li[3]")
	except:
		return []

	btn.click()

	WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.XPATH, "//div[@class='_7jxj']")))

	result = []
	managers_list = browser.find_element(By.XPATH, "//div[@class='_7jxj']")
	for text in managers_list.text.split('\n')[1:]:
		manager_token = text.split(" ")
		result.append({"country": manager_token[0], "count": manager_token[1][1:-1]})

	return result

#should be in transparency page
def parse_fp_ads(browser):

	btn = browser.find_element(By.XPATH, "//div[@role='dialog']//ul[@role='tablist']/li[1]")
	btn.click()
	
	WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.LINK_TEXT, "Go to Ad Library")))

	del browser.requests

	ad_library_btn = browser.find_element(By.XPATH, "//a[text()='Go to Ad Library']")
	ad_library_btn.click()
	browser.close()
	browser.switch_to.window(browser.window_handles[0])

	result = []
	
	try:
		WebDriverWait(browser, 30).until(EC.presence_of_element_located((By.XPATH, ".//div[@class='_7owt']")))
	except:
		return result

	time.sleep(5)

	for r in browser.requests:
		if "search_ads" in r.path:
			body = json.loads(r.response.body.decode("utf-8")[9:])
			#print(body["payload"]["results"])
			for l in body["payload"]["results"]:
				result.append({"list": l})

	ad_index = 0

	#ad_elements = browser.find_elements_by_class_name('_7owt')
	ad_elements = browser.find_elements(By.XPATH, ".//div[@class='_7owt']")

	for ad_element in ad_elements:
		# ad_type = ''
		# ad_link = ''
		# if try_find_element(ad_element, ".//div[@class='_7jwy']/div/a[@class='_231w _231z _4yee']"):
		# 	ad_type = 'link'
		# 	ad_link = ad_element.find_element(By.XPATH, ".//div[@class='_7jwy']/div/a[@class='_231w _231z _4yee']").get_attribute('href')

		# elif try_find_element(ad_element, ".//div[@class='_7jwy']/div/img[@class='_7jys img']"):
		# 	ad_type = 'image'
		# 	ad_link = ad_element.find_element(By.XPATH, ".//div[@class='_7jwy']/div/img[@class='_7jys img']").get_attribute('src')

		# elif try_find_element(ad_element, ".//div[@class='_7jwy']/div/div/video"):
		# 	ad_type = 'video'
		# 	ad_link = ad_element.find_element(By.XPATH, ".//div[@class='_7jwy']/div/div/video").get_attribute('src')
		# else:
		# 	ad_type = 'unknown'

		# ad_date = ad_element.find_element(By.XPATH, ".//div[@class='_7jwu']/span").text
		# ad_text = ad_element.find_element(By.XPATH, ".//div[@class='_7jyr']").text

		# ad_obj = {
		# 	'type': ad_type,
		# 	'date': ad_date,
		# 	'text': ad_text,
		# 	'link': ad_link,
		# }

		detail_btn = ad_element.find_element(By.XPATH, ".//a[@data-testid='snapshot_footer_link']")
		result[ad_index] = parse_fp_ad_detail(browser, detail_btn, result[ad_index])

		ad_index += 1

		# if not ad_repeated(result, ad_obj):
		# 	result.append(ad_obj)

	ad_elements = None
	return result

def parse_fp_ad_detail(browser, btn, ad_obj):

	browser.execute_script("arguments[0].scrollIntoView(true);", btn);
	browser.execute_script("window.scrollBy(0, -200)");

	time.sleep(1)

	del browser.requests
	btn.click()

	time.sleep(5)

	r = browser.wait_for_request('/ads/library/async/insights')
	ad_obj["detail"] = json.loads(r.response.body.decode("utf-8")[9:])["payload"]

	back_btn = browser.find_element(By.XPATH, ".//div[contains(@class,'_5aat') and not(contains(@class,'hidden_elem'))]//div[@class='_7lq1']/button")
	back_btn.click()
	return ad_obj

def run(browser, filename, urls):

	with open(filename, 'a') as f:
		for url in urls:		
			url = url.strip()

			result = {
				'url': url
			}

			try:
				browser.get(url)

				WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.XPATH, "//span[@class='_5dw8']")))
				result['name'] = browser.find_element_by_id('u_0_0').text
				#fp_community_btn = browser.find_elements_by_class_name('_5dw8')[0]
				fp_transparency_btn = browser.find_elements_by_class_name('_5dw8')[2]

				time.sleep(5)

				result["meta"] = parse_fp_meta(browser)

				#move clickable element to the middle of the window
				browser.execute_script("arguments[0].scrollIntoView();", fp_transparency_btn);
				browser.execute_script("window.scrollBy(0, -200)");
				time.sleep(2)

				fp_transparency_btn.click()

				WebDriverWait(browser, 20).until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//ul[@role='tablist']")))

				result["history"] = parse_fp_history(browser)

				result["managers"] = parse_fp_managers(browser)

				result["ads"] = parse_fp_ads(browser)

				time.sleep(5)
			except Exception as e:
				browser.save_screenshot(os.path.join(os.path.dirname(filename), url.split('?')[0].split('/')[-2] + '.png'))
				print(e)
				pass

			f.write(json.dumps(result) + '\n')
