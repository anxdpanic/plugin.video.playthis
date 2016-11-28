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
import cache
from HTMLParser import HTMLParser
from urlresolver import common, add_plugin_dirs, HostedMediaFile
from urlresolver.plugins.lib.helpers import pick_source, parse_smil_source_list, get_hidden, add_packed_data
from urlresolver.plugins.lib.helpers import append_headers as __append_headers
from YDStreamExtractor import _getYoutubeDLVideo
from youtube_dl import extractor as __extractor
from constants import RESOLVER_DIR

socket.setdefaulttimeout(30)

RUNPLUGIN_EXCEPTIONS = ['plugin.video.twitch']
dash_supported = common.has_addon('inputstream.mpd')
net = common.Net()

user_cache_limit = int(kodi.get_setting('cache-expire-time'))
resolver_cache_limit = 0.11
cache.cache_enabled = user_cache_limit > 0


def append_headers(headers):
    if headers.has_key('Accept-Encoding'):
        del headers['Accept-Encoding']
    if headers.has_key('Host'):
        del headers['Host']
    return __append_headers(headers)


def get_default_headers(url):
    parsed_url = urlparse.urlparse(url)
    return {'User-Agent': common.FF_USER_AGENT,
            'Host': parsed_url.hostname,
            'Accept-Language': 'en',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'Keep-Alive',
            'Referer': '%s://%s' % (parsed_url.scheme, parsed_url.hostname)}


def __get_html_and_headers(url, headers=None):
    if headers is None:
        headers = get_default_headers(url)
    try:
        response = net.http_GET(url, headers=headers)
        response_headers = response.get_headers(as_dict=True)
        cookie = response_headers.get('Set-Cookie', '')
        if cookie:
            headers['Cookie'] = headers.get('Cookie', '') + cookie
        html = response.content
        redirect = response.get_url()
        if ('reddit' in redirect) and ('over18' in redirect):
            post_headers = {}
            post_headers.update(
                {'User-Agent': common.FF_USER_AGENT, 'Content-Type': 'application/x-www-form-urlencoded'})
            data = get_hidden(html)
            data.update({'over18': 'yes'})
            response = net.http_POST(response.get_url(), form_data=data, headers=post_headers)
            response_headers = response.get_headers(as_dict=True)
            cookie = response_headers.get('Set-Cookie', '')
            if cookie:
                headers['Cookie'] = headers.get('Cookie', '')
            html = response.content
        log_utils.log('GET request updated headers: |{0!s}|'.format(headers), log_utils.LOGDEBUG)
        return html, headers
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
    if any(ext in url for ext in kodi.get_supported_media('music').split('|')):
        potential_type = 'audio'
    elif any(ext in url for ext in kodi.get_supported_media('picture').split('|')):
        potential_type = 'image'
    elif any(ext in url for ext in kodi.get_supported_media('video').split('|')):
        potential_type = 'video'

    return potential_type


@cache.cache_function(cache_limit=168)
def __get_gen_extractors():
    return __extractor.gen_extractors()


@cache.cache_function(cache_limit=168)
def __get_gen_extractors_names():
    names = set()
    extractors = __get_gen_extractors()
    for extractor in extractors:
        if extractor.IE_NAME == 'generic': continue
        name = extractor.IE_NAME.lower().split(':')[0]
        if isinstance(name, unicode):
            name = name.encode('utf-8')
        names.add(name)
    return list(names)


def ytdl_supported(url):
    extractors = __get_gen_extractors()
    for extractor in extractors:
        if extractor.suitable(url) and extractor.IE_NAME != 'generic':
            return True
    return False


def ytdl_candidate(url):
    names = __get_gen_extractors_names()
    return any(name in url for name in names)


def __get_content_type_and_headers(url, headers=None):
    url_override = None
    if headers is None:
        headers = get_default_headers(url)

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
    if 'google' in url:
        try:
            return urllib2.unquote(re.findall('cache:[a-zA-Z0-9_\-]+:(.+?)\+&amp;', url)[-1])
        except:
            try:
                return urllib2.unquote(re.findall('google[a-z]+\.[a-z]+/.*url=(.+?)[&$]', url)[-1])
            except:
                pass
    if 'reddit' in url:
        try:
            return urllib2.unquote(re.findall('http[s]?://out\.reddit\.com/.*?url=(.+?)&amp;', url)[-1])
        except:
            pass
    return url


def scrape_supported(url, html, regex):
    parsed_url = urlparse.urlparse(url)
    links = []
    _filter = ['.js', 'data:', 'blob:', 'tab=', 'usp=', '/pixel.', '/1x1.', 'javascript:', 'rss.', 'blank.', '.rss']
    sources = []
    progress_dialog = kodi.ProgressDialog('%s...' % kodi.i18n('scraping_for_potential_urls'), '%s: %s' % (kodi.i18n('source'), url), ' ', timer=2)
    canceled = False
    with progress_dialog:
        while not progress_dialog.is_canceled():
            new_iter = re.findall(regex, html, re.DOTALL)
            len_iter = len(new_iter)
            for index, match in enumerate(new_iter):
                if progress_dialog.is_canceled():
                    canceled = True
                    break
                percent = int((float(index) / float(len_iter)) * 100)
                stream_url = match[0]
                if stream_url == '#' or stream_url == '//' or '/' not in stream_url or not re.match('^[hruf:/].+', stream_url) or \
                        any(item in stream_url for item in _filter) or any(stream_url == t[1] for t in links):
                    progress_dialog.update(percent, kodi.i18n('preparing_results'), '%s: %s' % (kodi.i18n('discarded'), '%s' % stream_url), ' ')
                    continue
                stream_url = __check_for_new_url(stream_url).replace(r'\\', '')
                if stream_url.startswith('//'):
                    stream_url = '%s:%s' % (parsed_url.scheme, stream_url)
                elif stream_url.startswith('/'):
                    stream_url = '%s://%s%s' % (parsed_url.scheme, parsed_url.hostname, stream_url)

                host = urlparse.urlparse(stream_url).hostname
                label = host.encode('utf-8')
                if (len(match) > 2) and (match[2] is not None) and (match[2].strip()) and (host not in match[2]):
                    label = match[2].strip()
                elif (len(match) > 1) and (match[1] is not None) and (match[1].strip()) and (host not in match[1]):
                    label = match[1].strip()
                if not isinstance(label, unicode):
                    label = label.decode('utf-8', 'ignore')
                failed_unescape = False
                try:
                    label = HTMLParser().unescape(label)
                except:
                    failed_unescape = True
                try:
                    if not failed_unescape:
                        label = HTMLParser().unescape(label)
                except:
                    pass
                progress_dialog.update(percent, kodi.i18n('preparing_results'), '%s: %s' % (kodi.i18n('added'), label), stream_url)
                sources.append((label, stream_url))
            if progress_dialog.is_canceled():
                canceled = True
            break
        if canceled:
            return []

    progress_dialog = kodi.ProgressDialog('%s...' % kodi.i18n('scraping_for_potential_urls'), '%s: %s' % (kodi.i18n('source'), url), ' ', timer=2)
    canceled = False
    with progress_dialog:
        while not progress_dialog.is_canceled():
            len_iter = len(sources)
            for index, source in enumerate(sources):
                if progress_dialog.is_canceled():
                    canceled = True
                    break
                percent = int((float(index) / float(len_iter)) * 100)
                label = source[0]
                stream_url = source[1]
                hmf = HostedMediaFile(url=stream_url)
                potential_type = __get_potential_type(stream_url)
                is_valid = hmf.valid_url()
                is_valid_type = (potential_type != 'audio') and (potential_type != 'image')

                if is_valid and is_valid_type:
                    progress_dialog.update(percent, kodi.i18n('check_for_support'),
                                           '%s [%s]: %s' % (kodi.i18n('support_potential'), 'video', 'URLResolver'),
                                           '[%s]: %s' % (label, stream_url))
                    links.append((label, stream_url, True, 'video'))
                    continue
                else:
                    if potential_type == 'text':
                        if ytdl_candidate(stream_url):
                            ytdl_valid = ytdl_supported(stream_url)
                            if ytdl_valid:
                                progress_dialog.update(percent, kodi.i18n('check_for_support'),
                                                       '%s [%s]: %s' % (kodi.i18n('support_potential'), 'video', 'youtube-dl'),
                                                       '[%s]: %s' % (label, stream_url))
                                links.append((label, stream_url, True, 'video'))
                                continue
                        progress_dialog.update(percent, kodi.i18n('check_for_support'),
                                               '%s [%s]: %s' % (kodi.i18n('support_potential'), potential_type, 'None'),
                                               '[%s]: %s' % (label, stream_url))
                    else:
                        progress_dialog.update(percent, kodi.i18n('check_for_support'),
                                               '%s [%s]: %s' % (kodi.i18n('support_potential'), potential_type, 'Kodi'),
                                               '[%s]: %s' % (label, stream_url))
                    links.append((label, stream_url, False, potential_type))
                    continue
            if progress_dialog.is_canceled():
                canceled = True
            break
        if canceled:
            return []
    return links


@cache.cache_function(cache_limit=resolver_cache_limit)
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


@cache.cache_function(cache_limit=resolver_cache_limit)
def resolve_youtube_dl(url):
    label = None
    stream_url = None
    content_type = 'video'
    source = _getYoutubeDLVideo(url, resolve_redirects=True)
    if source:
        stream_url = source.selectedStream()['xbmc_url']
        title = source.title
        label = None if title.lower().startswith('http') else title
        try:
            label = HTMLParser().unescape(label)
        except:
            pass
        selected_stream = source.selectedStream()
        if 'ytdl_format' in selected_stream and 'formats' in selected_stream['ytdl_format']:
            formats = selected_stream['ytdl_format']['formats']
            format_id = selected_stream['formatID']
            format_index = next(index for (index, f) in enumerate(formats) if f['format_id'] == format_id)
            ext = formats[format_index]['ext']
            if ext:
                content_type = __get_potential_type('.' + ext)
    return stream_url, label, content_type


def __pick_source(sources):
    if len(sources) == 1:
        return sources[0][1]
    elif len(sources) > 1:
        listitem_sources = []
        for source in sources:
            title = source[0] if source[0] else kodi.i18n('unknown')
            icon = ''
            if source[3] == 'image':
                icon = source[1]
            l_item = kodi.ListItem(label=title, label2=source[3], iconImage=icon)
            l_item.setArt({'thumb': icon})
            listitem_sources.append(l_item)

        try:
            result = kodi.Dialog().select(kodi.i18n('choose_source'), list=listitem_sources, useDetails=True)
        except:
            result = kodi.Dialog().select(kodi.i18n('choose_source'),
                                          ['[%s] %s' % (source[3], source[0])
                                           if source[0]
                                           else '[%s] %s' % (source[3], kodi.i18n('unknown'))
                                           for source in sources])
        if result == -1:
            return None
        else:
            return sources[result]
    else:
        return None


@cache.cache_function(cache_limit=user_cache_limit)
def _scrape(url):
    unresolved_source_list = []
    html, headers = __get_html_and_headers(url)
    html = add_packed_data(html)

    def _to_list(items):
        for lstitem in items:
            if not any(lstitem[1] == t[1] for t in unresolved_source_list):
                unresolved_source_list.append(lstitem)
            else:
                if lstitem[0] not in lstitem[1]:
                    for idx, itm in enumerate(unresolved_source_list):
                        if lstitem[1] == itm[1]:
                            if itm[0] in itm[1]:
                                unresolved_source_list[idx] = lstitem
                                break

    log_utils.log('Scraping for iframes', log_utils.LOGDEBUG)
    _to_list(scrape_supported(url, html, '''iframe src\s*=\s*['"]([^'"]+)(?:[^>]+(?:title|alt)\s*=\s*['"]([^'"]+))?'''))
    log_utils.log('Scraping for hrefs', log_utils.LOGDEBUG)
    _to_list(scrape_supported(url, html, '''href\s*=\s*['"]([^'"]+)[^>]+(?:(?:(?:data-title|title)\s*=\s*['"]([^'"]+))?(?:[^>]*>([^<]+))?)'''))
    log_utils.log('Scraping for data-hrefs', log_utils.LOGDEBUG)
    _to_list(scrape_supported(url, html, '''data-href-url\s*=\s*['"]([^'"]+)[^>]+(?:(?:(?:data-title|title)\s*=\s*['"]([^'"]+))?(?:[^>]*>([^<]+))?)'''))
    log_utils.log('Scraping for data-lazy-srcs', log_utils.LOGDEBUG)
    _to_list(scrape_supported(url, html, '''data-lazy-src\s*=\s*['"]([^'"]+)(?:[^>]+(?:title|alt)\s*=\s*['"]([^'"]+))?'''))
    log_utils.log('Scraping for srcs', log_utils.LOGDEBUG)
    _to_list(scrape_supported(url, html, '''src(?<!iframe\s)\s*=\s*['"]([^'"]+)(?:[^>]+(?:title|alt)\s*=\s*['"]([^'"]+))?'''))

    result_list = []
    for item in unresolved_source_list:
        if item[3] != 'text':
            result_list.append(item)
    return result_list, headers


def scrape(url):
    result_list, headers = _scrape(url)
    if result_list:
        chosen = __pick_source(result_list)
        if chosen:
            if chosen[2]:
                label = None
                content_type = None
                resolved = resolve(chosen[1], title=chosen[0])
                if not resolved:
                    resolved, label, content_type = resolve_youtube_dl(chosen[1])
                label = chosen[0] if label is None else label
                content_type = chosen[3] if content_type is None else content_type
                return resolved, content_type, chosen[1], label, headers
            elif chosen[3] == 'text':
                resolved, label, content_type = resolve_youtube_dl(chosen[1])
                if resolved:
                    label = chosen[0] if label is None else label
                    return resolved, content_type, chosen[1], label, headers
            return chosen[1], chosen[3], None, chosen[0], headers
    return None, None, None, None, None


def __check_smil_dash(source, headers):
    if '.smil' in source:
        smil, _headers = __get_html_and_headers(source, headers)
        source = pick_source(parse_smil_source_list(smil))
    elif '.mpd' in source and not dash_supported:
        source = None
    return source


def play_this(item, title='', thumbnail='', player=True, history=None):
    if history is None:
        history = kodi.get_setting('history-add-on-play') == "true"
    override_history = kodi.get_setting('history-add-on-play') == "true"
    stream_url = None
    headers = None
    content_type = 'video'
    override_content_type = None
    is_dash = False
    direct = ['rtmp:', 'rtmpe:', 'ftp:', 'ftps:', 'special:', 'plugin:', 'udp:', 'upnp:']
    unresolved_source = None
    label = title
    source_label = label
    history_item = None

    if item.startswith('http'):
        progress_dialog = kodi.ProgressDialog('%s...' % kodi.i18n('resolving'), '%s:' % kodi.i18n('attempting_determine_type'), item)
        canceled = False
        with progress_dialog:
            while not progress_dialog.is_canceled():
                url_override = __check_for_new_url(item)
                if item != url_override:
                    log_utils.log('Source |{0}| has been replaced by |{1}|'.format(item, url_override), log_utils.LOGDEBUG)
                    progress_dialog.update(5, '%s: %s' % (kodi.i18n('source'), item), '%s: %s' % (kodi.i18n('replaced_with'), url_override), ' ')
                    item = url_override
                content_type, headers, url_override = __get_content_type_and_headers(item)
                if url_override:
                    log_utils.log('Source |{0}| has been replaced by |{1}|'.format(item, url_override), log_utils.LOGDEBUG)
                    progress_dialog.update(10, '%s: %s' % (kodi.i18n('source'), item), '%s: %s' % (kodi.i18n('replaced_with'), url_override), ' ')
                    item = url_override

                log_utils.log('Source |{0}| has media type |{1}|'.format(item, content_type), log_utils.LOGDEBUG)
                progress_dialog.update(20, '%s: %s' % (kodi.i18n('source'), item), '%s: %s' % (kodi.i18n('using_media_type'), content_type), ' ')
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
                    if progress_dialog.is_canceled():
                        break
                    progress_dialog.update(40, '%s: %s' % (kodi.i18n('source'), item), '%s: URLResolver' % kodi.i18n('attempt_resolve_with'), ' ')
                    content_type = 'video'
                    headers.update({'Referer': item})
                    source = resolve(item, title=title)
                    if source:
                        log_utils.log('Source |{0}| was |URLResolver supported|'.format(source), log_utils.LOGDEBUG)
                        source = __check_smil_dash(source, headers)
                        if source:
                            progress_dialog.update(98, '%s: %s' % (kodi.i18n('source'), item),
                                                   '%s: URLResolver' % kodi.i18n('attempt_resolve_with'),
                                                   '%s: %s' % (kodi.i18n('resolution_successful'), source))
                            stream_url = source

                    if not stream_url:
                        if progress_dialog.is_canceled():
                            break
                        progress_dialog.update(60, '%s: %s' % (kodi.i18n('source'), item), '%s: youtube-dl' % kodi.i18n('attempt_resolve_with'), ' ')
                        source, _ytdl_label, content_type = resolve_youtube_dl(item)
                        if source:
                            label = _ytdl_label if _ytdl_label is not None else label
                            log_utils.log('Source |{0}| found by |youtube-dl|'
                                          .format(source), log_utils.LOGDEBUG)
                            source = __check_smil_dash(source, headers)
                            if source:
                                progress_dialog.update(98, '%s: %s' % (kodi.i18n('source'), item),
                                                       '%s: youtube-dl' % kodi.i18n('attempt_resolve_with'),
                                                       '%s: %s' % (kodi.i18n('resolution_successful'), source))
                                stream_url = source

                if not progress_dialog.is_canceled():
                    progress_dialog.update(100, ' ', kodi.i18n('resolution_completed'), ' ')
                else:
                    canceled = True
                break

        if not stream_url and not canceled:
            content_type = 'executable'
            source, override_content_type, unresolved_source, source_label, headers = scrape(item)
            if source:
                log_utils.log('Source |{0}| found by |Scraping for supported|'
                              .format(source), log_utils.LOGDEBUG)
                if override_content_type == 'video':
                    source = __check_smil_dash(source, headers)
                if source:
                    stream_url = source

        if stream_url:
            stream_url = stream_url.replace(r'\\', '')

    elif any(item.startswith(p) for p in direct):
        log_utils.log('Source |{0}| may be supported'.format(item), log_utils.LOGDEBUG)
        stream_url = item

    if is_dash and (not dash_supported or not kodi.addon_enabled('inputstream.mpd')):
        stream_url = None

    if stream_url and (content_type == 'video' or content_type == 'audio' or content_type == 'image' or content_type == 'executable'):
        working_dialog = kodi.WorkingDialog()
        with working_dialog:
            play_history = utils.PlayHistory()
            working_dialog.update(20)
            if history or player == 'history':
                history_item = item
                if '%' not in history_item:
                    history_item = urllib2.quote(history_item)
                log_utils.log('Adding source |{0}| to history with content_type |{1}|'
                              .format(item, content_type), log_utils.LOGDEBUG)
                play_history.add(history_item, content_type, label if label else item)
            working_dialog.update(40)
            if override_content_type and override_history:
                history_item = stream_url
                if history_item.startswith('plugin://') or unresolved_source:
                    history_item = unresolved_source
                if '%' not in history_item:
                    history_item = urllib2.quote(history_item)
                log_utils.log('Adding source |{0}| to history with content_type |{1}|'
                              .format(unresolved_source, override_content_type), log_utils.LOGDEBUG)
                play_history.add(history_item, override_content_type, source_label)
            if player == 'history':
                return
            if history_item:
                kodi.refresh_container()
            working_dialog.update(60)
            if (not stream_url.startswith('plugin://')) and ('|' not in stream_url) and (headers is not None):
                stream_url += append_headers(headers)
            if len(stream_url.split('|')) > 2:
                url_parts = stream_url.split('|')
                stream_url = '%s|%s' % (url_parts[0], url_parts[-1])

            working_dialog.update(80)
            player_stopped = kodi.stop_player()
            if any(plugin_id in stream_url for plugin_id in RUNPLUGIN_EXCEPTIONS):
                log_utils.log('Running plugin: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                kodi.execute_builtin('RunPlugin(%s)' % stream_url)
            else:
                if override_content_type:
                    content_type = override_content_type

                if content_type == 'image':
                    player_open = {'jsonrpc': '2.0', 'id': 1, 'method': 'Player.Open', 'params': {'item': {'file': stream_url}}}
                    log_utils.log('Play using jsonrpc method Player.Open: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                    response = kodi.execute_jsonrpc(player_open)
                else:
                    info = {'title': source_label}
                    art = {'icon': thumbnail, 'thumb': thumbnail}
                    playback_item = kodi.ListItem(label=title, path=stream_url)
                    playback_item.setProperty('IsPlayable', 'true')
                    if kodi.get_kodi_version().major < 16:
                        playback_item.setIconImage(thumbnail)
                        del art['icon']
                    playback_item.setArt(art)
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
