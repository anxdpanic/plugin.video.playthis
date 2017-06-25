'''
thevideo urlresolver plugin
Copyright (C) 2014 Eldorado
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
from urlresolver.plugins.lib import helpers
from operator import itemgetter
from urlresolver import common
from urlresolver.resolver import UrlResolver, ResolverError


class ExternalVidMeResolver(UrlResolver):
    name = "vid.me"
    domains = ["vid.me"]
    pattern = '(?://|\.)(vid\.me)/(?:embedded/|e/)?([0-9A-Za-z]+)'

    def __init__(self):
        self.net = common.Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        html = self.net.http_GET(web_url).content

        # r = re.search('\<meta property.*og:video:url.*\s*content="([^"]+.mp4[^"]+)', html)
        sources = re.findall('''source\s+src\s*=\s*['"]([^'"]+)['"].*?res\s*=\s*['"]([^'"]+)''', html)
        if sources:
            sources = [(b, a.replace('&amp;', '&')) for a, b in sources]
            sources.sort(key=itemgetter(0), reverse=True)
            return helpers.pick_source(sources)

        raise ResolverError('File Not Found or removed')

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, 'https://{host}/embedded/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return common.get_setting('VidMeResolver_enabled') == 'true'

    @classmethod
    def _get_priority(cls):
        try:
            return int(common.get_setting('VidMeResolver_priority')) - 1
        except:
            return 99
