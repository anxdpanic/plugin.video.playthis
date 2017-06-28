"""
    Copyright (C) 2017 tknorris

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
from urlresolver.plugins.lib import helpers
from urlresolver.resolver import UrlResolver, ResolverError
from urlresolver import common


class ExternalTheVidResolver(UrlResolver):
    name = "TheVid"
    domains = ["thevid.net"]
    pattern = '(?://|\.)(thevid\.net)/(?:video|e|v)/([A-Za-z0-9]+)'

    def get_media_url(self, host, media_id):
        return helpers.get_media_url(self.get_url(host, media_id), patterns=['''vurl\w+="(?P<url>[^"]+)'''], result_blacklist=['rick', 'logger', 'iframe']).replace(' ', '%20')

    def get_url(self, host, media_id):
        return self._default_get_url(host, media_id, template='http://{host}/e/{media_id}/')

    @classmethod
    def _is_enabled(cls):
        return common.get_setting('TheVidResolver_enabled') == 'true'

    @classmethod
    def _get_priority(cls):
        try:
            return int(common.get_setting('TheVidResolver_priority')) - 1
        except:
            return 99
