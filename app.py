from bs4 import BeautifulSoup
import requests_async as requests
import asyncio
import re
import os
import json

# global vars
i = 0
proUrlsPrefix = 'https://www.checkatrade.com'
proPages = []
contacts = { 'users': [] }

# decode protected email
def decodeEmail(encoded):
  decodedEmail = ''
  k = int(encoded[:2], 16)

  for i in range(2, len(encoded)-1 ,2):
    decodedEmail += chr(int(encoded[i:i+2], 16)^k)
  
  return decodedEmail

# form user object 
def createUserObject(html, _tag, _class):
  user = {}

  # otherwise kills the runtime
  try: 
    nameTmp = BeautifulSoup(html).find('div', { 'class': 'contact-card__contact-name'}).text
    user['name'] = nameTmp.replace('\n', '')
  except:
    user['name'] = 'Error!'
    print('Could not get supplier name.')
  try:
    encodedEmail = BeautifulSoup(html).find(_tag, { 'class': _class }).get('data-cfemail')
    user['email'] = decodeEmail(encodedEmail)
  except:
    user['email'] = 'Error!'
    print('Could not get supplier email.')
  try:
    user['number'] = BeautifulSoup(html).find('span', { 'id': 'ctl00_ctl00_content_lblMobile' }).text
  except:
    user['number'] = 'Error!'
    print('Could not get supplier number.')
  
  return user

# extract stuff
def scrapTrades(html, _tag, _class, single):
  if single:
    contacts['users'].append(createUserObject(html, _tag, _class))

    return 0 
  else:
    # separate function?
    links = BeautifulSoup(html).findAll(_tag, {'class': _class})

    return list(map(lambda link: proUrlsPrefix + link.get('href'), links))

# requests-async.get request
async def makeRequest(url):
  res = await requests.get(url)
  proPages.append(res.text)

# no really needed, but...
async def fetchContent(url):
  await asyncio.create_task(makeRequest(url))

# write to a file
def saveJSONFile(data):
  try: 
    os.remove('contacts.json')
  except:
    print('contact.json file does not exists. Skipping')

  with open('contacts.json', 'w') as outfile:
    json.dump(data, outfile, indent=2, sort_keys=True)

# main function...
async def main():
  # Scrap main page (ads)
  res = await requests.get('https://www.checkatrade.com/Search/?location=W10+5JJ&cat=1476')
  html = res.text

  # basic rec fn
  # TODO break down into smaller functions
  async def recrusive(_html):
    global i
    # build a list of trades people urls
    for url in set(scrapTrades(_html, 'a', 'catnow-search-click', False)):
      await fetchContent(url)

    nextPageEl = BeautifulSoup(_html).findAll('span', { 'class': 'pagination__prev-next' })
    items = list(map(lambda el: el.find('a'), nextPageEl))
    _next = list(map(lambda el: re.sub('[^A-Za-z0-9]+', '', el.text), items))

    if 'Next' in _next:
      print('There is more, go and fetch them all!')
      nextUrl = ''
      if len(items) > 0:
        nextUrl = items[1].get('href')
      else:
        nextUrl = items[0].get('href')

      newPageRes = await requests.get(proUrlsPrefix + nextUrl)
      print('next url: ', nextUrl)
      newHtml = newPageRes.text

      await recrusive(newHtml)

    else :
      print('We are done now...')

  await recrusive(html)

  # add suppliers to the dic
  list(map(lambda page: scrapTrades(page, 'span', '__cf_email__', True), proPages)) 
  
  saveJSONFile(contacts)

asyncio.run(main())
