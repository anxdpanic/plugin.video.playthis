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

import kodi
import log_utils
from constants import RESOLVER_DIR

RUNPLUGIN_EXCEPTIONS = ['plugin.video.twitch']


def play_this(item, title='', thumbnail='', player=True):
    import urlresolver

    urlresolver.add_plugin_dirs(RESOLVER_DIR)

    log_utils.log('Attempting to resolve: |{0!s}|'.format(item), log_utils.LOGDEBUG)
    source = urlresolver.HostedMediaFile(url=item, title=title, include_disabled=False)
    stream_url = source.resolve()

    if not stream_url or not isinstance(stream_url, basestring):
        log_utils.log('Unable to resolve: |{0!s}|'.format(item), log_utils.LOGDEBUG)
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
