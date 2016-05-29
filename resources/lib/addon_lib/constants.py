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
import db_utils
from url_dispatcher import URL_Dispatcher


def __enum(**enums):
    return type('Enum', (), enums)


DATABASE_VERSION = 1
DATABASE_FILE = kodi.translate_path('special://database/{0!s}{1!s}.db'.format(kodi.get_name(), str(DATABASE_VERSION)))
DATABASE = db_utils.SQLite(DATABASE_FILE)
DISPATCHER = URL_Dispatcher()

RESOLVER_DIR = kodi.translate_path('special://home/addons/{0!s}/resources/lib/addon_lib/resolvers/'.format(kodi.get_id()))

MODES = __enum(
    MAIN='main',
    PLAY='play',
    CLEARHISTORY='clearhistory',
    NEW='new',
    ADD='add',
    DELETE='delete',
    URLRESOLVER='urlresolver')
