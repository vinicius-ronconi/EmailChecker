from apiclient.discovery import build
from apiclient import errors
from baseobject import *
from operator import itemgetter
from selenium.common.exceptions import ElementNotVisibleException


import os
import sys
import urllib

import gsearch_reader

class EmailChecker(BaseObject):
	CONST_STATIC_DIR = ''


	googlePages = 1
	stopWhenFound = True

#	search_engine_id = '012229299473602674636:xod5lrggucs'
#	api_key = 'AIzaSyD8y01BmKw7bdGaHkhq9OcCzU3vG_dx5xs'
	search_engine_id = '012229299473602674636:2xcpnfdhv_q'
	api_key = 'AIzaSyATlUuELvnQ4QXAjsDcd3GDM_rjfmoyTVc'

	CONST_GOOGLE_SEARCH_URL = 'http://www.google.com/search'
	CONST_RESULT_CSS = 'div.g'
	CONST_GOOGLE_ROBOT_URL = '/sorry'

	patterns = None
	firstName = None
	lastName = None
	domain = None
	emailValidationList = OrderedDict()

	resultWithEmails = []

	def getErrorMessage(self, e):
		errorMsg = ''
		if isinstance(e, ElementNotVisibleException):
			errorMsg = 'No results found'
		else:
			errorMsg = 'General Error - ' + str(e)

		return errorMsg

	def setItemInformation(self, email, count, comment=None):
		if not email:
			raise Exception('email not set.')

		item = self.getOrderedDict()

		item['email'] = email
		item['googleCount'] = count
		item['comment'] = comment

		return item

	def getQueryTerms(self, email):
		terms = ''

		if self.firstName:
			terms = terms + self.firstName + ' '

		if self.middleName:
			terms = terms + self.middleName + ' '

		if self.lastName:
			terms = terms + self.lastName + ' '

		if self.domain:
			terms = terms + self.domain + ' '

		if email:
			terms = terms + email

		return terms.strip()

	def linkExists(self, item):
		for f in self.resultWithEmails:
			if f['link'] == item['link'] and f['type'] == item['type'] and f['emailFound'] ==item['emailFound']:
				return True

		return False

	def getGoogleApiOccurrences(self, email):
		service = build('customsearch', 'v1', developerKey=self.api_key)
		collection = service.cse()

		count = 0

		emailEntries = []

		g = gsearch_reader.GSearch(email=email)
		for i in range(0, self.googlePages):
			start_val = 1 + (i * 10)
			request = collection.list(q=self.getQueryTerms(email), num=10, start=start_val, cx=self.search_engine_id)
			try:
				response = request.execute()
			except errors.HttpError as err:
				raise Exception('It was not possible to complete the search due to an error on Google Request: <br>' + str(err).replace('<', '[').replace('>', ']'))

			g.loadDataFromJSON(response)
			foundEmails = g.processData()

			for f in foundEmails:
				if not self.linkExists(f):
					self.resultWithEmails.append(f)
					if f['type'] == 'ExactMatch':
						count = count + 1

			if count > 0 and self.stopWhenFound:
				break

		return count

	def getResponsesForEmail(self, email):
		responses = []
		setDriver = False

		if not self.driver:
			self.initWebDriver()
			setDriver = True
		try:
			url = self.CONST_GOOGLE_SEARCH_URL + '?' + urllib.parse.urlencode( {'q' : self.getQueryTerms(email) })
			self.setContent(url, self.CONST_RESULT_CSS)
			items = self.soup.select(self.CONST_RESULT_CSS)
			for i in items:
				responses.append(i)
		except Exception as e:
			if isinstance(e, ElementNotVisibleException):
				if self.CONST_GOOGLE_ROBOT_URL in self.driver.current_url:
					raw_input('Please, fill the captcha in the browser before continue the Google Search. After that, press Enter...')
			else:
				print ('ERROR RETRIEVING DATA - ' + str(e))
		finally:
			if setDriver:
				self.closeWebDriver()

		return responses

	def getResponsesForAllEmails(self, initialPage=1, maxPages=0):
		if len(self.inputData) == 0:
			raise Exception('No input data defined. Please, read a CSV file before check emails using the readCSV method.')

		self.setInitialPage(initialPage)
		responses = []

		self.initWebDriver()
		try:
			for p in self.inputData[self.currentPage:]:
				if self.fileType == FileType.csv:
					email = p[0]
				else:
					email = p

				if not self.hasMorePages(maxPages):
					break

				for r in self.getResponsesForEmail(email):
					responses.append(r)

				self.setCurrentPage(self.currentPage + 1)
		finally:
			self.closeWebDriver()

		return responses

	def countOccurrences(self, autoRefresh=True, initialPage=1, maxPages=0):
		if len(self.inputData) == 0:
			raise Exception('No input data defined. Please, read a CSV file before check emails using the readCSV method.')

		self.setInitialPage(initialPage)
		self.resultWithEmails = []
		output = []

		self.initWebDriver()
		try:

			for email in self.inputData:
				googleCount = 0

				responses = self.getResponsesForEmail(email)

				for resp in responses:
					googleCount = googleCount + resp.text.count(' ' + email) + resp.text.count(':' + email)

				outputItem = self.setItemInformation(email, googleCount)
				output.append(outputItem)
				if googleCount > 0 and self.stopWhenFound:
					break
		finally:
			self.closeWebDriver()

		self.emailValidationList = output

	def loopEmails(self):
		if len(self.inputData) == 0:
			raise Exception('No patterns data defined. Please, read a Patterns file using the readPatterns method.')

		self.resultWithEmails = []
		output = []

		for email in self.inputData:
			googleCount = self.getGoogleApiOccurrences(email)

			outputItem = self.setItemInformation(email, googleCount)
			output.append(outputItem)

			if googleCount > 0 and self.stopWhenFound:
				break

		self.emailValidationList = output


	def saveEmails(self, autoRefresh=False, initialPage=1, maxPages=0, useAPI=True, outputFile='output.csv'):
		if autoRefresh:
			if useAPI:
				self.loopEmails()
			else:
				self.countOccurrences(autoRefresh, initialPage, maxPages)

		self.emailValidationList = sorted(self.emailValidationList, key=itemgetter('googleCount'), reverse=True)

		if not useAPI:
			self.setWriter(outputFile)
			for record in self.emailValidationList:
				self.writeToCSV(record)
			print (str(self.emailValidationList[0]['email']) + ' is the best guess.... We found it ' + str(self.emailValidationList[0]['googleCount']) + ' times in the first Google Search results page.')
			print ('Please, check the complete list in the file: ' + self.outputFileName)


	def readPatterns(self,filename='patterns.txt'):
		with open(self.CONST_STATIC_DIR + filename, 'rU') as input:
			self.patterns = input.readlines()
		self.patterns = [x.strip().replace('\n', '') for x in self.patterns if x.strip()[0] != '#']

	def createEmailsFromPatterns(self):
		if not self.inputData:
			self.inputData = []

		if not self.patterns:
			self.readPatterns()

		if not self.domain:
			raise Exception('Domain is mandatory')

		self.setPagingAsSingleRecord()

		for p in self.patterns:
			if not self.middleName and ( '{mi}' in p.lower() or '{mn}' in p.lower() ):
				continue

			if not self.lastName and ( '{li}' in p.lower() or '{ln}' in p.lower() ):
				continue

			if not self.firstName and ( '{fi}' in p.lower() or '{fn}' in p.lower() ):
				continue

			email = p.lower()+ '@' + self.domain.lower()

			if self.firstName:
				email = email.replace('{fn}', self.firstName.lower())
				email = email.replace('{fi}', self.firstName.lower()[0])

			if self.middleName:
				email = email.replace('{mn}', self.middleName.lower())
				email = email.replace('{mi}', self.middleName.lower()[0])

			if self.lastName:
				email = email.replace('{ln}', self.lastName.lower())
				email = email.replace('{li}', self.lastName.lower()[0])

			self.inputData.append(email)

	def __init__(self, filename=None, googlePages = 1, stopWhenFound=True, firstName='', middleName='', lastName='', domain=''):
		self.isDevelopmentEnvironment = ('PYTHON_DEV' in os.environ)
		if self.isDevelopmentEnvironment:
			self.CONST_STATIC_DIR = '/Users/ronconi/Workspaces/Github/EmailChecker/static/'
		else:
			self.CONST_STATIC_DIR = '/home/viniciusronconi/mysite/static/'

		self.inputFileName = filename

		self.rowSample['email'] = None
		self.rowSample['googleCount'] = None
		self.rowSample['comment'] = None

		if self.inputFileName:
			self.readCSV(self.inputFileName)
			self.setPagingAsSingleRecord()

		self.googlePages = googlePages
		self.stopWhenFound = stopWhenFound
		self.firstName = firstName
		self.middleName = middleName
		self.lastName = lastName
		self.domain = domain

if __name__ == "__main__":
	e = EmailChecker()
	e.createEmailsFromPatterns()
	e.saveEmails(autoRefresh=True, useAPI=True)