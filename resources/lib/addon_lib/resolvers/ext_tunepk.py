'''
tunepk urlresolver plugin
Copyright (C) 2013 icharania
updated Copyright (C) 2017 Gujal

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

import re, json
from urlresolver.plugins.lib import helpers
from urlresolver import common
from urlresolver.resolver import UrlResolver, ResolverError


class ExternalTunePkResolver(UrlResolver):
    name = "tune.pk"
    domains = ["tune.pk", "tune.video"]
    pattern = '(?://|\.)(tune\.(?:video|pk))/(?:player|video|play)/(?:[\w\.\?]+=)?(\d+)'

    def __init__(self):
        self.net = common.Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {'User-Agent': common.FF_USER_AGENT}
        response = self.net.http_GET(web_url, headers=headers)
        html = response.content
        if 'Not Found' in html:
            raise ResolverError('File Removed')

        web_url = re.findall("requestURL = '(.*?)'", html)[0]
        response = self.net.http_GET(web_url, headers=headers)
        jdata = json.loads(response.content)
        vids = jdata.get('data', {}).get('details', {}).get('player', {}).get('sources', [])
        sources = [(vid['label'], vid['file']) for vid in vids]
        return helpers.pick_source(sources) + helpers.append_headers(headers)

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, template='https://embed.tune.pk/play/{media_id}')

    @classmethod
    def _is_enabled(cls):
        return common.get_setting('TunePkResolver_enabled') == 'true'

    @classmethod
    def _get_priority(cls):
        try:
            return int(common.get_setting('TunePkResolver_priority')) - 1
        except:
            return 99
