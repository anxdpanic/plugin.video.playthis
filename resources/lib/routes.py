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
from addon_lib import kodi
from addon_lib.constants import DISPATCHER, MODES
from addon_lib.playback import play_this
from urllib2 import unquote

play_history = PlayHistory()


@DISPATCHER.register(MODES.MAIN)
def main_route():
    playback_item = play_history.input()
    if playback_item:
        play_this(unquote(playback_item), player=True)
    else:
        kodi.refresh_container()


@DISPATCHER.register(MODES.PLAY, ['path'], ['player'])
def play(path, player=True):
    play_this(unquote(path), player=player)


@DISPATCHER.register(MODES.CLEARHISTORY)
def clear_history():
    play_history.clear()
