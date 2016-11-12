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
import socket
import kodi
import utils
import log_utils
from urllib2 import quote
from urlresolver import common, add_plugin_dirs, scrape_supported, choose_source, HostedMediaFile
from urlresolver.plugins.lib.helpers import pick_source, scrape_sources, parse_smil_source_list
from urlresolver.plugins.lib.helpers import append_headers as __append_headers

from constants import RESOLVER_DIR

socket.setdefaulttimeout(30)

RUNPLUGIN_EXCEPTIONS = ['plugin.video.twitch']
dash_supported = common.has_addon('inputstream.mpd')
net = common.Net()


def append_headers(headers):
    if headers.has_key('Accept-Encoding'):
        del headers['Accept-Encoding']
    if headers.has_key('Host'):
        del headers['Host']
    return __append_headers(headers)


def __get_content_type_and_headers(url, headers=None):
    # returns content-type, headers
    parsed_url = urlparse.urlparse(url)
    if headers is None:
        headers = {'User-Agent': common.FF_USER_AGENT,
                   'Host': parsed_url.hostname,
                   'Accept-Language': 'en',
                   'Accept-Encoding': 'gzip, deflate',
                   'Connection': 'Keep-Alive',
                   'Referer': '%s://%s' % (parsed_url.scheme, parsed_url.hostname)}

    try:
        response = net.http_HEAD(url, headers=headers)
    except:
        return 'video', headers

    response_headers = response.get_headers(as_dict=True)
    headers.update({'Cookie': response_headers.get('Set-Cookie', '')})

    ctype_header = response_headers.get('Content-Type', 'video')

    try:
        media, subtype = re.findall('([a-z\-]+)/([a-z0-9\-+.]+);?', ctype_header, re.DOTALL)[0]
        content_type = media
        if (content_type == 'application') and (subtype == 'dash+xml'):
            content_type = 'mpd'
        elif (content_type == 'application') and (subtype == 'smil+xml'):
            content_type = 'smil'
        elif (content_type == 'application') and ('mpeg' in subtype):
            content_type = 'video'
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


def play_this(item, title='', thumbnail='', player=True, history=None):
    if history is None:
        history = kodi.get_setting('history-add-on-play') == "true"
    stream_url = None
    content_type = 'video'
    is_dash = False
    direct = ['rtmp:', 'rtmpe:', 'ftp:', 'ftps:', 'special:', 'plugin:']

    if item.startswith('http'):
        content_type, headers = __get_content_type_and_headers(item)
        log_utils.log('Source |{0}| has media type |{1}|'.format(item, content_type), log_utils.LOGDEBUG)
        if content_type == 'video' or content_type == 'audio' or content_type == 'image' \
                or content_type == 'mpd' or content_type == 'smil':
            source = item
            if content_type == 'smil':
                content_type = 'video'
                smil, _headers = __get_html_and_headers(item, headers)
                source = pick_source(parse_smil_source_list(smil))
            elif content_type == 'mpd':
                content_type = 'video'
                if not dash_supported:
                    source = None
            if source:
                stream_url = source + append_headers(headers)
        elif content_type == 'text':
            content_type = 'video'
            headers.update({'Referer': item})
            source = resolve(item, title=title)
            if source:
                log_utils.log('Source |{0}| was |URLResolver supported|'.format(source), log_utils.LOGDEBUG)
                if '.smil' in source:
                    smil, _headers = __get_html_and_headers(item, headers)
                    source = pick_source(parse_smil_source_list(smil))
                elif '.mpd' in source and not dash_supported:
                    source = None
                if source:
                    stream_url = source
                    if not stream_url.startswith('plugin://'):
                        stream_url += append_headers(headers)

            if not stream_url:
                html, headers = __get_html_and_headers(item, headers)
                blacklist = ['dl', 'error.']
                if not dash_supported:
                    blacklist += ['.mpd']
                sources = scrape_sources(html, result_blacklist=blacklist)
                if sources:
                    source = pick_source(sources)
                    log_utils.log('Source |{0}| found by |Scraping for sources|'.format(source), log_utils.LOGDEBUG)
                    if '.smil' in source:
                        smil, _headers = __get_html_and_headers(item, headers)
                        source = pick_source(parse_smil_source_list(smil))
                    elif '.mpd' in source and not dash_supported:
                        source = None
                    if source:
                        stream_url = source + append_headers(headers)

                if not stream_url:
                    source = scrape(html, title=title)
                    if source:
                        log_utils.log('Source |{0}| found by |Scraping for URLResolver supported|'
                                      .format(source), log_utils.LOGDEBUG)
                        if '.smil' in source:
                            smil, _headers = __get_html_and_headers(item, headers)
                            source = pick_source(parse_smil_source_list(smil))
                        elif '.mpd' in source:
                            if not dash_supported:
                                source = None
                        if source:
                            stream_url = source
                            if not stream_url.startswith('plugin://'):
                                stream_url += append_headers(headers)

    elif any(item.startswith(p) for p in direct):
        log_utils.log('Source |{0}| may be supported'.format(item), log_utils.LOGDEBUG)
        stream_url = item

    if is_dash and (not dash_supported):
        stream_url = None

    if stream_url and (content_type == 'video' or content_type == 'audio' or content_type == 'image'):
        if history:
            play_history = utils.PlayHistory()
            history_item = item
            if '%' not in item:
                history_item = quote(item)
            log_utils.log('Adding source |{0}| to history with content_type |{1}|'
                          .format(item, content_type), log_utils.LOGDEBUG)
            play_history.add(history_item, content_type)
            if player == 'history':
                return
        if any(plugin_id in stream_url for plugin_id in RUNPLUGIN_EXCEPTIONS):
            log_utils.log('Running plugin: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
            kodi.execute_builtin('RunPlugin(%s)' % stream_url)
        else:
            playback_item = kodi.ListItem(label=title, path=stream_url)
            playback_item.setArt({'thumb': thumbnail})
            playback_item.setProperty('IsPlayable', 'true')
            info = {'title': playback_item.getLabel()}
            if content_type == 'image':
                info.update({'picturepath': stream_url})
            playback_item.setInfo(content_type, info)
            if content_type == 'video' or content_type == 'audio':
                playback_item.addStreamInfo(content_type, {})
                if is_dash:
                    playback_item.setProperty('inputstreamaddon', 'inputstream.mpd')
            if player:
                log_utils.log('Play using Player(): |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                kodi.Player().play(stream_url, playback_item)
            else:
                log_utils.log('Play using set_resolved_url: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                kodi.set_resolved_url(playback_item)
