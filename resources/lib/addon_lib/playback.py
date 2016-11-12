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
from urlresolver import common, add_plugin_dirs, scrape_supported, choose_source, HostedMediaFile
from urlresolver.plugins.lib.helpers import pick_source, append_headers, scrape_sources, parse_smil_source_list
from constants import RESOLVER_DIR

RUNPLUGIN_EXCEPTIONS = ['plugin.video.twitch']
dash_supported = common.has_addon('inputstream.mpd')
net = common.Net()


def __get_content_type_and_headers(url):
    # returns content-type, headers
    parsed_url = urlparse.urlparse(url)
    headers = {'User-Agent': common.FF_USER_AGENT,
               'Referer': '%s://%s' % (parsed_url.scheme, parsed_url.hostname)}

    try:
        response = net.http_HEAD(url, headers=headers)
    except:
        return '', ''

    response_headers = response.get_headers(as_dict=True)
    headers.update({'Cookie': response_headers.get('Set-Cookie', '')})

    ctype_header = response_headers.get('Content-Type', '')

    try:
        media, subtype = re.findall('([a-z\-]+)/([a-z0-9\-+.]+);?', ctype_header, re.DOTALL)[0]
        content_type = media
        if (content_type == 'application') and (subtype == 'dash+xml'):
            content_type = 'mpd'
    except:
        content_type = ctype_header

    log_utils.log('HEAD Request returned Content-Type: |{0!s}| updated Headers: |{1!s}|'
                  .format(content_type, headers), log_utils.LOGDEBUG)
    return content_type, headers


def __get_html_and_headers(url, headers):
    try:
        response = net.http_GET(url, headers=headers)
        response_headers = response.get_headers(as_dict=True)
        cookie = response_headers.get('Set-Cookie', '')
        if cookie:
            headers['Cookie'] = headers.get('Cookie', '') + cookie

        log_utils.log('GET Request updated Headers: |{0!s}|'.format(headers), log_utils.LOGDEBUG)
        return response.content, headers
    except:
        return '', ''


def resolve(url, title=''):
    add_plugin_dirs(RESOLVER_DIR)
    log_utils.log('Attempting to resolve: |{0!s}|'.format(url), log_utils.LOGDEBUG)
    source = HostedMediaFile(url=url, title=title, include_disabled=False)
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


def scrape(html, title=''):
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

    return None


def play_this(item, title='', thumbnail='', player=True):
    stream_url = None
    content_type = 'video'
    is_dash = False

    if not item.startswith('plugin://'):
        content_type, headers = __get_content_type_and_headers(item)
        if content_type == 'video' or content_type == 'audio' or content_type == 'image' or content_type == 'mpd':
            stream_url = item + append_headers(headers)
            if content_type == 'mpd':
                content_type = 'video'
                if not dash_supported:
                    stream_url = None

        elif content_type == 'text':
            content_type = 'video'
            stream_url = resolve(item, title=title)
            if stream_url:
                if '.mpd' in stream_url or dash_supported:
                    is_dash = True
                    if '.mpd' not in stream_url:
                        content_type, _headers = __get_content_type_and_headers(stream_url)
                        if content_type != 'mpd':
                            is_dash = False
                            stream_url = None

            if not stream_url:
                html, headers = __get_html_and_headers(item, headers)
                blacklist = ['dl', 'error.']
                if not dash_supported:
                    blacklist += ['.mpd']
                sources = scrape_sources(html, result_blacklist=blacklist)
                if sources:
                    headers.update({'Referer': item})
                    source = pick_source(sources)
                    if '.smil' in source:
                        smil, headers = __get_html_and_headers(source, headers)
                        source = pick_source(parse_smil_source_list(smil))
                    elif '.mpd' in source or dash_supported:
                        is_dash = True
                        if '.mpd' not in source:
                            content_type, _headers = __get_content_type_and_headers(source)
                            if content_type != 'mpd':
                                is_dash = False

                    stream_url = source + append_headers(headers)

                if not stream_url:
                    stream_url = scrape(html, title=title)
                    if stream_url:
                        if '.mpd' in stream_url or dash_supported:
                            is_dash = True
                            if '.mpd' not in stream_url:
                                content_type, _headers = __get_content_type_and_headers(stream_url)
                                if content_type != 'mpd':
                                    is_dash = False
                                    stream_url = None

    else:
        stream_url = item

    if is_dash and not dash_supported:
        stream_url = None

    if stream_url:
        if any(plugin_id in stream_url for plugin_id in RUNPLUGIN_EXCEPTIONS):
            log_utils.log('Running plugin: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
            kodi.execute_builtin('RunPlugin(%s)' % stream_url)
        else:
            playback_item = kodi.ListItem(label=title, thumbnailImage=thumbnail, path=stream_url)
            if is_dash:
                playback_item.setProperty('inputstreamaddon', 'inputstream.mpd')
            playback_item.setProperty('IsPlayable', 'true')
            playback_item.setInfo(content_type, {'title': playback_item.getLabel()})
            playback_item.addStreamInfo(content_type, {})

            if player:
                log_utils.log('Play using Player(): |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                kodi.Player().play(stream_url, playback_item)
            else:
                log_utils.log('Play using set_resolved_url: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                kodi.set_resolved_url(playback_item)
