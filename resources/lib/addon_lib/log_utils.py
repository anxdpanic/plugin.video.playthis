# -*- coding: utf-8 -*-
"""

    Copyright (C) 2015-2016 tknorris
    Copyright (C) 2016-2019 anxdpanic

    This file is part of PlayThis (plugin.video.playthis)

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

import time

from xbmc import LOGDEBUG
from xbmc import LOGERROR
from xbmc import LOGFATAL
from xbmc import LOGINFO
from xbmc import LOGNONE
from xbmc import LOGWARNING

LOGNOTICE = LOGINFO

from . import kodi


__all__ = ['log', 'trace', 'LOGDEBUG', 'LOGERROR', 'LOGFATAL', 'LOGINFO', 'LOGNONE', 'LOGNOTICE', 'LOGWARNING']


name = kodi.get_name()


def log(msg, level=LOGDEBUG):
    try:
        if kodi.is_unicode(msg):
            msg = '%s (ENCODED)' % msg.encode('utf-8')

        kodi.__log('%s: %s' % (name, msg), level)
    except Exception as e:
        try:
            kodi.__log('Logging Failure: %s' % (e), level)
        except:
            pass


def trace(method):
    #  @trace decorator
    def method_trace_on(*args, **kwargs):
        start = time.time()
        result = method(*args, **kwargs)
        end = time.time()
        log('{name!r} time: {time:2.4f}s args: |{args!r}| kwargs: |{kwargs!r}|'
            .format(name=method.__name__,time=end - start, args=args, kwargs=kwargs), LOGDEBUG)
        return result

    def method_trace_off(*args, **kwargs):
        return method(*args, **kwargs)

    if __is_debugging():
        return method_trace_on
    else:
        return method_trace_off


def __is_debugging():
    command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Settings.getSettings',
               'params': {'filter': {'section': 'system', 'category': 'logging'}}}
    js_data = kodi.execute_jsonrpc(command)
    if 'result' in js_data and 'settings' in js_data['result']:
        for item in js_data['result']['settings']:
            if item['id'] == 'debug.showloginfo':
                return item['value']

    return False
