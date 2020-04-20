# -*- coding: utf-8 -*-
"""

    Copyright (C) 2016-2019 anxdpanic

    This file is part of PlayThis (plugin.video.playthis)

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

import re
import sys
import struct
import socket

from six import string_types
from six.moves.html_parser import HTMLParser
from six.moves.urllib_parse import parse_qsl
from six.moves.urllib_parse import urlparse
from six.moves.urllib_parse import quote
from six.moves.urllib_parse import unquote
from six.moves.urllib_parse import quote_plus
from six.moves.urllib_parse import unquote_plus

from . import kodi
from . import utils
from . import log_utils
from . import cache
from .net import Net
from .remote import HttpJSONRPC
from .urlresolver_helpers import pick_source
from .urlresolver_helpers import parse_smil_source_list
from .urlresolver_helpers import get_hidden
from .urlresolver_helpers import append_headers
from .urlresolver_helpers import get_packed_data
from .constants import COOKIE_FILE
from .constants import ICONS
from .constants import MODES
from .constants import RAND_UA
from .constants import FF_USER_AGENT

has_youtube = None

try:
    import youtube_resolver

    has_youtube = 'YouTube'
except ImportError:
    pass

socket.setdefaulttimeout(30)

RUNPLUGIN_EXCEPTIONS = []

dash_supported = kodi.has_addon('inputstream.adaptive')
inputstream_rtmp = kodi.has_addon('inputstream.rtmp')
has_youtube_addon = kodi.has_addon('plugin.video.youtube')

adaptive_version = None
if dash_supported:
    try:
        adaptive_version = kodi.Addon('inputstream.adaptive').getAddonInfo('version')
        hls_supported = False if adaptive_version is None else (kodi.loose_version(adaptive_version) >= kodi.loose_version('2.0.10'))  # Kodi 17.4
    except RuntimeError:
        dash_supported = False
        hls_supported = False

user_cache_limit = int(kodi.get_setting('cache-expire-time'))
resolver_cache_limit = 0.11  # keep resolver caching to 10 > minutes > 5, resolved sources expire
cache.cache_enabled = user_cache_limit > 0


def get_url_with_headers(url, headers):
    if 'Accept-Encoding' in headers:
        del headers['Accept-Encoding']
    if 'Host' in headers:
        del headers['Host']
    parts = url.split('|')
    url = parts[0]
    url_headers = {}
    if len(parts) > 1:
        for i in re.finditer(r'(?:&|^)([^=]+)=(.+?)(?:&|$)', parts[-1]):
            if (i.group(1) == 'Cookie') and ('Cookie' in headers):
                headers['Cookie'] += unquote_plus(i.group(2))
            else:
                url_headers.update({i.group(1): unquote_plus(i.group(2))})
    url_headers.update(headers)
    cookie_string = ''
    if 'Cookie' in url_headers:
        cookie_string = ''.join(c.group(1) for c in re.finditer(r'(?:^|\s)(.+?=.+?;)', url_headers['Cookie']))
        del url_headers['Cookie']
    net = Net()
    cookie_jar_result = net.set_cookies(COOKIE_FILE)
    for c in net._cj:
        if c.domain and (c.domain.lstrip('.') in url):
            if c.value not in cookie_string:
                cookie_string += '%s=%s;' % (c.name, c.value)
    if cookie_string:
        sep = '&' if url_headers else ''
        return url + append_headers(url_headers) + sep + 'Cookie=' + quote_plus(cookie_string)
    if url_headers:
        return url + append_headers(url_headers)
    else:
        return url


def get_default_headers(url):
    parsed_url = urlparse(url)
    try:
        user_agent = RAND_UA
    except:
        user_agent = FF_USER_AGENT
    return {'User-Agent': user_agent,
            'Host': parsed_url.hostname,
            'Accept-Language': 'en',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'Keep-Alive',
            'Referer': '%s://%s' % (parsed_url.scheme, parsed_url.hostname)}


def __get_html_and_headers(url, headers=None):
    if headers is None:
        headers = get_default_headers(url)
    try:
        net = Net()
        cookie_jar_result = net.set_cookies(COOKIE_FILE)
        response = net.http_GET(url, headers=headers)
        cookie_jar_result = net.save_cookies(COOKIE_FILE)
        contents = response.content
        redirect = response.get_url()
        if ('reddit' in redirect) and ('over18' in redirect):
            post_headers = {}
            post_headers.update(
                {'User-Agent': FF_USER_AGENT, 'Content-Type': 'application/x-www-form-urlencoded'})
            data = get_hidden(contents)
            data.update({'over18': 'yes'})
            cookie_jar_result = net.set_cookies(COOKIE_FILE)
            response = net.http_POST(response.get_url(), form_data=data, headers=post_headers)
            cookie_jar_result = net.save_cookies(COOKIE_FILE)
            contents = response.content
        log_utils.log('GET request updated headers: |{0!s}|'.format(headers), log_utils.LOGDEBUG)
        return {'contents': contents, 'headers': headers}
    except:
        return {'contents': '', 'headers': headers}


def __get_qt_atom_url(url, headers):
    log_utils.log('Attempting to get url from quicktime atom: |{0!s}|'.format(url), log_utils.LOGDEBUG)
    try:
        result = __get_html_and_headers(url, headers)
        r = re.search(r'moov.*?rmra.*?rdrf.*?url (....)(.*)', result['contents'])
        l = struct.unpack("!I", r.group(1))[0]
        return {'url': r.group(2)[:l], 'headers': result['headers']}
    except:
        return {'url': None, 'headers': headers}


def __get_potential_type(url):
    supported_music = [ext for ext in kodi.get_supported_media('music').split('|') if ext != '']
    supported_picture = [ext for ext in kodi.get_supported_media('picture').split('|') if ext != '']
    supported_video = [ext for ext in kodi.get_supported_media('video').split('|') if ext != '']

    potential_type = 'text'
    if '.mpd' in url:
        potential_type = 'mpd'
    elif any(ext in url for ext in supported_music):
        potential_type = 'audio'
    elif any(ext in url for ext in supported_picture):
        potential_type = 'image'
    elif any(ext in url for ext in supported_video):
        potential_type = 'video'

    return potential_type


@cache.cache_function(cache_limit=23)
def __get_gen_extractors():
    from youtube_dl import extractor as __extractor
    return __extractor.gen_extractors()


@cache.cache_function(cache_limit=23)
def __get_gen_extractors_names():
    names = set()
    extractors = __get_gen_extractors()
    for extractor in extractors:
        if extractor.IE_NAME == 'generic': continue
        name = extractor.IE_NAME.lower().split(':')[0]
        if kodi.is_unicode(name):
            name = name.encode('utf-8')
        names.add(name)
    return list(names)


def ytdl_supported(url):
    names = __get_gen_extractors_names()
    name = None
    hostname = urlparse(url).hostname
    if any(((name in hostname) or (hostname in name)) for name in names):
        name = next(name for name in names if ((name in hostname) or (hostname in name)))
    if name:
        extractors = __get_gen_extractors()
        for extractor in extractors:
            if (extractor.IE_NAME != 'generic') and (name.lower() in extractor.IE_NAME.split(':')[0].lower()) and (extractor.suitable(url)):
                return True
    return False


def yt_addon_supported(url):
    return has_youtube_addon and re.match(r'(?:http)*s*:*[/]{0,2}(?:www\.)*youtu(?:\.be/|be\.com/(?:embed/|watch/|v/|.*?[?&/]v=))[a-zA-Z0-9_\-]{11}.*', url)


def __get_content_type_and_headers(url, headers=None):
    url_override = None
    if headers is None:
        headers = get_default_headers(url)

    potential_type = __get_potential_type(url)

    try:
        net = Net()
        cookie_jar_result = net.set_cookies(COOKIE_FILE)
        response = net.http_HEAD(url, headers=headers)
        cookie_jar_result = net.save_cookies(COOKIE_FILE)
        response_headers = response.get_headers(as_dict=True)
        try:
            redirect = response.get_url()
            if redirect != url:
                log_utils.log('Head request following redirect to: |{0!s}|'.format(url_override), log_utils.LOGDEBUG)
                url_override = redirect
                cookie_jar_result = net.set_cookies(COOKIE_FILE)
                response = net.http_HEAD(url_override, headers=headers)
                cookie_jar_result = net.save_cookies(COOKIE_FILE)
                response_headers = response.get_headers(as_dict=True)
        except:
            pass
    except:
        log_utils.log('HEAD request failed: |{1!s}| media type: |{0!s}|'
                      .format(potential_type, headers), log_utils.LOGDEBUG)
        return {'content_type': potential_type, 'headers': headers, 'url_override': None}

    clength_header = response_headers.get('Content-Length', '')
    ctype_header = response_headers.get('Content-Type', potential_type)

    try:
        media, subtype = re.findall('([a-z\-]+)/([a-z0-9\-+.]+);?', ctype_header, re.DOTALL)[0]
        log_utils.log('HEAD request returned MIME type: |{0!s}/{1!s}| and headers: |{2!s}|'
                      .format(media, subtype, response_headers), log_utils.LOGDEBUG)
        content_type = media
        if (content_type == 'application') and ((subtype == 'dash+xml') or ((subtype == 'xml') and url.endswith('.mpd'))):
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
                    qt_result = __get_qt_atom_url(url, headers)
                    headers = qt_result['headers']
                    url_override = qt_result['url']
            except:
                pass
    except:
        content_type = ctype_header

    log_utils.log('HEAD request complete updated headers: |{1!s}| using media type: |{0!s}|'
                  .format(content_type, headers), log_utils.LOGDEBUG)
    return {'content_type': content_type, 'headers': headers, 'url_override': url_override}


def __check_for_new_url(url):
    if 'google' in url:
        try:
            return unquote(re.findall(r'cache:[a-zA-Z0-9_\-]+:(.+?)\+&amp;', url)[-1])
        except:
            try:
                return unquote(re.findall(r'google[a-z]*\.[a-z]+/.*url=(.+?)[&$]', url)[-1])
            except:
                pass
    if 'reddit' in url:
        try:
            return unquote(re.findall(r'http[s]?://out\.reddit\.com/.*?url=(.+?)&amp;', url)[-1])
        except:
            pass
    if 'youtu.be' in url:
        result = re.search(r'http[s]*://youtu\.be/(?P<video_id>[a-zA-Z0-9_\-]{11})', url)
        if result:
            return 'https://www.youtube.com/watch?v=%s' % result.group('video_id')

    return url


def scrape_supported(url, html, regex):
    parsed_url = urlparse(url)
    links = []
    _filter = ['.js', 'data:', 'blob:', 'tab=', 'usp=', '/pixel.', '/1x1.', 'javascript:', 'rss.', 'blank.', '.rss', '.css']
    sources = []
    with kodi.ProgressDialog('%s...' % kodi.i18n('scraping_for_potential_urls'), '%s: %s' % (kodi.i18n('source'), url), ' ', timer=0.2) as progress_dialog:
        while not progress_dialog.is_canceled():
            new_iter = re.findall(regex, html, re.DOTALL)
            len_iter = len(new_iter)
            for index, match in enumerate(new_iter):
                if progress_dialog.is_canceled():
                    sys.exit(0)
                percent = int((float(index) / float(len_iter)) * 100)
                stream_url = match[0]
                if stream_url == '#' or stream_url == '//' or '/' not in stream_url or not re.match(r'^[hruf:/].+', stream_url) or \
                        any(item in stream_url for item in _filter) or any(stream_url == t[1] for t in links):
                    progress_dialog.update(percent, kodi.i18n('preparing_results'), '%s: %s' % (kodi.i18n('discarded'), '%s' % stream_url), ' ')
                    continue
                stream_url = __check_for_new_url(stream_url).replace(r'\\', '')
                if stream_url.startswith('//'):
                    stream_url = '%s:%s' % (parsed_url.scheme, stream_url)
                elif stream_url.startswith('/'):
                    stream_url = '%s://%s%s' % (parsed_url.scheme, parsed_url.hostname, stream_url)

                host = urlparse(stream_url).hostname
                if host is None:
                    continue
                label = host
                if (len(match) > 2) and (match[2] is not None) and (match[2].strip()) and (host not in match[2]):
                    label = match[2].strip()
                elif (len(match) > 1) and (match[1] is not None) and (match[1].strip()) and (host not in match[1]):
                    label = match[1].strip()
                if not kodi.is_unicode(label):
                    label = kodi.decode_utf8(label, ignore=True)
                try:
                    parser = HTMLParser()
                    label = parser.unescape(label)
                    try:
                        label = parser.unescape(label)
                    except:
                        pass
                except:
                    pass
                progress_dialog.update(percent, kodi.i18n('preparing_results'), '%s: %s' % (kodi.i18n('added'), label), stream_url)
                sources.append((label, stream_url))
            if progress_dialog.is_canceled():
                sys.exit(0)
            break
        if progress_dialog.is_canceled():
            sys.exit(0)

    with kodi.ProgressDialog('%s...' % kodi.i18n('scraping_for_potential_urls'), '%s: %s' % (kodi.i18n('source'), url), ' ', timer=0.1) as progress_dialog:
        while not progress_dialog.is_canceled():
            len_iter = len(sources)
            for index, source in enumerate(sources):
                if progress_dialog.is_canceled():
                    sys.exit(0)
                percent = int((float(index) / float(len_iter)) * 100)
                label = source[0]
                stream_url = source[1]

                if yt_addon_supported(stream_url):
                    resolver_name = has_youtube
                    progress_dialog.update(percent, kodi.i18n('check_for_support'),
                                           '%s [%s]: %s' % (kodi.i18n('support_potential'), 'video', resolver_name),
                                           '[%s]: %s' % (label, stream_url))
                    links.append({'label': label, 'url': stream_url, 'resolver': resolver_name, 'content_type': 'video'})
                    continue

                potential_type = __get_potential_type(stream_url)

                if potential_type == 'text':
                    if ytdl_supported(stream_url):
                        progress_dialog.update(percent, kodi.i18n('check_for_support'),
                                               '%s [%s]: %s' % (kodi.i18n('support_potential'), 'video', 'youtube-dl'),
                                               '[%s]: %s' % (label, stream_url))
                        links.append({'label': label, 'url': stream_url, 'resolver': 'youtube-dl', 'content_type': 'video'})
                        continue
                    progress_dialog.update(percent, kodi.i18n('check_for_support'),
                                           '%s [%s]: %s' % (kodi.i18n('support_potential'), potential_type, 'None'),
                                           '[%s]: %s' % (label, stream_url))
                else:
                    progress_dialog.update(percent, kodi.i18n('check_for_support'),
                                           '%s [%s]: %s' % (kodi.i18n('support_potential'), potential_type, 'Kodi'),
                                           '[%s]: %s' % (label, stream_url))
                links.append({'label': label, 'url': stream_url, 'resolver': None, 'content_type': potential_type})
                continue

            if progress_dialog.is_canceled():
                sys.exit(0)
            break
        if progress_dialog.is_canceled():
            sys.exit(0)
    return links


@cache.cache_function(cache_limit=resolver_cache_limit)
def resolve_yt_addon(url):
    label = None
    stream_url = None
    headers = None
    thumbnail = None
    content_type = 'video'

    sources = youtube_resolver.resolve(url, sort=True)
    if isinstance(sources, list):
        src = sources[0]
        if src.get('container') == 'mpd' and not dash_supported:
            src = sources[1]

        stream_url = src.get('url')

        hdr = src.get('headers')
        if hdr:
            headers = parse_qsl(hdr)

        lbl = src.get('meta', {}).get('video', {}).get('title')
        if lbl:
            label = lbl

        thmb = src.get('meta', {}).get('images', {}).get('high', src.get('meta', {}).get('images', {}).get('medium'))
        if thmb:
            thumbnail = thmb

    return {'label': label, 'resolved_url': stream_url, 'content_type': content_type, 'thumbnail': thumbnail, 'headers': headers}


@cache.cache_function(cache_limit=resolver_cache_limit)
def resolve_youtube_dl(url):
    label = None
    stream_url = None
    headers = None
    thumbnail = None
    content_type = 'video'
    try:
        from YDStreamExtractor import _getYoutubeDLVideo
        source = _getYoutubeDLVideo(url, resolve_redirects=True)
    except:
        source = None
    if source:
        selected_stream = source.selectedStream()
        stream_url = selected_stream['xbmc_url']
        title = source.title
        thumbnail = source.thumbnail
        label = None if title.lower().startswith('http') else title
        try:
            label = HTMLParser().unescape(label)
        except:
            pass
        if 'ytdl_format' in selected_stream and 'formats' in selected_stream['ytdl_format']:
            formats = selected_stream['ytdl_format']['formats']
            format_index = None
            if selected_stream['ytdl_format'].get('extractor_key') == 'Facebook':  # ytdl xbmc_url is audio only for Facebook, override url
                q_ids = ['dash_hd_src_no_ratelimit', 'dash_hd_src', 'dash_sd_src_no_ratelimit', 'dash_sd_src']
                while len(q_ids) > 0:
                    format_id = q_ids[0]
                    try:
                        format_index = next(index for (index, f) in enumerate(formats) if f['format_id'] == format_id)
                        stream_url = formats[format_index]['url']
                        break
                    except StopIteration:
                        del q_ids[0]
            else:
                format_id = selected_stream['formatID']
                format_index = next(index for (index, f) in enumerate(formats) if f['format_id'] == format_id)
            if format_index:
                ext = formats[format_index]['ext']
                headers = formats[format_index]['http_headers']
                if ext:
                    content_type = __get_potential_type('.' + ext)
    return {'label': label, 'resolved_url': stream_url, 'content_type': content_type, 'thumbnail': thumbnail, 'headers': headers}


def __pick_source(sources):
    log_utils.log('Sources found: {0}'.format(sources))
    if len(sources) == 1:
        return sources[0]
    elif len(sources) > 1:
        if kodi.get_kodi_version().major > 16:
            listitem_sources = []
            for source in sources:
                title = source['label'] if source['label'] else kodi.i18n('unknown')
                label2 = '%s [[COLOR=lightgray]%s[/COLOR]]' % (source['content_type'].capitalize(), source['resolver'] if source['resolver'] else 'Kodi')
                icon = ''
                if source['content_type'] == 'image':
                    icon = source['url']
                elif not source['resolver']:
                    icon = ICONS.KODI
                elif source['resolver'] == 'YouTube':
                    icon = ICONS.YOUTUBE
                elif source['resolver'] == 'youtube-dl':
                    icon = ICONS.YOUTUBEDL

                l_item = kodi.ListItem(label=title, label2=label2)
                l_item.setArt({'icon': icon, 'thumb': icon})
                listitem_sources.append(l_item)
            result = kodi.Dialog().select(kodi.i18n('choose_source'), list=listitem_sources, useDetails=True)
        else:
            result = kodi.Dialog().select(kodi.i18n('choose_source'),
                                          ['[%s] %s' % (source['content_type'].capitalize(), source['label'])
                                           if source['label']
                                           else '[%s] %s' % (source['content_type'].capitalize(), kodi.i18n('unknown'))
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
    result = __get_html_and_headers(url)
    html = result['contents'] + get_packed_data(result['contents'])

    def _to_list(items):
        for lstitem in items:
            if not any(lstitem['url'] == t['url'] for t in unresolved_source_list):
                unresolved_source_list.append(lstitem)
            else:
                if lstitem['label'] not in lstitem['url']:
                    for idx, itm in enumerate(unresolved_source_list):
                        if (lstitem['url'] == itm['url']) and (itm['label'] in itm['url']):
                            unresolved_source_list[idx] = lstitem
                            break

    log_utils.log('Scraping for iframes', log_utils.LOGDEBUG)
    _to_list(scrape_supported(url, html, r'''iframe src\s*=\s*['"]([^'"]+)(?:[^>]+(?:title|alt)\s*=\s*['"]([^'"]+))?'''))
    log_utils.log('Scraping for hrefs', log_utils.LOGDEBUG)
    _to_list(scrape_supported(url, html, r'''href\s*=\s*['"]([^'"]+)[^>]+(?:(?:(?:data-title|title)\s*=\s*['"]([^'"]+))?(?:[^>]*>([^<]+))?)'''))
    log_utils.log('Scraping for data-hrefs', log_utils.LOGDEBUG)
    _to_list(scrape_supported(url, html, r'''data-href-url\s*=\s*['"]([^'"]+)[^>]+(?:(?:(?:data-title|title)\s*=\s*['"]([^'"]+))?(?:[^>]*>([^<]+))?)'''))
    log_utils.log('Scraping for data-lazy-srcs', log_utils.LOGDEBUG)
    _to_list(scrape_supported(url, html, r'''data-lazy-src\s*=\s*['"]([^'"]+)(?:[^>]+(?:title|alt)\s*=\s*['"]([^'"]+))?'''))
    log_utils.log('Scraping for srcs', log_utils.LOGDEBUG)
    _to_list(scrape_supported(url, html, r'''src(?<!iframe\s)\s*=\s*['"]([^'"]+)(?:[^>]+(?:title|alt)\s*=\s*['"]([^'"]+))?'''))

    title = ''
    match = re.search(r'title>\s*(.+?)\s*</title', html)
    if match:
        title = match.group(1)
        try:
            title = HTMLParser().unescape(title)
        except:
            pass
    result_list = []
    for item in unresolved_source_list:
        if item['content_type'] != 'text':
            result_list.append(item)
    return {'results': result_list, 'title': title, 'headers': result['headers']}


def scrape(url):
    result = _scrape(url)
    result_list = result['results']
    if result_list:
        chosen = __pick_source(result_list)
        if chosen:
            if chosen['resolver']:
                label = None
                content_type = None
                headers = None
                thumbnail = None
                resolved = None
                if chosen['resolver'] == 'YouTube':
                    yt_result = resolve_yt_addon(chosen['url'])
                    label = yt_result['label']
                    resolved = yt_result['resolved_url']
                    content_type = yt_result['content_type']
                    headers = yt_result['headers']
                    thumbnail = yt_result['thumbnail']
                if chosen['resolver'] == 'youtube-dl' or not resolved:
                    ytdl_result = resolve_youtube_dl(chosen['url'])
                    label = ytdl_result['label']
                    resolved = ytdl_result['resolved_url']
                    content_type = ytdl_result['content_type']
                    headers = ytdl_result['headers']
                    thumbnail = ytdl_result['thumbnail']
                headers = result['headers'] if headers is None else headers
                label = chosen['label'] if label is None else label
                content_type = chosen['content_type'] if content_type is None else content_type
                return {'label': label, 'resolved_url': resolved, 'content_type': content_type, 'unresolved_url': chosen['url'], 'thumbnail': thumbnail, 'title': result['title'],
                        'headers': headers}
            elif chosen['content_type'] == 'text':
                ytdl_result = resolve_youtube_dl(chosen['url'])
                if ytdl_result['resolved_url']:
                    label = chosen['label'] if ytdl_result['label'] is None else ytdl_result['label']
                    headers = result['headers'] if ytdl_result['headers'] is None else ytdl_result['headers']
                    return {'label': label, 'resolved_url': ytdl_result['resolved_url'], 'content_type': ytdl_result['content_type'], 'unresolved_url': chosen['url'],
                            'thumbnail': ytdl_result['thumbnail'], 'title': result['title'], 'headers': headers}

            thumbnail = chosen['url'] if chosen['content_type'] == 'image' else None
            return {'label': chosen['label'], 'resolved_url': chosen['url'], 'content_type': chosen['content_type'], 'unresolved_url': chosen['url'], 'thumbnail': thumbnail,
                    'title': result['title'], 'headers': result['headers']}

    return {'label': None, 'resolved_url': None, 'content_type': None, 'unresolved_url': None, 'thumbnail': None, 'title': None, 'headers': None}


def __check_smil_dash(source, headers):
    is_dash = False
    if '.smil' in source:
        smil_result = __get_html_and_headers(source, headers)
        source = pick_source(parse_smil_source_list(smil_result['contents']))
    elif '.mpd' in source and not dash_supported:
        is_dash = False
        source = None
    elif '.mpd' in source and dash_supported:
        is_dash = True
    return {'url': source, 'is_dash': is_dash}


def remote_play(source):
    rpc_client = HttpJSONRPC()
    command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Player.GetActivePlayers'}
    response = rpc_client.execute_rpc(command)
    if 'error' in response:
        kodi.notify(kodi.get_name(), response['error'], duration=7000)
        return
    try:
        player_id = response['result'][0]['playerid']
    except IndexError:
        player_id = None
    if player_id == 2:  # stop picture player if active, it will block
        command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Player.Stop', 'params': {'playerid': player_id}}
        response = rpc_client.execute_rpc(command)
        if 'error' in response:
            kodi.notify(kodi.get_name(), response['error'], duration=7000)
            return
    if source['is_dash']:
        filename = kodi.get_plugin_url({'mode': MODES.PLAY, 'player': 'false', 'path': quote(source['url']),
                                        'thumb': quote(source['art']['thumb']), 'title': quote(source['info']['title'])})
    else:
        filename = source['url']
    command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Player.Open', 'params': {'item': {'file': filename}}}
    response = rpc_client.execute_rpc(command)
    if 'error' in response:
        kodi.notify(kodi.get_name(), response['error'], duration=7000)
    else:
        if 'No Response' not in response['result']:
            kodi.notify(kodi.get_name(), kodi.i18n('send_success'))


def play(source, player=True):
    if player == 'remote':
        remote_play(source)
    else:
        if source['content_type'] == 'image':
            command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Player.Open', 'params': {'item': {'file': source['url']}}}
            log_utils.log('Play using jsonrpc method Player.Open: |{0!s}|'.format(source['url']), log_utils.LOGDEBUG)
            response = kodi.execute_jsonrpc(command)
        else:
            playback_item = kodi.ListItem(label=source['info']['title'], path=source['url'])
            playback_item.setProperty('IsPlayable', 'true')
            playback_item.setArt(source['art'])
            playback_item.addStreamInfo(source['content_type'], {})
            if source['is_dash']:
                playback_item.setContentLookup(False)
                playback_item.setMimeType('application/xml+dash')
                playback_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
                playback_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
            elif (source['url'].startswith('rtmp')) and (inputstream_rtmp):
                if kodi.addon_enabled('inputstream.rtmp'):
                    playback_item.setProperty('inputstreamaddon', 'inputstream.rtmp')
            elif ('.m3u8' in source['url']) and (hls_supported):
                playback_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
                playback_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
            playback_item.setInfo(source['content_type'], source['info'])
            if kodi.get_handle() == -1:
                log_utils.log('Play using Player(): |{0!s}|'.format(source['url']), log_utils.LOGDEBUG)
                kodi.Player().play(source['url'], playback_item)
            else:
                log_utils.log('Play using set_resolved_url: |{0!s}|'.format(source['url']), log_utils.LOGDEBUG)
                kodi.set_resolved_url(playback_item)


def play_this(item, title='', thumbnail='', player=True, history=None):
    if history is None:
        history = kodi.get_setting('history-add-on-play') == "true"
    override_history = kodi.get_setting('history-add-on-play') == "true"
    stream_url = None
    headers = None
    content_type = 'video'
    override_content_type = None
    is_dash = False
    direct = ['rtmp:', 'rtmpe:', 'ftp:', 'ftps:', 'special:', 'plugin:', 'udp:', 'upnp:', 'shout:']
    unresolved_source = None
    label = title
    source_label = label
    source_thumbnail = thumbnail
    history_item = None

    if item.startswith('blob:http'):
        item = item.lstrip('blob:')
    if item.find(' ') > -1:
        item = quote(item, safe="%/:=&?~#+!$,;'@()*[]")
    if item.startswith('http'):
        with kodi.ProgressDialog('%s...' % kodi.i18n('resolving'), '%s:' % kodi.i18n('attempting_determine_type'), item) as progress_dialog:
            while not progress_dialog.is_canceled():
                url_override = __check_for_new_url(item)
                if item != url_override:
                    log_utils.log('Source |{0}| has been replaced by |{1}|'.format(item, url_override), log_utils.LOGDEBUG)
                    progress_dialog.update(5, '%s: %s' % (kodi.i18n('source'), item), '%s: %s' % (kodi.i18n('replaced_with'), url_override), ' ')
                    item = url_override
                result = __get_content_type_and_headers(item)
                content_type = result['content_type']
                headers = result['headers']
                url_override = result['url_override']
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
                        smil_result = __get_html_and_headers(item, headers)
                        source = pick_source(parse_smil_source_list(smil_result['contents']))
                    elif content_type == 'mpd':
                        content_type = 'video'
                        if not dash_supported:
                            source = None
                        else:
                            is_dash = True
                    if source:
                        stream_url = source

                elif content_type == 'text':
                    if progress_dialog.is_canceled():
                        sys.exit(0)

                    content_type = 'video'
                    headers.update({'Referer': item})

                    resolver_name = 'YouTube'
                    progress_dialog.update(40, '%s: %s' % (kodi.i18n('source'), item), '%s: %s' % (kodi.i18n('attempt_resolve_with'), resolver_name), ' ')
                    if yt_addon_supported(item):
                        yt_result = resolve_yt_addon(item)
                        if yt_result['resolved_url']:
                            headers = yt_result['headers']
                            label = yt_result['label'] if yt_result['label'] is not None else label
                            source_label = label
                            thumbnail = yt_result['thumbnail'] if yt_result['thumbnail'] is not None else thumbnail
                            source_thumbnail = thumbnail
                            log_utils.log('Source |{0}| found by |{1}|'
                                          .format(yt_result['resolved_url'], resolver_name), log_utils.LOGDEBUG)
                            sd_result = __check_smil_dash(yt_result['resolved_url'], headers)
                            source = sd_result['url']
                            is_dash = sd_result['is_dash']
                            if source:
                                progress_dialog.update(98, '%s: %s' % (kodi.i18n('source'), item),
                                                       '%s: %s' % (kodi.i18n('attempt_resolve_with'), resolver_name),
                                                       '%s: %s' % (kodi.i18n('resolution_successful'), source))
                                stream_url = source

                    if not stream_url:
                        if progress_dialog.is_canceled():
                            sys.exit(0)

                        resolver_name = 'youtube-dl'
                        progress_dialog.update(80, '%s: %s' % (kodi.i18n('source'), item), '%s: %s' % (kodi.i18n('attempt_resolve_with'), resolver_name), ' ')
                        if ytdl_supported(item):
                            ytdl_result = resolve_youtube_dl(item)
                            if ytdl_result['resolved_url']:
                                headers = ytdl_result['headers']
                                label = ytdl_result['label'] if ytdl_result['label'] is not None else label
                                source_label = label
                                thumbnail = ytdl_result['thumbnail'] if ytdl_result['thumbnail'] is not None else thumbnail
                                source_thumbnail = thumbnail
                                log_utils.log('Source |{0}| found by |{1}|'
                                              .format(ytdl_result['resolved_url'], resolver_name), log_utils.LOGDEBUG)
                                sd_result = __check_smil_dash(ytdl_result['resolved_url'], headers)
                                source = sd_result['url']
                                is_dash = sd_result['is_dash']
                                if source:
                                    progress_dialog.update(98, '%s: %s' % (kodi.i18n('source'), item),
                                                           '%s: %s' % (kodi.i18n('attempt_resolve_with'), resolver_name),
                                                           '%s: %s' % (kodi.i18n('resolution_successful'), source))
                                    stream_url = source

                if not progress_dialog.is_canceled():
                    progress_dialog.update(100, ' ', kodi.i18n('resolution_completed'), ' ')
                    break
                else:
                    sys.exit(0)

        if not stream_url:
            content_type = 'executable'
            scrape_result = scrape(item)
            source = scrape_result['resolved_url']
            override_content_type = scrape_result['content_type']
            unresolved_source = scrape_result['unresolved_url']
            source_label = scrape_result['label']
            headers = scrape_result['headers']
            if scrape_result['thumbnail']:
                source_thumbnail = scrape_result['thumbnail']
            if scrape_result['title']:
                label = scrape_result['title']
            if source:
                log_utils.log('Source |{0}| found by |Scraping for supported|'
                              .format(source), log_utils.LOGDEBUG)
                if override_content_type == 'video' or override_content_type == 'mpd':
                    sd_result = __check_smil_dash(source, headers)
                    source = sd_result['url']
                    is_dash = sd_result['is_dash']
                if source:
                    stream_url = source

        if stream_url:
            stream_url = stream_url.replace(r'\\', '')

    elif any(item.startswith(p) for p in direct):
        log_utils.log('Source |{0}| may be supported'.format(item), log_utils.LOGDEBUG)
        stream_url = item

    if is_dash and (not dash_supported or not kodi.addon_enabled('inputstream.adaptive')):
        stream_url = None

    if stream_url and (content_type == 'video' or content_type == 'audio' or content_type == 'image' or content_type == 'executable'):
        working_dialog = kodi.WorkingDialog()
        with working_dialog:
            play_history = utils.PlayHistory()
            working_dialog.update(20)
            if history or player == 'history':
                history_item = item.split('|')[0]
                if '%' not in history_item:
                    history_item = quote(history_item)
                log_utils.log('Adding source |{0}| to history with content_type |{1}|'
                              .format(item, content_type), log_utils.LOGDEBUG)
                play_history.add(history_item, content_type, label if label else item, quote(thumbnail))
            working_dialog.update(40)
            if override_content_type and override_history:
                history_item = stream_url
                if history_item.startswith('plugin://') or unresolved_source:
                    history_item = unresolved_source
                history_item = history_item.split('|')[0]
                if '%' not in history_item:
                    history_item = quote(history_item)
                log_utils.log('Adding source |{0}| to history with content_type |{1}|'
                              .format(unresolved_source, override_content_type), log_utils.LOGDEBUG)
                play_history.add(history_item, override_content_type, source_label, quote(source_thumbnail))
            if player == 'history':
                return
            if history_item:
                kodi.refresh_container()
            working_dialog.update(60)
            if (not stream_url.startswith('plugin://')) and (headers is not None):
                stream_url = get_url_with_headers(stream_url, headers)

            working_dialog.update(80)
            if any(plugin_id in stream_url for plugin_id in RUNPLUGIN_EXCEPTIONS):
                log_utils.log('Running plugin: |{0!s}|'.format(stream_url), log_utils.LOGDEBUG)
                kodi.execute_builtin('RunPlugin(%s)' % stream_url)
            else:
                if override_content_type:
                    content_type = override_content_type

                source = {'content_type': content_type,
                          'url': stream_url,
                          'is_dash': is_dash,
                          'info': {'title': source_label},
                          'art': {'icon': source_thumbnail, 'thumb': source_thumbnail}}

                play(source, player)

    else:
        log_utils.log('Found no potential sources: |{0!s}|'.format(item), log_utils.LOGDEBUG)
