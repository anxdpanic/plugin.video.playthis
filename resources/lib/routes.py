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

from utils import PlayHistory
from addon_lib.kodi import Addon
from addon_lib.constants import DISPATCHER, MODES
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


@DISPATCHER.register(MODES.DELETE, ['path'])
def delete_url(path):
    if '%' not in path:
        path = quote(path)
    play_history.delete(path)


@DISPATCHER.register(MODES.PLAY, ['path'], ['player', 'history'])
def play(path, player=True, history=True):
    if history:
        history = path
        if '%' not in history:
            history = quote(history)
        play_history.add(history)
    play_this(unquote(path), player=player)


@DISPATCHER.register(MODES.CLEARHISTORY)
def clear_history():
    play_history.clear()


@DISPATCHER.register(MODES.URLRESOLVER)
def urlresolver_settings():
    Addon(id='script.module.urlresolver').openSettings()
