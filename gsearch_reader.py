import json
import re
import sys
from enum import Enum

class EmailFoundType(Enum):
	exactMatch = 1
	foundOnSnippet = 2
	foundOnPageMap = 3
	
class GSearch(object):
	data = {}
	emailsFound = []
	email = ''
	
	def loadDataFromFile(self, filename):
		with open(filename) as data_file:
			self.data = json.load(data_file)
		self.emailsFound = []

	def loadDataFromJSON(self, json):
		self.data = json
		self.emailsFound = []

	def addEmail(self, type, emailFound, title, snippet, link):
		item = {}
		item['searchedEmail'] = self.email
		item['type'] = type
		item['emailFound'] = emailFound
		item['title'] = title
		item['snippet'] = snippet
		item['link'] = link
		self.emailsFound.append(item)

	def getEmailsFromText(self, text):
		cleanText = text.replace('\n', '')
		mails = re.findall(r'[\w\.-]+@[\w\.-]+', cleanText)
		return mails

	def lookForEmailOnPagemap(self, obj, title, snippet, link):
		if isinstance(obj, dict):
			for k, v in obj.items():
				if isinstance(v,dict) or isinstance(v,list):
					self.lookForEmailOnPagemap(v, title, snippet, link)
				else:
					mailOnText = self.getEmailsFromText(v)
					for m in mailOnText:
						self.addEmail('FoundOnPageMap', m, title, snippet, link)
		elif isinstance(obj, list):
			for l in obj:
				self.lookForEmailOnPagemap(l, title, snippet, link)
		else:
			mailOnText = self.getEmailsFromText(obj)
			for m in mailOnText:
				self.addEmail('FoundOnPageMap', m, title, snippet, link)

	def processData(self):
		index = 0
		self.emailsFound = []
		if 'items' not in self.data:
			return self.emailsFound
		for item in self.data['items']:
			mailOnSnippet = self.getEmailsFromText(item['snippet'])
			mailOnTitle = self.getEmailsFromText(item['title'])

			if ' ' + self.email in item['snippet'] or \
			   ':' + self.email in item['snippet'] or \
			   '>' + self.email in item['snippet'] or \
			   ' ' + self.email in item['title'] or \
			   ':' + self.email in item['title'] or \
			   '>' + self.email in item['title']:
				self.addEmail('ExactMatch', self.email, item['title'], item['snippet'], item['link'])
				
			elif mailOnSnippet or mailOnTitle:
				for m in mailOnSnippet:
					self.addEmail('FoundOnSnippet', m, item['title'], item['snippet'], item['link'])
				for m in mailOnTitle:
					self.addEmail('FoundOnSnippet', m, item['title'], item['snippet'], item['link'])
			if 'pagemap' in item:
				self.lookForEmailOnPagemap(item['pagemap'], item['title'], item['snippet'], item['link'])
			index = index + 1
			
		return self.emailsFound

	def __init__(self, *args, **kwargs):
		self.email = kwargs.get('email')
		data = kwargs.get('data')
		if data:
			self.loadDataFromJSON(data)
		else:
			inputFile = kwargs.get('inputFile')
			if inputFile:
				self.loadDataFromFile(inputFile)

if __name__ == '__main__':
	inputFile = sys.argv[1]
	email = sys.argv[2]
	g = GSearch(inputFile=inputFile, email=email)
	g.processData()
