#! /usr/bin/python
import sys, json, urllib2, time, logging
import PIL as pillow
from cStringIO import StringIO
from datetime import datetime
import logging.handlers
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.rl_config import defaultPageSize
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader

#module to convert GridRef to longLat
import utm
#modules for webpage scraping
import mechanize
from BeautifulSoup import BeautifulSoup
import pyrtlsdr



#Setup logging environment
logPath = '/var/log/turnout/turnout.log'
my_logger = logging.getLogger('MyLogger')
my_logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(logPath, maxBytes=1000000, backupCount=5)
my_logger.addHandler(handler)

#def scrapeBART():
#        global my_logger
#
#        """Access the BART webpage"""
#        br = mechanize.Browser()
#        br.set_handle_robots(False)
#        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
 #       url = 'http://bart.emerg.com.au/administration/Login/Live_Feed_Login.aspx'
#                br.open(url)
#        except URLError:
#                time.sleep(30)
#                br.open(url)
#        response = br.response().read()
#        br.select_form(nr=0)
#        br.set_all_readonly(False)
        #login to BARTwebsite with bart credentials
#        #bart username and pass required here.
#        br.form['txtUsername'] = ''
#        br.form['txtPassword'] = ''
#        response = br.submit(name='submit').read()
#        soup = BeautifulSoup(response)
#        table = soup.find('table', {"class" : "AdminGridView"})
#        return table
#####Removed, introduded rtlsdr instead with POCSAG decoder

def tableScan(x):
        global my_logger
        try:
                for row in x.findAll('tr')[1:]:
                        col = row.findAll('td')
                        if len(col) == 6:
                                id = col[0].string
                                date_time = col[1].string
                                capcode = col[2].string
                                callout = col[3].string
                                map = col[4]
                                try:
                                        map = map.find('a').contents[0]
                                except IndexError:
                                        map = "Message Only"
                                message = col[5].string

                                if callout == "Alert":
                                        isTurnout = True
                                        try:
                                                pager = (id, date_time, capcode, callout, map, message)
                                        except TypeError:
                                                pass
                                        return (map, pager, message, isTurnout, id)
        except AttributeError, error:
                my_logger.debug('Exception encountered: %s' % error)
                map, pager, message, isTurnout, id = (False, False, False, False, False)
                return (map, pager, message, isTurnout, id)

def mapLookup(x):
        #google developer API key required here.
        api_key = ''
        origin = 'CFA+upper+ferntree+Gully'
        n = 3
        map = [x[i:i+n] for i in range(0, len(x), n)]
        #extract out the map details (this is hard coded and needs to be adjusted per brigade)
        northing =  '3%s00' % map[0]
        easting  = '58%s00' % map[1]

        #Could probably clean this up right now.
        destination = utm.to_latlon(int(northing), int(easting), 55, 'H')

        destination = ("%s,%s") % (str(destination[0]), str(destination[1]))
        #get the directions details from maps.googleapis.com
        directions_url = "https://maps.googleapis.com/maps/api/directions/json?origin=%s&destination=%s&key=%s" % (origin, destination, api_key)
        req = urllib2.Request(directions_url)
        response = urllib2.urlopen(req)
        the_page = response.read()
        jsondir = json.loads(the_page)
        return jsondir


def printTurnouts(x):
        global my_logger
        message =  x.split( )
        if "UPPE" in message[3] or "UPPE" in message[2]:
                my_logger.info('4 copies')
        else:
                my_logger.info('1 copy')


def buildMap(x):
        routes = x.get("routes")
        overview =  routes[0].get("overview_polyline")
        points =  overview.get("points")
        legs = routes[0].get("legs")

        map_url = "https://maps.googleapis.com/maps/api/staticmap?size=500x500&scale=2&path=weight:10%%7Ccolor:red%%7Cenc:%s" % points

        #Write map with path
        req = urllib2.Request(map_url)
        response = urllib2.urlopen(req)
        the_page = response.read()
        mapImage1 = StringIO(the_page)
        #file = open('turnout_directions.jpg', 'w')
        ##file.write(the_page)
        #file.close()
        return (mapImage1, legs)

def createPDF(legs, message, mapImage1):
        #setup PDF document
        PAGE_HEIGHT=defaultPageSize[1]; PAGE_WIDTH=defaultPageSize[0]
        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate("turnout.pdf")
        Story = [Spacer(1,0.002*inch)]
        style = styles["Normal"]

        Story.append(Paragraph('TURNOUT', style))
        Story.append(Paragraph(message, style))
        Story.append(Image(mapImage1, width=500, height=500, lazy=1))
        Story.append(Spacer(1,0.5*inch))

        #extract the directions ready for appending to map
        for i in legs[0]:
                if i == "steps":
                        listofsteps = legs[0].get("steps")
                        for i in listofsteps:
                                dir_step =  i.get("html_instructions")
                                p = Paragraph(dir_step, style)
                                Story.append(p)
                                Story.append(Spacer(1,0.1*inch))

        doc.build(Story)


def main(lastID):
        global my_logger

        isTurnout = False
        while True:
                my_logger.debug('Top Of Program')
                table = scrapeBART()
                map, pager, message, isTurnout, id = tableScan(table)
                if id == False:
                        my_logger.debug('Retured error from table scan')
                        #my_logger.debug('Table Dump: %s') % table
                else:
                        my_logger.info('Is it a turnout: %s' % isTurnout)
                        my_logger.info('Last Callout ID: %s' % lastID)
                        if isTurnout == True and lastID != id:
                                table = scrapeBART()
                                the_page = mapLookup(map)
                                mapImage1, legs = buildMap(the_page)
                                createPDF(legs, message, mapImage1)
                                printTurnouts(message)
                                lastID = id
                                my_logger.info('Turnout Complete')
                        else:
                                my_logger.info('-----------------------')
                                my_logger.info('Waiting for New Turnout')
                                time.sleep(30)



#main code branch - code starts here
if __name__ == "__main__":
        time.sleep(180)
        lastID = '0'
        sys.exit(main(lastID))
