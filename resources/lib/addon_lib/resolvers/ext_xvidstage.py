"""
urlresolver XBMC Addon
Copyright (C) 2011 t0mm0

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
from urlresolver.plugins.lib import jsunpack, helpers
from urlresolver import common
from urlresolver.resolver import UrlResolver, ResolverError


class ExternalXvidstageResolver(UrlResolver):
    name = "xvidstage"
    domains = ["xvidstage.com"]
    pattern = '(?://|\.)(xvidstage\.com)/(?:embed-|)?([0-9A-Za-z]+)'

    def __init__(self):
        self.net = common.Net()

    def get_media_url(self, host, media_id):
        web_url = self.get_url(host, media_id)
        headers = {'User-Agent': common.FF_USER_AGENT}
        response = self.net.http_GET(web_url, headers=headers)
        html = response.content
        data = helpers.get_hidden(html)
        headers['Cookie'] = response.get_headers(as_dict=True).get('Set-Cookie', '')
        html = self.net.http_POST(web_url, headers=headers, form_data=data).content
        html = html.encode("utf-8")

        packed = re.findall('(eval\(function.*?)\s*</script>', html, re.DOTALL)
        if packed:

            js = ''
            for pack in packed:
                js += jsunpack.unpack(pack)

            sources = helpers.scrape_sources(js, patterns=['''(?P<url>[^"']+\.(?:m3u8|mp4))'''], result_blacklist='tmp')

            if sources: return helpers.pick_source(sources) + helpers.append_headers(headers)

        raise ResolverError('Unable to locate video')

    def get_url(self, host, media_id):
        return 'http://www.xvidstage.com/%s' % media_id

    @classmethod
    def _is_enabled(cls):
        return common.get_setting('XvidstageResolver_enabled') == 'true'

    @classmethod
    def _get_priority(cls):
        try:
            return int(common.get_setting('XvidstageResolver_priority')) - 1
        except:
            return 99
