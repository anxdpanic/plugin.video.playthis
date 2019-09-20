# -*- coding: utf-8 -*-
"""

    Copyright (C) 2016-2019 anxdpanic

    This file is part of PlayThis (plugin.video.playthis)

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

import os

from . import kodi
from . import db_utils
from .net import get_ua


def __enum(**enums):
    return type('Enum', (), enums)


DATABASE_VERSION = 1
DATABASE_FILE = kodi.translate_path('special://database/{0!s}{1!s}.db'.format(kodi.get_name(), str(DATABASE_VERSION)))
DATABASE = db_utils.SQLite(DATABASE_FILE)

ADDON_DATA_DIR = kodi.translate_path('special://profile/addon_data/%s/' % kodi.get_id())
THUMBNAILS_DIR = kodi.translate_path('special://thumbnails/')

COOKIE_FILE = kodi.translate_path('special://temp/%s/cookies.lwp' % kodi.get_id())

MODES = __enum(
    MAIN='main',
    PLAY='play',
    CLEARHISTORY='clearhistory',
    NEW='new',
    ADD='add',
    DELETE='delete',
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
    YOUTUBEDL=kodi.translate_path('special://home/addons/script.module.youtube.dl/icon.png'),
    YOUTUBE=kodi.translate_path('special://home/addons/plugin.video.youtube/icon.png'))

RAND_UA = get_ua()
IE_USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko'
FF_USER_AGENT = 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'
OPERA_USER_AGENT = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36 OPR/34.0.2036.50'
IOS_USER_AGENT = 'Mozilla/5.0 (iPhone; CPU iPhone OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A5376e Safari/8536.25'
ANDROID_USER_AGENT = 'Mozilla/5.0 (Linux; Android 4.4.2; Nexus 4 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.114 Mobile Safari/537.36'


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
