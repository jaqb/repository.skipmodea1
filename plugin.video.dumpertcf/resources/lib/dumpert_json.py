#!/usr/bin/env python
# -*- coding: UTF-8 -*-

#
# Imports
#
import os
import re
import requests
import sys
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin
from BeautifulSoup import BeautifulSoup
import json

from dumpert_const import ADDON, SETTINGS, LANGUAGE, IMAGES_PATH, DATE, VERSION


#
# Main class
#
class Main:
    #
    # Init
    #
    def __init__(self):
        # Get the command line arguments
        # Get the plugin url in plugin:// notation
        self.plugin_url = sys.argv[0]
        # Get the plugin handle as an integer number
        self.plugin_handle = int(sys.argv[1])

        xbmc.log("[ADDON] %s v%s (%s) debug mode, %s = %s, %s = %s" % (
                ADDON, VERSION, DATE, "ARGV", repr(sys.argv), "File", str(__file__)), xbmc.LOGDEBUG)

        # Parse parameters
        self.plugin_category = urlparse.parse_qs(urlparse.urlparse(sys.argv[2]).query)['plugin_category'][0]
        self.video_list_page_url = urlparse.parse_qs(urlparse.urlparse(sys.argv[2]).query)['url'][0]
        self.next_page_possible = urlparse.parse_qs(urlparse.urlparse(sys.argv[2]).query)['next_page_possible'][0]

        xbmc.log("[ADDON] %s v%s (%s) debug mode, %s = %s" % (
                ADDON, VERSION, DATE, "self.video_list_page_url", str(self.video_list_page_url)),
                     xbmc.LOGDEBUG)

        # Determine current page number and base_url
        # http://www.dumpert.nl/toppers/
        # http://www.dumpert.nl/
        # http://www.dumpert.nl/<thema>/
        # find last slash
        pos_of_last_slash = self.video_list_page_url.rfind('/')
        # remove last slash
        self.video_list_page_url = self.video_list_page_url[0: pos_of_last_slash]
        pos_of_last_slash = self.video_list_page_url.rfind('/')
        self.base_url = self.video_list_page_url[0: pos_of_last_slash + 1]
        self.current_page = self.video_list_page_url[pos_of_last_slash + 1:]
        self.current_page = int(self.current_page)
        # add last slash
        self.video_list_page_url = str(self.video_list_page_url) + "/"

        xbmc.log("[ADDON] %s v%s (%s) debug mode, %s = %s" % (
                ADDON, VERSION, DATE, "self.video_list_page_url", str(self.video_list_page_url)),
                     xbmc.LOGDEBUG)

        #
        # Get the videos...
        #
        self.getVideos()

    #
    # Get videos...
    #
    def getVideos(self):
        #
        # Init
        #
        shownsfw = (SETTINGS.getSetting('nsfw') == 'true')
        listing = []

        #
        # Get data
        #

        # Set cookies for cookie-firewall and nsfw-switch
        if SETTINGS.getSetting('nsfw') == 'true':
            cookies = {"Cookie": "cpc=10", "nsfw": "1"}
        else:
            cookies = {"Cookie": "cpc=10"}

        # Determine if cloudflare protection is active or not
        html_source = requests.get(self.video_list_page_url, cookies=cookies).text
        if str(html_source).find("cloudflare") >= 0:
            cloudflare_active = True
        else:
            cloudflare_active = False

        # Make a session
        sess = requests.session()

        # Get the page
        if cloudflare_active == True:
            try:
                import cfscrape
            except:
                xbmcgui.Dialog().ok(LANGUAGE(30000), LANGUAGE(30513))
                sys.exit(1)
            try:
                # returns a CloudflareScraper instance
                scraper = cfscrape.create_scraper(sess)
            except:
                xbmcgui.Dialog().ok(LANGUAGE(30000), LANGUAGE(30514))
                sys.exit(1)
            try:
                html_source = scraper.get(self.video_list_page_url).content
            except:
                xbmcgui.Dialog().ok(LANGUAGE(30000), LANGUAGE(30515))
                sys.exit(1)
        else:
            html_source = sess.get(self.video_list_page_url, cookies=cookies).text

        json_source = html_source
        data = json.loads(json_source)
        if not data['success']:
            xbmcplugin.endOfDirectory(self.plugin_handle)
            return

        for item in data['items']:
            title = item['title']
            description = item['description']
            thumbnail_url = item['thumbnail']
            nsfw = item['nsfw']
            if not nsfw or shownsfw:
                # {"id":"6737324_36df9881","title":"Hardcore brei-oma","thumbnail":"http:\/\/media.dumpert.nl\/sq_thumbs\/6737324_36df9881.jpg",
                # "still":"http:\/\/media.dumpert.nl\/stills\/6737324_36df9881.jpg","description":"Heeft vroeger wat uitgevroten... WTF?","date":"2016-03-18T19:35:56+01:00",
                # "tags":"dwdd oma wtf breien oud","nsfw":false,"nopreroll":false,"stats":{"views_total":466917,"views_today":32706,"kudos_total":4916,"kudos_today":343},
                # "stills":{"thumb":"http:\/\/media.dumpert.nl\/sq_thumbs\/6737324_36df9881.jpg","thumb-medium":"http:\/\/media.dumpert.nl\/sq_thumbs\/medium\/6737324_36df9881.jpg",
                # "still":"http:\/\/media.dumpert.nl\/stills\/6737324_36df9881.jpg","still-medium":"http:\/\/media.dumpert.nl\/stills\/medium\/6737324_36df9881.jpg",
                # "still-large":"http:\/\/media.dumpert.nl\/stills\/large\/6737324_36df9881.jpg"},"media":[{"description":"","mediatype":"VIDEO","duration":55,
                # "variants":[{"version":"tablet","uri":"http:\/\/media.dumpert.nl\/tablet\/36df9881_VID_20160318_WA0000.mp4.mp4.mp4"},{"version":"mobile",
                # "uri":"http:\/\/media.dumpert.nl\/mobile\/36df9881_VID_20160318_WA0000.mp4.mp4.mp4"}]}]}
                #
                # grab first item (tablet)
                # skip embedded (youtube links) for now {"version":"embed","uri":"youtube:wOeZB7bnoxw"}
                if item['media'][0]['mediatype'] == 'VIDEO' and item['media'][0]['variants'][0]['version'] != 'embed':
                    url = item['media'][0]['variants'][0]['uri']
                    list_item = xbmcgui.ListItem(label=title, thumbnailImage=thumbnail_url)
                    list_item.setInfo("video", {"title": title, "studio": ADDON, "plot": description})
                    list_item.setArt({'thumb': thumbnail_url, 'icon': thumbnail_url,
                                      'fanart': os.path.join(IMAGES_PATH, 'fanart-blur.jpg')})
                    list_item.setProperty('IsPlayable', 'true')
                    is_folder = False
                    # Add refresh option to context menu
                    list_item.addContextMenuItems([('Refresh', 'Container.Refresh')])
                    # Add our item to the listing as a 3-element tuple.
                    listing.append((url, list_item, is_folder))

        # Next page entry
        if self.next_page_possible == 'True':
            next_page = self.current_page + 1
            list_item = xbmcgui.ListItem(LANGUAGE(30503), thumbnailImage=os.path.join(IMAGES_PATH, 'next-page.png'))
            list_item.setArt({'fanart': os.path.join(IMAGES_PATH, 'fanart-blur.jpg')})
            list_item.setProperty('IsPlayable', 'false')
            parameters = {"action": "json", "plugin_category": self.plugin_category,
                          "url": str(self.base_url) + str(next_page) + '/',
                          "next_page_possible": self.next_page_possible}
            url = self.plugin_url + '?' + urllib.urlencode(parameters)
            is_folder = True
            # Add refresh option to context menu
            list_item.addContextMenuItems([('Refresh', 'Container.Refresh')])
            # Add our item to the listing as a 3-element tuple.
            listing.append((url, list_item, is_folder))

        # Add our listing to Kodi.
        # Large lists and/or slower systems benefit from adding all items at once via addDirectoryItems
        # instead of adding one by ove via addDirectoryItem.
        xbmcplugin.addDirectoryItems(self.plugin_handle, listing, len(listing))
        # Disable sorting
        xbmcplugin.addSortMethod(handle=self.plugin_handle, sortMethod=xbmcplugin.SORT_METHOD_NONE)
        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.plugin_handle)
