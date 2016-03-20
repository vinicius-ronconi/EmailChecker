from collections import OrderedDict
from emailchecker import *
from flask import Flask, request
from operator import itemgetter
from unittest import result

app = Flask(__name__)

@app.errorhandler(Exception)
def exception_handler(error):
    return 'ERROR !!! <br>'  + repr(error)

def getHtmlHeader():
    result = '<html>' + \
                '<head>' + \
                    '<title>Search Result</title>' + \
                    '<link rel="stylesheet" type="text/css" href="/static/styles.css">' + \
                '</head>' + \
                '<body>'
                
    return result

def getHtmlBestGuess(resp, stopWhenFound, googlePages):
    result = '<h1 class="titulo.result">Result</h1>' + \
             '<div class="bestResult">'
    
    if resp.emailValidationList[0]['googleCount'] > 0:
        result = result + '<div class="bestGuess"><span class="corretEmail">' + resp.emailValidationList[0]['email'] + '</span> is the best guess....</div>' + \
                          '<div class="corretOccurrences">We found it <span class="corretEmailOccurrences">' + str(resp.emailValidationList[0]['googleCount']) + '</span> time(s) in the first <span class="countResults">' + str(googlePages * 10) + '</span> results.</div>'
    else:
        result = result + '<div class="bestGuess">Unfortunatelly, it was not possible to find any e-mail matching one of the patterns tried.</div>'
    
    result = result + '</div>'
    
    if stopWhenFound and resp.emailValidationList[0]['googleCount'] > 0:
        result = result + '<div class="stopWhenFound"><div class="message">Since this e-mail was found, the system stopped the search.</div></div>'

    return result

def getHtmlPatternsList(list):
    result = '<div class="completeList">' + \
                '<div class="listTitle">Check out other e-mails searched:</div>'
    
    odd = True
    for item in list:
        if odd:
            result = result + \
                     '<div class="completeListItem odd">' + item['email'] + ' was found ' + str(item['googleCount']) + ' time(s).</div>'
        else:
            result = result + \
                     '<div class="completeListItem even">' + item['email'] + ' was found ' + str(item['googleCount']) + ' time(s).</div>'
        odd = not odd

    result = result + '</div>'
    
    return result    

def getHtmlResultCard(item):
    result = '<div class="result">' + \
                '<h2 class="emailFound">' + item['emailFound'] + '</h2>' + \
                '<h3 class="title"><a href="' + item['link'] + '">' + item['title'] + '</a></h3>' + \
                '<div class="resultInner">' + \
                    '<div class="link"><a href="' + item['link'] + '">' + item['link'] + '</a></div>' + \
                    '<div class="snippet">' + item['snippet'] + '</div>' + \
                '</div>' + \
             '</div>'
    return result

def getHtmlExactMatches(list):
    result = '<h1 class="titulo.exact">Exact Matches</h1>' + \
             '<div class="explain">In this section you can review all links with an exact match of the best guess.</div>'
    
    found = False
    for l in list:
        if l['type'] == 'ExactMatch':
            found = True
            result = result + getHtmlResultCard(l)

    if not found:
        result = result + '<div class="notFound">No exact match was found.</div>'

    return result

def getHtmlFoundOnSnippet(list):
    result = '<h1 class="titulo.snippet">Emails found on snippet or Title</h1>' + \
             '<div class="explain">In this section you can review all links with e-mails that does not match the search, <br>but can be useful to identify some patterns if no exact match was found.</div>'

    found = False
    for l in list:
        if l['type'] == 'FoundOnSnippet':
            found = True
            result = result + getHtmlResultCard(l)

    if not found:
        result = result + '<div class="notFound">No snippet containing an e-mail was found.</div>'

    return result

def getHtmlFoundOnPageMap(list):
    result = '<h1 class="titulo.pagemap">Emails found on Pagemap</h1>' + \
             '<div class="explain">Here you can see some e-mails found on Google Search metadata.<br>These e-mails are not visible on the snippet, but they were found on internal data on Google Engine.</div>'

    found = False
    for l in list:
        if l['type'] == 'FoundOnPageMap':
            found = True
            result = result + getHtmlResultCard(l)

    if not found:
        result = result + '<div class="notFound">No Google Search Metadata containing an e-mail was found.</div>'

    return result

    
def getHtmlCode(resp, stopWhenFound, googlePages):
    result = getHtmlHeader()
    result = result + getHtmlBestGuess(resp, stopWhenFound, googlePages)
    result = result + getHtmlPatternsList(resp.emailValidationList)
    result = result + getHtmlExactMatches(resp.resultWithEmails)
    result = result + getHtmlFoundOnSnippet(resp.resultWithEmails)
    result = result + getHtmlFoundOnPageMap(resp.resultWithEmails)

    return result


@app.route('/')
def hello():
    result = '<html>' + \
             '<head>'  + \
                '<title>Parameters</title>' + \
                '<link rel="stylesheet" type="text/css" href="static/styles.css">' + \
              '</head>' + \
              '<body>' + \
                '<form action="/email">' + \
                    '<fieldset>' + \
                        '<legend>Personal information</legend>' + \
                        '<input type="text" name="firstName" placeholder="First name">' + \
                        '<input type="text" name="middleName" placeholder="Middle name">' + \
                        '<input type="text" name="lastName" placeholder="Last name">' + \
                        '<input type="text" name="domain" placeholder="Domain (without the @ sign)">' + \
                        '<input type="text" name="googlePages" placeholder="How many google search result pages must be used on the search? Default = 1">' + \
                        '<input type="checkbox" name="stopWhenFound" id="stopWhenFound" value="True" checked>' + \
                        '<label for="stopWhenFound">Stop the search when an exact match is found.</label>' + \
                        '<input type="submit" id="search" class="search" value="Search">' + \
                    '</fieldset>' + \
                '</form>' + \
              '</body>' + \
            '</html>'
            
    return  result

@app.route('/email')
def email():
    firstName = request.args.get('firstName', '')
    middleName = request.args.get('middleName', '')
    lastName = request.args.get('lastName', '')
    domain = request.args.get('domain', '')
    try:
        googlePages = request.args.get('googlePages', '1')
        if googlePages == '':
            googlePages = '1'
        googlePages = int(googlePages)
    except:
        return 'googlePages must be an integer number. If it is not filled, the system will consider just the first page.'
    stopWhenFound = request.args.get('stopWhenFound', '1')

    if domain.strip() == '':
        return 'domain is mandatory and must be filled without the "@" symbol'

    e = EmailChecker(googlePages=googlePages, stopWhenFound=stopWhenFound, firstName=firstName, middleName=middleName, lastName=lastName, domain=domain)
    e.createEmailsFromPatterns()
    e.saveEmails(autoRefresh=True)

    return getHtmlCode(e, stopWhenFound, googlePages)

@app.route('/api')
def api():
	pass
	#TODO: Create REST API using the same structure currently used on email method

if __name__ == '__main__':
	app.run(debug=True)
