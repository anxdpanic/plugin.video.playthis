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
import kodi
import db_utils
from url_dispatcher import URL_Dispatcher


def __enum(**enums):
    return type('Enum', (), enums)


DATABASE_VERSION = 1
DATABASE_FILE = kodi.translate_path('special://database/{0!s}{1!s}.db'.format(kodi.get_name(), str(DATABASE_VERSION)))
DATABASE = db_utils.SQLite(DATABASE_FILE)
DISPATCHER = URL_Dispatcher()

ADDON_DATA_DIR = kodi.translate_path('special://profile/addon_data/%s/' % kodi.get_id())
THUMBNAILS_DIR = kodi.translate_path('special://thumbnails/')
RESOLVER_DIRS = [kodi.translate_path('special://home/addons/{0!s}/resources/lib/addon_lib/resolvers/'.format(kodi.get_id())),
                 kodi.translate_path('special://home/addons/script.module.urlresolver.xxx/resources/plugins/')]

COOKIE_FILE = kodi.translate_path('special://temp/%s/cookies.lwp' % kodi.get_id())

MODES = __enum(
    MAIN='main',
    PLAY='play',
    CLEARHISTORY='clearhistory',
    NEW='new',
    ADD='add',
    DELETE='delete',
    URLRESOLVER='urlresolver',
    EXPORT_STRM='export_strm',
    EXPORT_M3U='export_m3u',
    SENDREMOTE='send_remote',
    RENAME='rename',
    CHANGETHUMB='changethumb',
    CLEARCACHE='clearcache',
    CLEARCOOKIES='clearcookies',
    YOUTUBEDL='ytdl',
    EXPORT_MENU='export_menu',
    MANAGE_MENU='manage_menu')

ICONS = __enum(
    ADDON=kodi.translate_path('special://home/addons/{0!s}/icon.png'.format(kodi.get_id())),
    KODI=kodi.translate_path('special://xbmc/media/icon256x256.png'),
    URLRESOLVER=kodi.translate_path('special://home/addons/script.module.urlresolver/icon.png'),
    YOUTUBEDL=kodi.translate_path('special://home/addons/script.module.youtube.dl/icon.png'))


def _is_cookie_file(the_file):
    exists = os.path.exists(the_file)
    if not exists:
        return False
    else:
        try:
            tmp = kodi.vfs.File(the_file).read()
            if tmp.startswith('#LWP-Cookies-2.0'):
                return True
            return False
        except:
            with open(the_file, 'r') as f:
                tmp = f.readline()
                if tmp == '#LWP-Cookies-2.0\n':
                    return True
                return False


def _create_cookie(the_file):
    try:
        if kodi.vfs.exists(the_file):
            kodi.vfs.delete(the_file)
        _file = kodi.vfs.File(the_file, 'w')
        _file.write('#LWP-Cookies-2.0\n')
        _file.close()
        return the_file
    except:
        try:
            with open(the_file, 'w') as _file:
                _file.write('#LWP-Cookies-2.0\n')
            return the_file
        except:
            return ''


if not _is_cookie_file(COOKIE_FILE):
    COOKIE_FILE = _create_cookie(COOKIE_FILE)
