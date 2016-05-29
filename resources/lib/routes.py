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

import os
from utils import PlayHistory, M3UUtils
from addon_lib import kodi
from addon_lib.constants import DISPATCHER, MODES, ADDON_DATA_DIR
from addon_lib.playback import play_this
from urllib2 import unquote, quote

play_history = PlayHistory()


@DISPATCHER.register(MODES.MAIN)
def main_route():
    if play_history.use_directory():
        play_history.history_directory()
    else:
        playback_item = play_history.history_dialog()
        if playback_item:
            play_this(unquote(playback_item), player=True)


@DISPATCHER.register(MODES.NEW, kwargs=['player'])
def get_new_item(player=True):
    playback_item = play_history.get_input()
    if playback_item:
        play_this(unquote(playback_item), title=unquote(playback_item), player=player)


@DISPATCHER.register(MODES.ADD, ['path'])
def add_url(path):
    if '%' not in path:
        path = quote(path)
    play_history.add(path)


@DISPATCHER.register(MODES.DELETE, ['row_id'], ['refresh'])
def delete_url(row_id, refresh=True):
    result, rowcount = play_history.delete_row_id(row_id)
    if (result, rowcount) == (1, 1) and refresh:
        kodi.refresh_container()


@DISPATCHER.register(MODES.PLAY, ['path'], ['player', 'history'])
def play(path, player=True, history=True):
    if history:
        history = path
        if '%' not in history:
            history = quote(history)
        play_history.add(history)
    play_this(unquote(path), player=player)


@DISPATCHER.register(MODES.EXPORT_M3U, kwargs=['export_path', 'from_list'])
def export_m3u(export_path=None, from_list='history'):
    if export_path is None:
        export_path = kodi.get_setting('export_path')
        if not export_path:
            export_path = kodi.Dialog().browse(3, kodi.i18n('export_path'), 'video', '', False, False, ADDON_DATA_DIR)
            kodi.set_setting('export_path', export_path)
    if export_path:
        m3u_name = kodi.get_keyboard(kodi.i18n('m3u_filename'), '')
        if m3u_name:
            if export_path.startswith('special://'):
                if not export_path.endswith('/'):
                    export_path += '/'
                    kodi.set_setting('export_path', export_path)
                m3u_file = kodi.translate_path(export_path + m3u_name)
            else:
                m3u_file = os.path.join(export_path, m3u_name)
            M3UUtils(m3u_file, from_list).export()


@DISPATCHER.register(MODES.CLEARHISTORY)
def clear_history():
    play_history.clear()


@DISPATCHER.register(MODES.URLRESOLVER)
def urlresolver_settings():
    kodi.Addon(id='script.module.urlresolver').openSettings()
