# -*- coding: utf-8 -*-
"""
     
    Copyright (C) 2016 anxdpanic
    
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.
    
    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import re
from xbmc import getCondVisibility
from urlresolver.resolver import UrlResolver, ResolverError


class PlayThisTwitchResolver(UrlResolver):
    name = 'twitch'
    domains = ['twitch.tv']
    pattern = 'https?://(?:www\.)?(twitch\.tv)/(.+?)(?:\?|$)'

    def get_media_url(self, host, media_id):
        is_live = True if media_id.count('/') == 0 else False
        if is_live:
            return 'plugin://plugin.video.twitch/playLive/%s/-2/' % media_id
        else:
            if media_id.count('/') == 2:
                media_id_parts = media_id.split('/')
                media_id = media_id_parts[1] + media_id_parts[2]
                return 'plugin://plugin.video.twitch/playVideo/%s/-2/' % media_id
        raise ResolverError('No streamer name or VOD ID found')

    def get_url(self, host, media_id):
        return media_id

    def get_host_and_id(self, url):
        r = re.search(self.pattern, url, re.I)
        if r:
            return r.groups()
        else:
            return False

    def valid_url(self, url, host):
        if getCondVisibility('System.HasAddon(%s)' % 'plugin.video.twitch') == 0:
            return False
        return re.search(self.pattern, url, re.I) or self.name in host

    @classmethod
    def get_settings_xml(cls):
        xml = super(cls, cls).get_settings_xml()
        xml.append('<setting label="This plugin calls the Twitch Add-on, change settings there." type="lsep" />')
        return xml
