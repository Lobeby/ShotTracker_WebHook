# IMPORT

import json
import requests
from requests.exceptions import HTTPError
from datetime import date
from html.parser import HTMLParser
from discord_webhook import DiscordWebhook, DiscordEmbed

DEBUG = False

# FUNCTIONS

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

class myHTMLParser(HTMLParser):
    """Custom Parser class to read HTML"""
    def handleData(self, data):
        self.text += data

def readHTML(tempText):
    myHTMLParser().feed(tempText)
    myHTMLParser().close()
    tempResult = myHTMLParser().text
    tempResult = tempResult.replace(' ', ' ').strip()
    tempResult = tempResult.replace('`', '')
    if len(tempResult) == 0:
        tempResult = '// Deleted //'
    if len(tempResult) >= 70:
        tempResult = tempResult[0:70] + '...'
    return tempResult

def getPostList(itemData, tempPost, postDiscordList, vignette, postCount):
    for comment in itemData['comments']:
        tempName = comment['firstname'].strip() + ' ' + comment['lastname'].strip()
        tempDate = comment['creationdate']
        # Select only the posts that are from today and 
        if tempDate[0:10] == str(date.today()):
            postCount += 1
            if comment['files'] == []:
                tempFile = False
            else:
                tempFile = True
            tempText = comment['text']
            tempText = readHTML(tempText)
            # append the data to the list
        
            if tempPost not in postDiscordList:
                postDiscordList[tempPost] = [ [ tempDate, tempName, tempText, tempFile ] ]
            else:
                postDiscordList[tempPost].append( [ tempDate, tempName, tempText, tempFile ] )
                postDiscordList[tempPost].sort()
            postDiscordList = {k: v for k, v in sorted(postDiscordList.items())}
            
            if len( str(itemData['vignette']) ) != 0 and ' ' not in str(itemData['vignette']):
                vignette = str(itemData['vignette'])
    return postDiscordList, vignette, postCount

def createField( postDiscordList ):
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
    return fieldName, fieldValue

def webhookMaker( postDiscordList, vignette, postCount ):
    """Create the for the daily sum up field by field"""
    webhook = DiscordWebhook( url=urlWebHook )

    embed = DiscordEmbed(
        title=' Daily Sum Up -  '+str(date.today()), 
        description='> '+str(postCount)+' new message(s)', 
        color='FF0000')
     
    # if Messages, set fields by posts 
    if postCount != 0:
        fieldName, fieldValue = createField( postDiscordList )
        embed.set_thumbnail(url=vignette)
        for id, name in enumerate(fieldName):
            # add fields to embed
            embed.add_embed_field(
                name=str(name), 
                value=fieldValue[int(id)], 
                inline=False
                )

    embed.set_author(
        name = 'ShotTracker',
        url = 'http://tracker.artfx.fr',
        icon_url='http://tracker.artfx.fr/tracker/images/logo-tracker.png')

    webhook.add_embed(embed)
    response = webhook.execute()


def main(urlWebHook, loginID, loginPW, pfeID):

    ### Variables
    postDiscordList = {}
    vignette = []
    postCount = 0
    ### Log in ShotTracker
    key = getSession( loginID, loginPW )

    # Query the data from ShotTracker 
    for item in getItems( key, pfeID ):
        idData = item['id']
        itemData = getItemData( key, idData )
        postDiscordList, vignette, postCount = getPostList( 
                                                itemData, 
                                                item['name'], 
                                                postDiscordList, 
                                                vignette, 
                                                postCount )

    # Log out from ShotTracker
    endSession( key )
    # Create a WebHook Post in Discord with the collected data
    webhookMaker( postDiscordList, 
        'http://tracker.artfx.fr/tracker/data/vignette/' + str(pfeID) + '/' + str(idData) + '/960/' + vignette, 
        postCount )


### MAIN CODE

with open('./projects.json') as f:
  projects_data = json.load(f)

    for project, data in projects_data['projects'].items():
        if (DEBUG and project == "debug"):
            main('DEBUG', data["loginID"], data["loginPW"], data["pfeID"])
        elif (not DEBUG and project != "debug"):
            main(data["urlWebHook"], data["loginID"], data["loginPW"], data["pfeID"])

# CUSTOM FOR THE PFE PROJECT

# On ShotTracker, go in an asset or a shot, 
# Right Click on the thumbnail and Select "Copy image adress"
# The pfeID is in the adress : 
# http://tracker.artfx.fr/tracker/data/vignette/00/1234/960/image.png
#                                               ^^ pfeID

# Dans ShotTracker, va dans un asset ou un shot, 
# Clic Droit sur l'image et choisi "Copier le lien de l'image"
# Le pfeID est dans l'adresse : 
# http://tracker.artfx.fr/tracker/data/vignette/00/1234/960/image.png
#                                               ^^ pfeID
