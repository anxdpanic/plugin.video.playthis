# -*- coding: utf-8 -*-
"""

    Copyright (C) 2011-2016 t0mm0 (common XBMC Module)
    Copyright (C) 2016-2019 anxdpanic

    This file is part of PlayThis (plugin.video.playthis)

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

import random
import gzip
import re
import socket
import time

from six import StringIO
from six import string_types
from six.moves import http_cookiejar as cookielib
from six.moves.urllib_parse import urlencode
from six.moves import urllib_request
from six.moves import xrange

from . import kodi


# Set Global timeout - Useful for slow connections and Putlocker.
socket.setdefaulttimeout(10)

BR_VERS = [
    ['%s.0' % i for i in xrange(18, 50)],
    ['37.0.2062.103', '37.0.2062.120', '37.0.2062.124', '38.0.2125.101', '38.0.2125.104', '38.0.2125.111', '39.0.2171.71', '39.0.2171.95', '39.0.2171.99', '40.0.2214.93', '40.0.2214.111',
     '40.0.2214.115', '42.0.2311.90', '42.0.2311.135', '42.0.2311.152', '43.0.2357.81', '43.0.2357.124', '44.0.2403.155', '44.0.2403.157', '45.0.2454.101', '45.0.2454.85', '46.0.2490.71',
     '46.0.2490.80', '46.0.2490.86', '47.0.2526.73', '47.0.2526.80', '48.0.2564.116', '49.0.2623.112', '50.0.2661.86'],
    ['11.0'],
    ['8.0', '9.0', '10.0', '10.6']]
WIN_VERS = ['Windows NT 10.0', 'Windows NT 7.0', 'Windows NT 6.3', 'Windows NT 6.2', 'Windows NT 6.1', 'Windows NT 6.0', 'Windows NT 5.1', 'Windows NT 5.0']
FEATURES = ['; WOW64', '; Win64; IA64', '; Win64; x64', '']
RAND_UAS = ['Mozilla/5.0 ({win_ver}{feature}; rv:{br_ver}) Gecko/20100101 Firefox/{br_ver}',
            'Mozilla/5.0 ({win_ver}{feature}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{br_ver} Safari/537.36',
            'Mozilla/5.0 ({win_ver}{feature}; Trident/7.0; rv:{br_ver}) like Gecko',
            'Mozilla/5.0 (compatible; MSIE {br_ver}; {win_ver}{feature}; Trident/6.0)']


def get_ua():
    try:
        last_gen = int(kodi.get_setting('last_ua_create'))
    except:
        last_gen = 0
    if not kodi.get_setting('current_ua') or last_gen < (time.time() - (7 * 24 * 60 * 60)):
        index = random.randrange(len(RAND_UAS))
        versions = {'win_ver': random.choice(WIN_VERS), 'feature': random.choice(FEATURES), 'br_ver': random.choice(BR_VERS[index])}
        user_agent = RAND_UAS[index].format(**versions)

        kodi.set_setting('current_ua', user_agent)
        kodi.set_setting('last_ua_create', str(int(time.time())))
    else:
        user_agent = kodi.get_setting('current_ua')
    return user_agent


class Net:
    '''
    This class wraps :mod:`urllib2` and provides an easy way to make http
    requests while taking care of cookies, proxies, gzip compression and
    character encoding.

    Example::

        from addon.common.net import Net
        net = Net()
        response = net.http_GET('http://xbmc.org')
        print response.content
    '''

    _cj = cookielib.LWPCookieJar()
    _proxy = None
    _user_agent = 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'
    _http_debug = False

    def __init__(self, cookie_file='', proxy='', user_agent='', http_debug=False):
        '''
        Kwargs:
            cookie_file (str): Full path to a file to be used to load and save
            cookies to.

            proxy (str): Proxy setting (eg.
            ``'http://user:pass@example.com:1234'``)

            user_agent (str): String to use as the User Agent header. If not
            supplied the class will use a default user agent (chrome)

            http_debug (bool): Set ``True`` to have HTTP header info written to
            the XBMC log for all requests.
        '''
        if cookie_file:
            self.set_cookies(cookie_file)
        if proxy:
            self.set_proxy(proxy)
        if user_agent:
            self.set_user_agent(user_agent)
        self._http_debug = http_debug
        self._update_opener()

    def set_cookies(self, cookie_file):
        '''
        Set the cookie file and try to load cookies from it if it exists.

        Args:
            cookie_file (str): Full path to a file to be used to load and save
            cookies to.
        '''
        try:
            self._cj.load(cookie_file, ignore_discard=True)
            self._update_opener()
            return True
        except:
            return False

    def get_cookies(self, as_dict=False):
        '''Returns A dictionary containing all cookie information by domain.'''
        if as_dict:
            return dict((cookie.name, cookie.value) for cookie in self._cj)
        else:
            return self._cj._cookies

    def save_cookies(self, cookie_file):
        '''
        Saves cookies to a file.

        Args:
            cookie_file (str): Full path to a file to save cookies to.
        '''
        self._cj.save(cookie_file, ignore_discard=True)

    def set_proxy(self, proxy):
        '''
        Args:
            proxy (str): Proxy setting (eg.
            ``'http://user:pass@example.com:1234'``)
        '''
        self._proxy = proxy
        self._update_opener()

    def get_proxy(self):
        '''Returns string containing proxy details.'''
        return self._proxy

    def set_user_agent(self, user_agent):
        '''
        Args:
            user_agent (str): String to use as the User Agent header.
        '''
        self._user_agent = user_agent

    def get_user_agent(self):
        '''Returns user agent string.'''
        return self._user_agent

    def _update_opener(self):
        '''
        Builds and installs a new opener to be used by all future calls to
        :func:`urllib2.urlopen`.
        '''
        if self._http_debug:
            http = urllib_request.HTTPHandler(debuglevel=1)
        else:
            http = urllib_request.HTTPHandler()

        if self._proxy:
            opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor(self._cj),
                                                 urllib_request.ProxyHandler({'http': self._proxy}),
                                                 urllib_request.HTTPBasicAuthHandler(), http)
        else:
            opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor(self._cj),
                                                 urllib_request.HTTPBasicAuthHandler(), http)
            urllib_request.install_opener(opener)

    def http_GET(self, url, headers={}, compression=True):
        '''
        Perform an HTTP GET request.

        Args:
            url (str): The URL to GET.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

            compression (bool): If ``True`` (default), try to use gzip
            compression.

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page and the page content.
        '''
        return self._fetch(url, headers=headers, compression=compression)

    def http_POST(self, url, form_data, headers={}, compression=True):
        '''
        Perform an HTTP POST request.

        Args:
            url (str): The URL to POST.

            form_data (dict): A dictionary of form data to POST.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

            compression (bool): If ``True`` (default), try to use gzip
            compression.

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page and the page content.
        '''
        return self._fetch(url, form_data, headers=headers, compression=compression)

    def http_HEAD(self, url, headers={}):
        '''
        Perform an HTTP HEAD request.

        Args:
            url (str): The URL to GET.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page.
        '''
        request = urllib_request.Request(url)
        request.get_method = lambda: 'HEAD'
        request.add_header('User-Agent', self._user_agent)
        for key in headers:
            request.add_header(key, headers[key])
        response = urllib_request.urlopen(request)
        return HttpResponse(response)

    def _fetch(self, url, form_data={}, headers={}, compression=True):
        '''
        Perform an HTTP GET or POST request.

        Args:
            url (str): The URL to GET or POST.

            form_data (dict): A dictionary of form data to POST. If empty, the
            request will be a GET, if it contains form data it will be a POST.

        Kwargs:
            headers (dict): A dictionary describing any headers you would like
            to add to the request. (eg. ``{'X-Test': 'testing'}``)

            compression (bool): If ``True`` (default), try to use gzip
            compression.

        Returns:
            An :class:`HttpResponse` object containing headers and other
            meta-information about the page and the page content.
        '''
        req = urllib_request.Request(url)
        if form_data:
            if isinstance(form_data, string_types):
                form_data = form_data
            else:
                form_data = urlencode(form_data, True)
            req = urllib_request.Request(url, form_data)
        req.add_header('User-Agent', self._user_agent)
        for key in headers:
            req.add_header(key, headers[key])
        if compression:
            req.add_header('Accept-Encoding', 'gzip')
        req.add_unredirected_header('Host', req.get_host())
        response = urllib_request.urlopen(req)
        return HttpResponse(response)


class HttpResponse:
    '''
    This class represents a resoponse from an HTTP request.

    The content is examined and every attempt is made to properly encode it to
    Unicode.

    .. seealso::
        :meth:`Net.http_GET`, :meth:`Net.http_HEAD` and :meth:`Net.http_POST`
    '''

    content = ''
    '''Unicode encoded string containing the body of the reposne.'''

    def __init__(self, response):
        '''
        Args:
            response (:class:`mimetools.Message`): The object returned by a call
            to :func:`urllib2.urlopen`.
        '''
        self._response = response

    @property
    def content(self):
        html = self._response.read()
        encoding = None
        try:
            if self._response.headers['content-encoding'].lower() == 'gzip':
                html = gzip.GzipFile(fileobj=StringIO(html)).read()
        except:
            pass

        try:
            content_type = self._response.headers['content-type']
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[-1]
        except:
            pass

        r = re.search('<meta\s+http-equiv="Content-Type"\s+content="(?:.+?);\s+charset=(.+?)"', html, re.IGNORECASE)
        if r:
            encoding = r.group(1)

        if encoding is not None:
            try:
                html = html.decode(encoding)
            except:
                pass
        return html

    def get_headers(self, as_dict=False):
        '''Returns headers returned by the server.
        If as_dict is True, headers are returned as a dictionary otherwise a list'''
        if as_dict:
            return dict([(item[0].title(), item[1]) for item in self._response.info().items()])
        else:
            return self._response.info().headers

    def get_url(self):
        '''
        Return the URL of the resource retrieved, commonly used to determine if
        a redirect was followed.
        '''
        return self._response.geturl()
