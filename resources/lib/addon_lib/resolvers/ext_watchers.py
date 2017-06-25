"""
    OVERALL CREDIT TO:
        t0mm0, Eldorado, VOINAGE, BSTRDMKR, tknorris, smokdpi, TheHighway

    urlresolver XBMC Addon
    Copyright (C) 2011 t0mm0

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import re
from urlresolver.plugins.lib import jsunpack, helpers
from urlresolver import common
from urlresolver.resolver import UrlResolver, ResolverError


class ExternalWatchersResolver(UrlResolver):
    name = "watchers"
    domains = ['watchers.to']
    pattern = '(?://|\.)(watchers\.to)/(?:embed-)?([a-zA-Z0-9]+)'

    def __init__(self):
        self.net = common.Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        response = self.net.http_GET(web_url)
        html = response.content

        if html:
            packed = re.search('(eval\(function.*?)\s*</script>', html, re.DOTALL)
            if packed:
                js = jsunpack.unpack(packed.group(1))
            else:
                js = html

            sources = re.findall('''file\s*:\s*["']([^"']+\.(?:(m3u8|mp4)))''', js)
            if sources:
                headers = {'User-Agent': common.RAND_UA, 'Referer': web_url}
                sources = [(b, a) for a, b in sources]
                return helpers.pick_source(sources) + helpers.append_headers(headers)

        raise ResolverError('No playable video found.')

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id)

    @classmethod
    def _is_enabled(cls):
        return common.get_setting('WatchersResolver_enabled') == 'true'

    @classmethod
    def _get_priority(cls):
        try:
            return int(common.get_setting('WatchersResolver_priority')) - 1
        except:
            return 99
