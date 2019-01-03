"""

    Copyright (C) 2015 tknorris

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

import time

from xbmc import LOGDEBUG
from xbmc import LOGERROR
from xbmc import LOGFATAL
from xbmc import LOGINFO
from xbmc import LOGNONE
from xbmc import LOGNOTICE
from xbmc import LOGSEVERE
from xbmc import LOGWARNING

from . import kodi


__all__ = ['log', 'trace', 'LOGDEBUG', 'LOGERROR', 'LOGFATAL', 'LOGINFO', 'LOGNONE', 'LOGNOTICE', 'LOGSEVERE', 'LOGWARNING']


name = kodi.get_name()


def log(msg, level=LOGDEBUG):
    try:
        if isinstance(msg, unicode):
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
