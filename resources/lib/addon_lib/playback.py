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
import urllib2
import struct
import socket
import kodi
import utils
import log_utils
from urlresolver import common, add_plugin_dirs, choose_source, HostedMediaFile
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


def __get_html_and_headers(url, headers):
    try:
        response = net.http_GET(url, headers=headers)
        response_headers = response.get_headers(as_dict=True)
        cookie = response_headers.get('Set-Cookie', '')
        if cookie:
            headers['Cookie'] = headers.get('Cookie', '') + cookie

        log_utils.log('GET request updated headers: |{0!s}|'.format(headers), log_utils.LOGDEBUG)
        return response.content, headers
    except:
        return '', headers


def __get_qt_atom_url(url, headers):
    log_utils.log('Attempting to get url from quicktime atom: |{0!s}|'.format(url), log_utils.LOGDEBUG)
    try:
        mov, headers = __get_html_and_headers(url, headers)
        r = re.search('moov.*?rmra.*?rdrf.*?url (....)(.*)', mov)
        l = struct.unpack("!I", r.group(1))[0]
        return r.group(2)[:l], headers
    except:
        return None, headers


def __get_potential_type(url):
    potential_type = 'text'
    if any(ext in url for ext in kodi.get_supported_media('video').split('|')):
        potential_type = 'video'
    elif any(ext in url for ext in kodi.get_supported_media('music').split('|')):
        potential_type = 'audio'
    elif any(ext in url for ext in kodi.get_supported_media('picture').split('|')):
        potential_type = 'image'
    return potential_type


def __get_content_type_and_headers(url, headers=None):
    # returns content-type, headers
    url_override = None
    parsed_url = urlparse.urlparse(url)
    if headers is None:
        headers = {'User-Agent': common.FF_USER_AGENT,
                   'Host': parsed_url.hostname,
                   'Accept-Language': 'en',
                   'Accept-Encoding': 'gzip, deflate',
                   'Connection': 'Keep-Alive',
                   'Referer': '%s://%s' % (parsed_url.scheme, parsed_url.hostname)}

    potential_type = __get_potential_type(url)

    try:
        response = net.http_HEAD(url, headers=headers)
        redirect = response.get_url()
        if redirect != url:
            log_utils.log('Head request following redirect to: |{0!s}|'.format(url_override), log_utils.LOGDEBUG)
            url_override = redirect
            response = net.http_HEAD(url_override, headers=headers)
    except:
        return potential_type, headers, None

    response_headers = response.get_headers(as_dict=True)
    headers.update({'Cookie': response_headers.get('Set-Cookie', '')})

    clength_header = response_headers.get('Content-Length', '')
    ctype_header = response_headers.get('Content-Type', potential_type)

    try:
        media, subtype = re.findall('([a-z\-]+)/([a-z0-9\-+.]+);?', ctype_header, re.DOTALL)[0]
        log_utils.log('HEAD request returned MIME type: |{0!s}/{1!s}| and headers: |{2!s}|'
                      .format(media, subtype, response_headers), log_utils.LOGDEBUG)
        content_type = media
        if (content_type == 'application') and (subtype == 'dash+xml'):
            content_type = 'mpd'
        elif (content_type == 'application') and (subtype == 'smil+xml'):
            content_type = 'smil'
        elif (content_type == 'application') and ('mpeg' in subtype):
            content_type = 'video'
        elif (content_type == 'application') and (subtype == 'octet-stream') and \
                any(ext in url for ext in ['.iso', '.bin']):
            content_type = 'video'
        elif (content_type == 'video') and ('quicktime' in subtype):
            try:
                content_length = int(clength_header)
                if content_length <= 10000:
                    url_override, headers = __get_qt_atom_url(url, headers)
            except:
                pass
    except:
        content_type = ctype_header

    log_utils.log('HEAD request complete updated headers: |{1!s}| using media type: |{0!s}|'
                  .format(content_type, headers), log_utils.LOGDEBUG)
    return content_type, headers, url_override


def __check_for_new_url(url):
    result = url
    if 'google' in url:
        try:
            result = \
                urllib2.unquote(re.findall('cache:[a-zA-Z0-9_\-]+:(.+?)\+&amp;', url)[-1])
        except:
            try:
                result = urllib2.unquote(re.findall('google\.[a-z]+/.*?url=(.+?)&', url)[-1])
            except:
                pass
    elif 'reddit' in url:
        try:
            result = \
                urllib2.unquote(re.findall('http[s]?://out\.reddit\.com/.*?url=(.+?)&amp;', url)[-1])
        except:
            pass
    return result


def scrape_supported(html, regex=None, host_only=False):
    # modified version of scrape supported from urlresolver to support additional label match group, and filtering
    host_cache = {}
    if regex is None: regex = '''href\s*=\s*['"]([^'"]+)'''
    links = []
    filter = ['jquery', '/ads.js', '-ads.js', 'data:', 'blob:' '/search', 'tab=', 'usp=']
    for match in re.finditer(regex, html):
        stream_url = match.group(1)
        if any(item in stream_url for item in filter) or stream_url == '#' or any(stream_url == t[1] for t in links):
            continue
        stream_url = __check_for_new_url(stream_url).replace(r'\\', '')

        host = urlparse.urlparse(stream_url).hostname
        label = host
        if (len(match.groups()) > 1) and (match.group(2) is not None):
            label = match.group(2)

        if host_only:
            if host is None:
                continue

            if host in host_cache:
                if host_cache[host]:
                    links.append(stream_url)
                continue
            else:
                hmf = HostedMediaFile(host=host, media_id='dummy')  # use dummy media_id to allow host validation
        else:
            hmf = HostedMediaFile(url=stream_url)

        is_valid = hmf.valid_url()
        host_cache[host] = is_valid
        if is_valid:
            links.append((label, stream_url))
    return links


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
    src_match_regex = '''\s*=\s*['"]([^'"]+)'''
    log_utils.log('Scraping for data-hrefs', log_utils.LOGDEBUG)
    unresolved_source_list = \
        scrape_supported(html, '''data-href%s(?:.*?>\s*([^<]+).*?</a>)''' % src_match_regex)
    log_utils.log('Scraping for hrefs', log_utils.LOGDEBUG)
    unresolved_source_list += \
        scrape_supported(html, '''href%s(?:.*?>\s*([^<]+).*?</a>)''' % src_match_regex)
    log_utils.log('Scraping for data-lazy-srcs', log_utils.LOGDEBUG)
    unresolved_source_list += \
        scrape_supported(html, regex='''data-lazy-src%s''' % src_match_regex)
    log_utils.log('Scraping for srcs', log_utils.LOGDEBUG)
    unresolved_source_list += \
        scrape_supported(html, regex='''src%s''' % src_match_regex)

    hmf_list = []
    for label, source in unresolved_source_list:
        hmf_list.append(HostedMediaFile(source, title=label))

    if hmf_list:
        chosen = choose_source(hmf_list)
        if chosen:
            return resolve(chosen.get_url(), title=title)

    return None


def play_this(item, title='', thumbnail='', player=True, history=None):
    if history is None:
        history = kodi.get_setting('history-add-on-play') == "true"
    stream_url = None
    headers = None
    content_type = 'video'
    is_dash = False
    direct = ['rtmp:', 'rtmpe:', 'ftp:', 'ftps:', 'special:', 'plugin:']
    force_scrape_supported = ['reddit.com', 'google.']
    working_dialog = kodi.WorkingDialog()
    with working_dialog:
        if item.startswith('http'):
            url_override = __check_for_new_url(item)
            if item != url_override:
                item = url_override
                log_utils.log('Source |{0}| has been replaced by |{1}|'.format(item, url_override), log_utils.LOGDEBUG)

            content_type, headers, url_override = __get_content_type_and_headers(item)
            if url_override:
                log_utils.log('Source |{0}| has been replaced by |{1}|'.format(item, url_override), log_utils.LOGDEBUG)
                item = url_override
            log_utils.log('Source |{0}| has media type |{1}|'.format(item, content_type), log_utils.LOGDEBUG)
            working_dialog.update(20)
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
                    stream_url = source

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
                        stream_url = source.replace(r'\\', '')

                working_dialog.update(40)
                if not stream_url:
                    html, headers = __get_html_and_headers(item, headers)
                    if not any(override in item for override in force_scrape_supported):
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
                                stream_url = source.replace(r'\\', '')

                    working_dialog.update(60)
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
                                stream_url = source.replace(r'\\', '')

        elif any(item.startswith(p) for p in direct):
            working_dialog.update(80)
            log_utils.log('Source |{0}| may be supported'.format(item), log_utils.LOGDEBUG)
            stream_url = item

        if is_dash and (not dash_supported):
            stream_url = None

        if stream_url and (content_type == 'video' or content_type == 'audio' or content_type == 'image'):
            working_dialog.update(99)
            if history or player == 'history':
                play_history = utils.PlayHistory()
                history_item = item
                if '%' not in item:
                    history_item = urllib2.quote(item)
                log_utils.log('Adding source |{0}| to history with content_type |{1}|'
                              .format(item, content_type), log_utils.LOGDEBUG)
                play_history.add(history_item, content_type)
                if player == 'history':
                    return

            if (not stream_url.startswith('plugin://')) and ('|' not in stream_url) and (headers is not None):
                stream_url += append_headers(headers)
            if len(stream_url.split('|')) > 2:
                url_parts = stream_url.split('|')
                stream_url = '%s|%s' % (url_parts[0], url_parts[-1])

            if any(plugin_id in stream_url for plugin_id in RUNPLUGIN_EXCEPTIONS):
                log_utils.log('Running plugin: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                kodi.execute_builtin('RunPlugin(%s)' % stream_url)
            else:
                if content_type == 'image':
                    player_open = {'jsonrpc': '2.0',
                                   'id': '1',
                                   'method': 'Player.Open',
                                   'params': {'item': {'file': stream_url}}}
                    log_utils.log('Play using jsonrpc method Player.Open: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                    kodi.execute_jsonrpc(player_open)
                else:
                    info = {'title': title}
                    playback_item = kodi.ListItem(label=title, iconImage=thumbnail, path=stream_url)
                    playback_item.setProperty('IsPlayable', 'true')
                    playback_item.setArt({'thumb': thumbnail})
                    playback_item.addStreamInfo(content_type, {})
                    if is_dash:
                        playback_item.setProperty('inputstreamaddon', 'inputstream.mpd')
                    playback_item.setInfo(content_type, info)
                    if player:
                        log_utils.log('Play using Player(): |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                        kodi.Player().play(stream_url, playback_item)
                    else:
                        log_utils.log('Play using set_resolved_url: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                        kodi.set_resolved_url(playback_item)
        else:
            log_utils.log('Found no potential sources: |{0!s}|'.format(item), log_utils.LOGDEBUG)
