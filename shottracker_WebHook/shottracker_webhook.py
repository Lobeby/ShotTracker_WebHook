# IMPORT
import requests
from requests.exceptions import HTTPError
from datetime import *
from  html.parser import HTMLParser
from discord_webhook import DiscordWebhook, DiscordEmbed

import json

DEBUG = False

# CUSTOM FOR THE PFE PROJECT

# On ShotTracker, go in an asset or a shot, Right Click on the thumbnail and Select "Copy image adress"
# The pfeID is in the adress : 
#       http://tracker.artfx.fr/tracker/data/vignette/00/1234/960/image.png
#                                                     ^^ pfeID

# Dans ShotTracker, va dans un asset ou un shot, Clic Droit sur l'image et choisi "Copier le lien de l'image"
# Le pfeID est dans l'adresse : 
#       http://tracker.artfx.fr/tracker/data/vignette/00/1234/960/image.png
#                                                     ^^ pfeID

# DEF FUNCTION

# Code de Fabien
def getSession(login, password):
    url = "http://tracker.artfx.fr/tracker/index.php"
    rData = {"login" : login, "password" : password}
    response = requests.post(url, data=rData)
    return response.cookies["PHPSESSID"]

def endSession(session):
    url = "http://tracker.artfx.fr/tracker/index.php?logout"
    rParm = {"logout": ""}
    rCookie = {"PHPSESSID": session}
    response = requests.get(url, params=rParm, cookies=rCookie) 

def getItems(session, projectId, tagIds=[], sort=1):
    url = "http://tracker.artfx.fr/tracker/json/get-items.php"
    rParm = {"id": str(projectId)}
    rCookie = {"PHPSESSID": session}
    rData = {}
    if len(tagIds) != 0:
        rData["tags[]"] = tagIds
    rData["sort"] = str(sort)
    response = requests.post(url, params=rParm, cookies=rCookie, data=rData)
    return response.json()

def getItemData(session, itemId):
    url = "http://tracker.artfx.fr/tracker/json/get-details.php"
    rParm = {"id": str(itemId)}
    rCookie = {"PHPSESSID": session}
    response = requests.get(url, params=rParm, cookies=rCookie)
    return response.json()

# Parser class pour lire le HTML
class MyHTMLParser(HTMLParser):
    text = ""
    def handle_data(self, data):
        self.text += data

def sendSTDigest(urlWebHook, loginID, loginPW, pfeID):
    parser = MyHTMLParser()

    # VARIABLES
    today = str(date.today())
    vignette = []
    postDiscordList = {}
    count = 0

    ### Log in ShotTracker
    key = getSession( loginID, loginPW )
    items = getItems( key, pfeID )

    # Query the data from ShotTracker 
    for item in items:
        tempPost = item['name']
        idData = item['id']
        itemData = getItemData( key, idData )

        for comment in itemData['comments']:
            tempName = comment['firstname'].strip() +' '+ comment['lastname'].strip()
            tempDate = comment['creationdate']
            if comment['files']==[]:
                tempFile = False
            else:
                tempFile = True
            tempText = comment['text']
            parser = MyHTMLParser()
            parser.feed(tempText)
            parser.close()
            tempResult = parser.text
            tempResult = tempResult.replace(' ', ' ').strip()
            tempResult = tempResult.replace('`', '')
            if len(tempResult)==0:
                tempResult = '// Deleted //'
            if len(tempResult) >= 70:
                tempResult = tempResult[0:70]+'...'

            # Select only the posts that are from today and append the data to the list
            if tempDate[0:10] == today:
                if tempPost not in postDiscordList:
                    count += 1
                    postDiscordList[tempPost] = [ [ tempDate, tempName, tempResult, tempFile ] ]
                else:
                    count += 1
                    postDiscordList[tempPost].append( [ tempDate, tempName, tempResult, tempFile ] )
                    postDiscordList[tempPost].sort()
                postDiscordList = {k: v for k, v in sorted(postDiscordList.items())}
                
                if len( str(itemData['vignette']) ) != 0 :
                    vignette = 'http://tracker.artfx.fr/tracker/data/vignette/'+str(pfeID)+'/'+str(idData)+ '/960/' + str(itemData['vignette'])

    # Log out from ShotTracker
    endSession( key )

    ### WebHook in Achromatic Discord
    webhook = DiscordWebhook(
        url=urlWebHook # default urlWebHook, change this to DEBUG to send it to my Discord Test Server instead
        )

    embed = DiscordEmbed(
        title=' Daily Sum Up -  '+today, 
        description='> '+str(count)+' new message(s)', 
        color='FF0000')
     
    # if Messages, set fields by posts 
    if count != 0:
        fieldName = []
        fieldValue = []
        for cle, valeur in postDiscordList.items():
            message = ''
            for dataList in valeur:
                message +=  dataList[1]+ ' at '+dataList[0][-8:-3]+' : '
                if dataList[3]:
                    message += ':link: '
                message +=  ' `' + dataList[2] + '`\n'
            fieldName.append( '[ ' + str(cle) + ' ] ' )
            fieldValue.append( message )
            
        embed.set_thumbnail(url=vignette)
        for id, name in enumerate(fieldName):
            # add fields to embed
            embed.add_embed_field(
                name=str(name), 
                value=fieldValue[int(id)], 
                inline=False
                )

    embed.set_author(
        name = 'ＳｈｏｔＴｒａｃｋｅｒ',
        url = 'http://tracker.artfx.fr',
        icon_url='http://tracker.artfx.fr/tracker/images/logo-tracker.png')

    webhook.add_embed(embed)
    response = webhook.execute()


with open('./projects.json') as f:
  projects_data = json.load(f)

  for project, data in projects_data['projects'].items():
      if (DEBUG and project == "debug") or (not DEBUG and project != "debug"):
           sendSTDigest(data["urlWebHook"], data["loginID"], data["loginPW"], data["pfeID"])
