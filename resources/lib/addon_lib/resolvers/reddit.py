'''
    Copyright (C) 2017

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
'''

import re
from urlresolver import common
from urlresolver.plugins.lib import helpers
from urlresolver.resolver import UrlResolver, ResolverError


class PlayThisRedditResolver(UrlResolver):
    name = 'reddit'
    domains = ['redd.it', 'reddit.com']
    pattern = '(?:http[s]*://)*((?:v\.redd\.it|(?:www\.)*reddit.com/video))/([^/]+)'

    def __init__(self):
        self.net = common.Net()
        self.dash_supported = common.has_addon('inputstream.adaptive')

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {'User-Agent': common.RAND_UA}
        html = self.net.http_GET(web_url, headers=headers).content

        if html:
            sources = []

            pattern = '''src:\s*canPlayDash\s*\?\s*['"]\s*(?P<dash>[^'"]+)\s*['"]\s*:\s*['"]\s*(?P<hls>[^'"]+)\s*['"]'''
            match = re.search(pattern=pattern, string=html)
            if not match:
                pattern = '''data-hls-url\s*=\s*['"]\s*(?P<hls>[^'"]+).+?data-mpd-url\s*=\s*['"]\s*(?P<dash>[^'"]+)'''
                match = re.search(pattern=pattern, string=html)

            if match:
                if self.dash_supported:
                    sources += [('Reddit', match.group('dash'))]
                else:
                    sources += [('Reddit', match.group('hls'))]

                if sources:
                    return helpers.pick_source(sources) + helpers.append_headers(headers)

        raise ResolverError('File not found')

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, template='https://www.reddit.com/video/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return True

    @classmethod
    def _get_priority(cls):
        try:
            return int(common.get_setting('RedditResolver_priority')) - 1
        except:
            return 99
