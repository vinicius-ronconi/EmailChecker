from bs4 import BeautifulSoup
from collections import OrderedDict
from enum import Enum
from selenium import webdriver
from selenium.common.exceptions import ElementNotVisibleException, NoSuchElementException, StaleElementReferenceException

import copy
import csv
import os
import time

class PagingType(Enum):
	singleRecord = 1
	urlParam = 2
	element = 3

class FileType(Enum):
	csv = 1
	txt = 2

class BaseObject(object):
	driver = None
	html = None
	soup = None
	isDevelopmentEnvironment = False

	rowSample = OrderedDict()

	writer = None
	inputFileName = None
	outputFileName = None
	inputData = None

	columnDelimiter = ','
	lineTerminator = '\n'
	currentPage = 1
	hasHeader = True
	fileType = None

	pagingType = None
	pageParameter = None
	pageCssSelector = None
	currentPageCssSelector = None
	itemCssSelector = None

	def getOrderedDict(self):
		return copy.deepcopy(self.rowSample)

	def closeWebDriver(self):
		self.driver.close()

	def initWebDriver(self):
		self.driver = webdriver.Firefox()

	def setContent(self, url, selector):
		self.driver.get(url)
		self.refreshContent()

		if selector:
			self.waitForVisibility(selector)

	def refreshContent(self):
		self.html = self.driver.page_source
		self.soup = BeautifulSoup(self.html, 'lxml')

	def waitForVisibility(self, selector, timeout_seconds=5, pause_interval=0.5):
		retries = timeout_seconds

		while retries:
			try:
				element = self.driver.find_element_by_css_selector(selector)
				if element.is_displayed() and element.is_enabled():
					self.refreshContent()
					return element
			except (NoSuchElementException, StaleElementReferenceException):
				if retries <= 0:
					raise
				else:
					pass

			retries = retries - pause_interval
			time.sleep(pause_interval)
		raise ElementNotVisibleException ('Element %s not visible despite waiting for %s seconds' % (selector, timeout_seconds) )

	def getStrValue(self, text):
		if text is None:
			return ''
		else:
			return str(text).strip().replace('\n','')

	def writeToCSV(self, line):
		if (not self.writer) or (not line):
			return

		for k,v in line.items():
			line[k] = self.getStrValue(v)

		with open(self.outputFileName, 'a') as output:
			self.writer = csv.writer(output, delimiter=self.columnDelimiter, lineterminator = self.lineTerminator)
			self.writer.writerow(line.values())
			output.close()

	def setWriter(self, filename=None):
		if filename:
			self.outputFileName = filename
		else:
			self.outputFileName = os.path.splitext(self.inputFileName)[0] + '-output.csv'

		with open(self.outputFileName, 'w') as output:
			self.writer = csv.writer(output, delimiter=self.columnDelimiter, lineterminator = self.lineTerminator)
			self.writer.writerow(self.rowSample.keys())
			output.close()

	def clearWriter(self):
		self.outputFileName = None
		self.writer = None

	def readCSV(self, filename, delimiter=';',lineTerminator='\n', hasHeader=True):
		with open(filename, 'rU') as input:
			reader = csv.reader(input, dialect=csv.excel_tab, delimiter=delimiter, lineterminator = lineTerminator)
			self.inputData = list(reader)
			self.columnDelimiter = delimiter
			self.lineTerminator = lineTerminator
			self.inputFileName = filename
			self.hasHeader = hasHeader
			self.setPagingAsSingleRecord()
			self.fileType = FileType.csv

	def readText(self, filename, lineTerminator='\n', hasHeader=True):
		with open(filename, 'rU') as input:
			self.inputData = input.readlines()
			self.inputData = [self.getStrValue(x) for x in self.inputData]
			self.lineTerminator = lineTerminator
			self.inputFileName = filename
			self.hasHeader = hasHeader
			self.setPagingAsSingleRecord()
			self.fileType = FileType.txt

	def setPagingAsSingleRecord(self):
		self.pagingType = PagingType.singleRecord
		self.pageParameter = None
		self.pageCssSelector = None
		self.currentPageCssSelector = None
		self.itemCssSelector = None

	def setPagingAsUrlParam(self, paramName, cssSelector, currentPageCssSelector, itemCssSelector):
		self.pagingType = PagingType.urlParam
		self.pageParameter = paramName
		self.pageCssSelector = cssSelector
		self.currentPageCssSelector = currentPageCssSelector
		self.itemCssSelector = itemCssSelector

	def setPagingAsElement(self, cssSelector, currentPageCssSelector, itemCssSelector):
		self.pagingType = PagingType.element
		self.pageParameter = None
		self.pageCssSelector = cssSelector
		self.currentPageCssSelector = currentPageCssSelector
		self.itemCssSelector = itemCssSelector

	def setCurrentPage(self, page):
		self.currentPage = page

	def getCurrentPage(self):
		if self.pagingType == PagingType.urlParam:
			parsedUrl = urlparse.urlparse(self.driver.current_url)
			self.currentPage = int(urlparse.parse_qs(parsedUrl.query)[self.pageParameter][0])
			return self.currentPage
		elif self.pagingType == PagingType.element:
			elements = self.soup.select(self.currentPageCssSelector)
			for e in elements:
				if e.text.isnumeric():
					self.currentPage = int(e.text)
					return self.currentPage
					break
		elif self.pagingType == PagingType.singleRecord:
			return self.currentPage
		else:
			raise Exception('Paging Type not defined')

	def hasMorePages(self,maxPages):
		found = False

		if self.currentPage >= maxPages and maxPages > 0:
			return False

		if self.pagingType in (PagingType.urlParam, PagingType.element):
			try:
				pages = self.driver.find_elements_by_css_selector(self.currentPageCssSelector)
				for page in pages:
					#ATTENTION: May change according to the project
					p = int(page.get_attribute('data-page'))
					if p > self.currentPage:
						page.click()

						self.waitForVisibility(self.itemCssSelector)

						found = True
						break
			except NoSuchElementException:
				pass
		elif self.pagingType == PagingType.singleRecord:
			found = (self.currentPage < len(self.inputData))
		else:
			raise Exception('Paging Type not defined')

		return found

	def setInitialPage(self, initialPage):
		if self.pagingType == PagingType.urlParam:
			url_parts = list(urlparse.urlparse(self.driver.current_url))
			url_parts[4] = re.sub(self.pageParameter + '=\d+', self.pageParameter + '=' + str(initialPage), url_parts[4])
			self.setContent(urlparse.urlunparse(url_parts))
			self.waitForVisibility(self.itemCssSelector)
		elif self.pagingType == PagingType.element:
			curPage = self.getCurrentPage()

			while curPage < initialPage:
				if not self.hasMorePages(initialPage):
					break
				curPage = self.getCurrentPage()
		elif self.pagingType == PagingType.singleRecord:
			self.currentPage = initialPage - 1
		else:
			raise Exception('Paging Type not defined')

	def __init__(self, *args, **kwargs):
		try:
			self.isDevelopmentEnvironment = ('PYTHON_DEV' in os.environ['PYTHON_DEV'])
		except:
			self.isDevelopmentEnvironment = False
