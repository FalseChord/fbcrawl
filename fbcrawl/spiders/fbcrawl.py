import scrapy
import logging
import os
import json

from scrapy import signals
from scrapy.loader import ItemLoader
from scrapy.http import FormRequest
from scrapy.exceptions import CloseSpider
from scrapy.xlib.pydispatch import dispatcher
from fbcrawl.items import FbcrawlItem, parse_date, parse_date2
from datetime import datetime, timedelta

class FacebookSpider(scrapy.Spider):
    '''
    Parse FB pages (needs credentials)
    '''    
    name = 'fb'
    custom_settings = {
        'FEED_EXPORT_FIELDS': ['source','shared_from','date','text', \
                               'reactions','likes','ahah','love','wow', \
                               'sigh','grrr','comments','post_id','url', 'post_url'],
        'DUPEFILTER_CLASS' : 'scrapy.dupefilters.BaseDupeFilter',
    }
    
    def __init__(self, *args, **kwargs):
        #turn off annoying logging, set LOG_LEVEL=DEBUG in settings.py to see more logs
        logger = logging.getLogger('scrapy.middleware')
        logger.setLevel(logging.WARNING)

        dispatcher.connect(self.save_cookie, signal=signals.spider_closed)

        super().__init__(*args,**kwargs)
        
        #parse date
        if 'date' not in kwargs:
            self.logger.info('Date attribute not provided, scraping date set to 2004-02-04 (fb launch date)')
            self.date  = datetime.today() - timedelta(days=8)
            #self.date = datetime(2004,2,4)
        else:
            self.date = datetime.strptime(kwargs['date'],'%Y-%m-%d')
            self.logger.info('Date attribute provided, fbcrawl will stop crawling at {}'.format(kwargs['date']))
        self.year = self.date.year

        #parse start date
        if 'skipto_date' in kwargs:
            self.skipto_date = datetime.strptime(kwargs['skipto_date'],'%Y-%m-%d')
            self.logger.info('Skipto Date attribute provided, fbcrawl will start crawling at {}'.format(kwargs['skipto_date']))
        else:
            self.skipto_date = datetime.today() - timedelta(days=7)

        #parse lang, if not provided (but is supported) it will be guessed in parse_home
        if 'lang' not in kwargs:
            self.logger.info('Language attribute not provided, fbcrawl will try to guess it from the fb interface')
            self.logger.info('To specify, add the lang parameter: scrapy fb -a lang="LANGUAGE"')
            self.logger.info('Currently choices for "LANGUAGE" are: "en", "es", "fr", "it", "pt"')
            self.lang = '_'                       
        elif self.lang == 'en'  or self.lang == 'es' or self.lang == 'fr' or self.lang == 'it' or self.lang == 'pt':
            self.logger.info('Language attribute recognized, using "{}" for the facebook interface'.format(self.lang))
        else:
            self.logger.info('Lang "{}" not currently supported'.format(self.lang))                             
            self.logger.info('Currently supported languages are: "en", "es", "fr", "it", "pt"')                             
            self.logger.info('Change your interface lang from facebook settings and try again')
            raise AttributeError('Language provided not currently supported')
        
        #max num of posts to crawl
        if 'max' not in kwargs:
            self.max = int(10e5)
        else:
            self.max = int(kwargs['max'])
    
        #current year, this variable is needed for proper parse_page recursion
        self.k = datetime.now().year
        
        self.url_root = 'https://mbasic.facebook.com/'
        self.start_urls = self.load_urllist(os.path.join(os.path.dirname(__file__), '../../fp_urls')) + self.load_urllist(os.path.join(os.path.dirname(__file__), '../../group_urls'))

        self.cookie_path = os.path.join(os.path.dirname(__file__), '../../cookie.json')
        self.cookie = self.load_cookie()

    # def start_requests(self):
    #     #return [scrapy.FormRequest("http://www.example.com/login", formdata={'user': 'john', 'pass': 'secret'}, callback=self.logged_in)]
    #     pass

    def start_requests(self):
        yield scrapy.Request(self.url_root, callback=self.parse_home, cookies=self.cookie)

    def parse_home(self, response):
        '''
        This method has multiple purposes:
        1) Handle failed logins due to facebook 'save-device' redirection
        2) Set language interface, if not already provided
        3) Navigate to given page 
        '''
        #handle 'save-device' redirection
        # if response.xpath("//div/a[contains(@href,'save-device')]"):
        #     self.logger.info('Going through the "save-device" checkpoint')
        #     return FormRequest.from_response(
        #         response,
        #         formdata={'name_action_selected': 'dont_save'},
        #         callback=self.parse_home
        #         )
            
        #set language interface
        if self.lang == '_':
            if response.xpath("//input[@placeholder='Search Facebook']"):
                self.logger.info('Language recognized: lang="en"')
                self.lang = 'en'
            elif response.xpath("//input[@placeholder='Buscar en Facebook']"):
                self.logger.info('Language recognized: lang="es"')
                self.lang = 'es'
            elif response.xpath("//input[@placeholder='Rechercher sur Facebook']"):
                self.logger.info('Language recognized: lang="fr"')
                self.lang = 'fr'
            elif response.xpath("//input[@placeholder='Cerca su Facebook']"):
                self.logger.info('Language recognized: lang="it"')
                self.lang = 'it'
            elif response.xpath("//input[@placeholder='Pesquisa no Facebook']"):
                self.logger.info('Language recognized: lang="pt"')
                self.lang = 'pt'
            else:
                raise AttributeError('Language not recognized\n'
                                     'Change your interface lang from facebook ' 
                                     'and try again')

        for url in self.start_urls:
            #navigate to provided page
            group, page = self.trim_url(url)
            href = response.urljoin(page)
            self.logger.info('Scraping facebook page {}'.format(href))
            yield scrapy.Request(url=href,callback=self.parse_page,meta={'index': 1, 'group': group, 'flag':self.k})

    def parse_page(self, response):
        '''
        Parse the given page selecting the posts.
        Then ask recursively for another page.
        '''
#        #open page in browser for debug
#        from scrapy.utils.response import open_in_browser
#        open_in_browser(response)

        #allowed maximum number of outdated post in a page
        maximum_outdated_count = 3
        outdated_count = 0

        #select all posts

        posts = []
        if response.meta['group'] == 1:
            posts = response.xpath("//div[@id='m_group_stories_container']//div[contains(@data-ft,'mf_story_key')]")
        else:
            posts = response.xpath("//div[contains(@data-ft,'top_level_post_id')]")

        for post in posts:
            many_features = post.xpath('./@data-ft').get()
            date = []
            date.append(many_features)
            date = parse_date(date,{'lang':self.lang})
            current_date = datetime.strptime(date,'%Y-%m-%d %H:%M:%S') if date is not None else date
            
            if current_date is None:
                date_string = post.xpath('.//abbr/text()').get()
                if date_string is None:
                    continue
                date = parse_date2([date_string],{'lang':self.lang})
                current_date = datetime(date.year,date.month,date.day) if date is not None else date
                date = str(date)

            #if 'date' argument is reached stop crawling
            if self.date > current_date:
                outdated_count += 1
                if outdated_count > maximum_outdated_count:
                    self.logger.info('Reached date: {} for crawling page {}. Crawling finished'.format(self.date, response.url))
                    return
                else:
                    continue
            #if 'skipto_date' argument is not reached, skip crawling
            if self.skipto_date < current_date:
                continue

            new = ItemLoader(item=FbcrawlItem(),selector=post)
            new.add_xpath('comments', './div[2]/div[2]/a[1]/text()')     
            new.add_value('date',date)
            new.add_xpath('post_id','./@data-ft')
            #new.add_xpath('url', ".//a[contains(@href,'footer')]/@href")
            new.add_value('url',response.url)
            
            #returns full post-link in a list
            post = post.xpath(".//a[contains(@href,'footer')]/@href").extract() 
            temp_post = response.urljoin(post[0])
            yield scrapy.Request(temp_post, self.parse_post, meta={'item':new})

        #load following page, try to click on "more"
        #after few pages have been scraped, the "more" link might disappears 
        #if not present look for the highest year not parsed yet
        #click once on the year and go back to clicking "more"
        
        #new_page is different for groups
        if response.meta['group'] == 1:
            new_page = response.xpath("//div[contains(@id,'stories_container')]/div[2]/a/@href").extract()      
        else:
            new_page = response.xpath("//div[2]/a[contains(@href,'timestart=') and not(contains(text(),'ent')) and not(contains(text(),number()))]/@href").extract()      
            #this is why lang is needed                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^               
        
        if not new_page: 
            self.logger.info('[!] "more" link not found, will look for a "year" link')
            #self.k is the year link that we look for 
            if response.meta['flag'] == self.k and self.k >= self.year:                
                xpath = "//div/a[contains(@href,'time') and contains(text(),'" + str(self.k) + "')]/@href"
                new_page = response.xpath(xpath).extract()
                if new_page:
                    new_page = response.urljoin(new_page[0])
                    self.k -= 1
                    self.logger.info('Found a link for year "{}", new_page = {}'.format(self.k,new_page))
                    yield scrapy.Request(new_page, callback=self.parse_page, meta={'flag':self.k, 'group':response.meta['group']})
                else:
                    while not new_page: #sometimes the years are skipped this handles small year gaps
                        self.logger.info('Link not found for year {}, trying with previous year {}'.format(self.k,self.k-1))
                        self.k -= 1
                        if self.k < self.year:
                            self.logger.info('Reached date: {} for crawling page {}. Crawling finished'.format(self.date, response.url))
                            return
                        xpath = "//div/a[contains(@href,'time') and contains(text(),'" + str(self.k) + "')]/@href"
                        new_page = response.xpath(xpath).extract()
                    self.logger.info('Found a link for year "{}", new_page = {}'.format(self.k,new_page))
                    new_page = response.urljoin(new_page[0])
                    self.k -= 1
                    yield scrapy.Request(new_page, callback=self.parse_page, meta={'flag':self.k, 'group':response.meta['group']}) 
            else:
                self.logger.info('Crawling has finished with no errors!')
        else:
            new_page = response.urljoin(new_page[0])
            if 'flag' in response.meta:
                self.logger.info('Page scraped, clicking on "more"! new_page = {}'.format(new_page))
                yield scrapy.Request(new_page, callback=self.parse_page, meta={'flag':response.meta['flag'], 'group':response.meta['group']})
            else:
                self.logger.info('First page scraped, clicking on "more"! new_page = {}'.format(new_page))
                yield scrapy.Request(new_page, callback=self.parse_page, meta={'flag':self.k, 'group':response.meta['group']})
                
    def parse_post(self,response):
        new = ItemLoader(item=FbcrawlItem(),response=response,parent=response.meta['item'])
        new.context['lang'] = self.lang
        new.add_xpath('source', "//td/div/h3/strong/a/text() | //span/strong/a/text() | //div/div/div/a[contains(@href,'post_id')]/strong/text()")
        new.add_xpath('shared_from','//div[contains(@data-ft,"top_level_post_id") and contains(@data-ft,\'"isShare":1\')]/div/div[3]//strong/a/text()')
     #   new.add_xpath('date','//div/div/abbr/text()')
        new.add_xpath('text',"//div[@id='m_story_permalink_view']/div[1]//p//text() | //div[@data-ft]/div[@class]/div[@class]/text()")
        new.add_value('post_url',response.url)
        
        #check reactions for old posts
        check_reactions = response.xpath("//a[contains(@href,'reaction/profile')]/div/div/text()").get()
        if not check_reactions:
            yield new.load_item()       
        else:
            new.add_xpath('reactions',"//a[contains(@href,'reaction/profile')]/div/div/text()")
            reactions = response.xpath("//div[contains(@id,'sentence')]/a[contains(@href,'reaction/profile')]/@href")
            reactions = response.urljoin(reactions[0].extract())
            yield scrapy.Request(reactions, callback=self.parse_reactions, meta={'item':new})
        
    def parse_reactions(self,response):
        new = ItemLoader(item=FbcrawlItem(),response=response, parent=response.meta['item'])
        new.context['lang'] = self.lang           
        new.add_xpath('likes',"//a[contains(@href,'reaction_type=1')]/span/text()")
        new.add_xpath('ahah',"//a[contains(@href,'reaction_type=4')]/span/text()")
        new.add_xpath('love',"//a[contains(@href,'reaction_type=2')]/span/text()")
        new.add_xpath('wow',"//a[contains(@href,'reaction_type=3')]/span/text()")
        new.add_xpath('sigh',"//a[contains(@href,'reaction_type=7')]/span/text()")
        new.add_xpath('grrr',"//a[contains(@href,'reaction_type=8')]/span/text()")
        yield new.load_item()

    def load_cookie(self):
        cookies = []
        with open(self.cookie_path) as f:
            cookies = json.loads(f.read())
        return cookies

    def save_cookie(self):
        with open(self.cookie_path, 'w') as file:
            json.dump(self.cookie, file, indent=2)

    def load_urllist(self, file):
        with open(file) as f:
            return [x.strip() for x in list(f.readlines())]

    def trim_url(self, url):
        group = 0
        page = ''
        if url.find('/groups/') != -1:
            group = 1

        if url.find('https://www.facebook.com/') != -1:
            page = url[25:]
        elif url.find('https://mbasic.facebook.com/') != -1:
            page = url[28:]
        elif url.find('https://m.facebook.com/') != -1:
            page = url[23:]

        return group, page

