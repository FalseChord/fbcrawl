# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html

from scrapy.exceptions import DropItem
from datetime import datetime
from scrapy.exporters import CsvItemExporter
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

class FbcrawlPipeline(object):
	pass
	# def process_item(self, item, spider):
	# 	if item['date'] < datetime(2017,1,1).date():
	# 		raise DropItem("Dropping element because it's older than 01/01/2017")
	# 	elif item['date'] > datetime(2018,3,4).date():
	# 		raise DropItem("Dropping element because it's newer than 04/03/2018")
	# 	else:
	# 		return item

def item_type(item):
    return type(item).__name__.replace('Item','').lower()  # TeamItem => team

class MultiCSVItemPipeline(object):
    SaveTypes = ['fphistory','fpmanager', 'fpad']
    def __init__(self):
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    def spider_opened(self, spider):
        self.files = dict([ (name, open("./"+name+'.csv','w+b')) for name in self.SaveTypes ])
        self.exporters = dict([ (name,CsvItemExporter(self.files[name])) for name in self.SaveTypes])
        [e.start_exporting() for e in self.exporters.values()]

    def spider_closed(self, spider):
        [e.finish_exporting() for e in self.exporters.values()]
        [f.close() for f in self.files.values()]

    def process_item(self, item, spider):
        what = item_type(item)
        if what in set(self.SaveTypes):
            self.exporters[what].export_item(item)
        return item