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
import urlparse
import kodi
import log_utils
from constants import RESOLVER_DIR

RUNPLUGIN_EXCEPTIONS = ['plugin.video.twitch']


def resolve(url, title=''):
    import urlresolver
    urlresolver.add_plugin_dirs(RESOLVER_DIR)
    log_utils.log('Attempting to resolve: |{0!s}|'.format(url), log_utils.LOGDEBUG)
    source = urlresolver.HostedMediaFile(url=url, title=title, include_disabled=False)
    if not source:
        log_utils.log('Not supported by URLResolver: |{0!s}|'.format(url), log_utils.LOGDEBUG)
        return None
    try:
        resolved = source.resolve()
    except:
        resolved = None
    if not resolved or not isinstance(resolved, basestring):
        log_utils.log('Unable to resolve: |{0!s}|'.format(url), log_utils.LOGDEBUG)
        return None
    else:
        return resolved


def scrape(url, title=''):
    from urlresolver import common, scrape_supported, choose_source, HostedMediaFile
    from urlresolver.plugins.lib import jsunpack
    from urlresolver.plugins.lib.helpers import pick_source, append_headers

    net = common.Net()
    parsed_url = urlparse.urlparse(url)
    headers = {'User-Agent': common.FF_USER_AGENT,
               'Referer': '%s://%s' % (parsed_url.scheme, parsed_url.hostname)}
    log_utils.log('Attempting to scrape sources: |{0!s}|'.format(url), log_utils.LOGDEBUG)

    def _update_cookie(_headers):
        set_cookie = _headers.get('Set-Cookie', None)
        if set_cookie:
            cookie = {'Cookie': set_cookie}
            headers.update(cookie)

    try:
        response = net.http_HEAD(url, headers=headers)
        response_headers = response.get_headers(as_dict=True)
        if 'text/html' in response_headers.get('Content-Type', ''):
            _update_cookie(response_headers)
            response = net.http_GET(url, headers=headers)
            _update_cookie(response.get_headers(as_dict=True))
            html = response.content
        else:
            raise Exception
    except:
        return None

    def _parse_to_list(_html, regex):
        matches = []
        for i in re.finditer(regex, _html, re.DOTALL):
            match = i.group(1)
            parsed_match = urlparse.urlparse(match)
            sub_label = parsed_match.path.split('.')[-1]
            matches.append(('%s[%s]' % (parsed_match.hostname, sub_label), match))
        return matches

    unresolved_source_list = scrape_supported(html)
    unresolved_source_list += scrape_supported(html, regex='''<iframe.*?src\s*=\s*['"]([^'"]+)''')
    unresolved_source_list += scrape_supported(html, regex='''data-lazy-src\s*=\s*['"]([^'"]+)''')
    unresolved_source_list += scrape_supported(html, regex='''<script.*?src\s*=\s*['"]([^'"]+)''')
    hmf_list = []
    for source in unresolved_source_list:
        host = urlparse.urlparse(source).hostname
        hmf_list.append(HostedMediaFile(source, title=host))
    if hmf_list:
        chosen = choose_source(hmf_list)
        if chosen:
            return resolve(chosen.get_url(), title=title)
        else:
            return None
    else:
        unpacked = ''
        for packed in re.finditer('(eval\(function.*?)</script>', html, re.DOTALL):
            try:
                unpacked_data = jsunpack.unpack(packed.group(1))
                unpacked_data = unpacked_data.replace('\\\'', '\'')
                unpacked += unpacked_data
            except:
                pass

        html += unpacked
        source_list = _parse_to_list(html, '''video\s+src\s*=\s*['"]([^'"]+)''')
        source_list += _parse_to_list(html, '''source\s+src\s*=\s*['"]([^'"]+)''')
        source_list += _parse_to_list(html, '''["']?\s*file\s*["']?\s*[:=]\s*["']([^"']+)''')
        source_list += _parse_to_list(html, '''["']?\s*url\s*["']?\s*[:=]\s*["']([^"']+)''')

        if source_list:
            source = pick_source(source_list)
            if source:
                source += append_headers(headers)
            return source
        else:
            return None


def play_this(item, title='', thumbnail='', player=True):
    stream_url = resolve(item, title=title)

    if not stream_url:
        stream_url = scrape(item, title=title)

    if not stream_url:
        stream_url = item

    if stream_url:
        if any(plugin_id in stream_url for plugin_id in RUNPLUGIN_EXCEPTIONS):
            log_utils.log('Running plugin: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
            kodi.execute_builtin('RunPlugin(%s)' % stream_url)
        else:
            playback_item = kodi.ListItem(label=title, thumbnailImage=thumbnail, path=stream_url)
            playback_item.setProperty('IsPlayable', 'true')
            playback_item.setInfo('video', {'title': playback_item.getLabel()})
            playback_item.addStreamInfo('video', {})

            if player:
                log_utils.log('Play using Player(): |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                kodi.Player().play(stream_url, playback_item)
            else:
                log_utils.log('Play using set_resolved_url: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                kodi.set_resolved_url(playback_item)
