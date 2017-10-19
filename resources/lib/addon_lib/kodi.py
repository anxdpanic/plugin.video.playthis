# -*- coding: utf-8 -*-
"""
    Original Source can be found included in the original_sources/ directory

    SALTS XBMC Addon
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

import xbmcaddon
import xbmcplugin
import xbmcgui
import xbmc
import xbmcvfs
import urllib
import urlparse
import sys
import os
import re
import json
import strings
import time

__log = xbmc.log

Addon = xbmcaddon.Addon
Dialog = xbmcgui.Dialog
Player = xbmc.Player
execute_builtin = xbmc.executebuiltin
sleep = xbmc.sleep
conditional_visibility = xbmc.getCondVisibility
get_supported_media = xbmc.getSupportedMedia
vfs = xbmcvfs

addon = xbmcaddon.Addon()
get_setting = addon.getSetting
show_settings = addon.openSettings


def execute_jsonrpc(command):
    if not isinstance(command, basestring):
        command = json.dumps(command)
    response = xbmc.executeJSONRPC(command)
    return json.loads(response)


def get_handle():
    return int(sys.argv[1])


def get_path():
    return addon.getAddonInfo('path').decode('utf-8')


def get_profile():
    return addon.getAddonInfo('profile').decode('utf-8')


def translate_path(path):
    return xbmc.translatePath(path).decode('utf-8')


def set_setting(id, value):
    if not isinstance(value, basestring): value = str(value)
    addon.setSetting(id, value)


def get_version():
    return addon.getAddonInfo('version')


def get_id():
    return addon.getAddonInfo('id')


def get_name():
    return addon.getAddonInfo('name')


def get_icon():
    return os.path.join(get_path(), 'icon.png')


def get_fanart():
    return os.path.join(get_path(), 'fanart.jpg')


def get_plugin_url(queries):
    try:
        query = urllib.urlencode(queries)
    except UnicodeEncodeError:
        for k in queries:
            if isinstance(queries[k], unicode):
                queries[k] = queries[k].encode('utf-8')
        query = urllib.urlencode(queries)

    return sys.argv[0] + '?' + query


def end_of_directory(cache_to_disc=True):
    xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=cache_to_disc)


def set_content(content):
    xbmcplugin.setContent(int(sys.argv[1]), content)


def create_item(queries, label, thumb='', fanart='', is_folder=None, is_playable=None, total_items=0, menu_items=None,
                replace_menu=False, content_type='video', info=None):
    list_item = ListItem(label)
    add_item(queries, list_item, thumb, fanart, is_folder, is_playable, total_items,
             menu_items, replace_menu, content_type=content_type, info=info)


def add_item(queries, list_item, thumb='', fanart='', is_folder=None, is_playable=None, total_items=0, menu_items=None,
             replace_menu=False, content_type='video', info=None):
    if menu_items is None: menu_items = []

    if info is None: info = {'title': list_item.getLabel()}
    if not thumb: thumb = get_icon()
    if not fanart: fanart = get_fanart()

    if is_folder is None:
        is_folder = False if is_playable else True

    if is_playable is None:
        playable = 'false' if is_folder else 'true'
    else:
        playable = 'true' if is_playable else 'false'

    liz_url = queries
    if isinstance(queries, dict):
        liz_url = get_plugin_url(queries)

    list_item.setArt({'icon': thumb, 'thumb': thumb, 'fanart': fanart})
    list_item.setInfo(content_type, info)
    list_item.setProperty('isPlayable', playable)
    list_item.addContextMenuItems(menu_items, replaceItems=replace_menu)
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), liz_url, list_item, isFolder=is_folder, totalItems=total_items)


def get_playlist(list_type, new=False):
    # 0 = music, # 1 = video
    pl = xbmc.PlayList(list_type)
    if new:
        pl.clear()
    return pl


def parse_query(query):
    q = {'mode': 'main'}
    if query.startswith('?'): query = query[1:]
    queries = urlparse.parse_qs(query)
    for key in queries:
        if len(queries[key]) == 1:
            q[key] = queries[key][0]
        else:
            q[key] = queries[key]
    return q


def notify(header=None, msg='', duration=2000, sound=None):
    if header is None: header = get_name()
    if sound is None: sound = get_setting('mute_notifications') == 'false'
    icon_path = os.path.join(get_path(), 'icon.png')
    try:
        xbmcgui.Dialog().notification(header, msg, icon_path, duration, sound)
    except:
        builtin = "Notification(%s, %s, %s, %s)" % (header, msg, duration, icon_path)
        xbmc.executebuiltin(builtin)


def set_resolved_url(list_item, resolved=True):
    xbmcplugin.setResolvedUrl(get_handle(), resolved, list_item)


def get_info_label(name):
    return xbmc.getInfoLabel('%s') % name


def get_current_view():
    skinPath = translate_path('special://skin/')
    xml = os.path.join(skinPath, 'addon.xml')
    f = xbmcvfs.File(xml)
    read = f.read()
    f.close()
    try:
        src = re.search('defaultresolution="([^"]+)', read, re.DOTALL).group(1)
    except:
        src = re.search('<res.+?folder="([^"]+)', read, re.DOTALL).group(1)
    src = os.path.join(skinPath, src, 'MyVideoNav.xml')
    f = xbmcvfs.File(src)
    read = f.read()
    f.close()
    match = re.search('<views>([^<]+)', read, re.DOTALL)
    if match:
        views = match.group(1)
        for view in views.split(','):
            if xbmc.getInfoLabel('Control.GetLabel(%s)' % view): return view


def refresh_container():
    xbmc.executebuiltin("Container.Refresh")


def update_container(url):
    xbmc.executebuiltin('Container.Update(%s)' % (url))


def get_keyboard(heading, default=''):
    keyboard = xbmc.Keyboard()
    keyboard.setHeading(heading)
    if default: keyboard.setDefault(default)
    keyboard.doModal()
    if keyboard.isConfirmed():
        return keyboard.getText().strip()
    else:
        return None


def i18n(string_id):
    try:
        return addon.getLocalizedString(strings.STRINGS[string_id]).encode('utf-8', 'ignore')
    except Exception as e:
        xbmc.log('%s: Failed String Lookup: %s (%s)' % (get_name(), string_id, e), xbmc.LOGWARNING)
        return string_id


def string_to_filename(string):
    filename = string.strip()
    filename = filename.replace(' ', '_')
    filename = ''.join(c for c in filename if c.isalnum() or c in ('.', '_'))
    filename = re.sub('_{2,}', '_', filename)
    return filename


def addon_enabled(addon_id):
    rpc_request = {"jsonrpc": "2.0",
                   "method": "Addons.GetAddonDetails",
                   "id": 1,
                   "params": {"addonid": "%s" % addon_id,
                              "properties": ["enabled"]}
                   }
    response = execute_jsonrpc(rpc_request)
    try:
        return response['result']['addon']['enabled'] is True
    except KeyError:
        message = response['error']['message']
        code = response['error']['code']
        error = 'Requested |%s| received error |%s| and code: |%s|' % (rpc_request, message, code)
        xbmc.log(error, xbmc.LOGINFO)
        return False


def set_addon_enabled(addon_id, enabled=True):
    rpc_request = {"jsonrpc": "2.0",
                   "method": "Addons.SetAddonEnabled",
                   "id": 1,
                   "params": {"addonid": "%s" % addon_id,
                              "enabled": enabled}
                   }
    response = execute_jsonrpc(rpc_request)
    try:
        return response['result'] == 'OK'
    except KeyError:
        message = response['error']['message']
        code = response['error']['code']
        error = 'Requested |%s| received error |%s| and code: |%s|' % (rpc_request, message, code)
        xbmc.log(error, xbmc.LOGINFO)
        return False


def stop_player(player_id=None):
    # 0 = audio, 1 = video, 2 = image, None = Active
    if player_id is None:
        rpc_request = {"id": 1, "jsonrpc": "2.0", "method": "Player.GetActivePlayers"}
        response = execute_jsonrpc(rpc_request)
        try:
            player_id = response['result'][0]['playerid']
        except IndexError:  # player not running or already stopped
            return True
    rpc_request = {"id": 1, "jsonrpc": "2.0", "method": "Player.Stop", "params": {"playerid": player_id}}
    response = execute_jsonrpc(rpc_request)
    try:
        return response['result'] == 'OK'
    except KeyError:
        message = response['error']['message']
        code = response['error']['code']
        error = 'Requested |%s| received error |%s| and code: |%s|' % (rpc_request, message, code)
        xbmc.log(error, xbmc.LOGINFO)
        return False


def close_dialog(dialog_name, forced=True):
    if not forced:
        forced = 'false'
    else:
        forced = 'true'
    xbmc.executebuiltin('Dialog.Close(%s,%s)' % (dialog_name, forced))


def get_kodi_version():
    class MetaClass(type):
        def __str__(self):
            return '|%s| -> |%s|%s|%s|%s|%s|' % (self.version, self.major, self.minor, self.tag, self.tag_version, self.revision)

    class KodiVersion(object):
        __metaclass__ = MetaClass
        version = xbmc.getInfoLabel('System.BuildVersion').decode('utf-8')
        match = re.search('([0-9]+)\.([0-9]+)', version)
        if match: major, minor = match.groups()
        match = re.search('-([a-zA-Z]+)([0-9]*)', version)
        if match: tag, tag_version = match.groups()
        match = re.search('\w+:(\w+-\w+)', version)
        if match: revision = match.group(1)

        try:
            major = int(major)
        except:
            major = 0
        try:
            minor = int(minor)
        except:
            minor = 0
        try:
            revision = revision.decode('utf-8')
        except:
            revision = u''
        try:
            tag = tag.decode('utf-8')
        except:
            tag = u''
        try:
            tag_version = int(tag_version)
        except:
            tag_version = 0

    return KodiVersion


class WorkingDialog(object):
    wd = None

    def __init__(self):
        try:
            self.wd = xbmcgui.DialogBusy()
            self.wd.create()
            self.update(0)
        except:
            xbmc.executebuiltin('ActivateWindow(busydialog)')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.wd is not None:
            self.wd.close()
        else:
            xbmc.executebuiltin('Dialog.Close(busydialog)')

    def is_canceled(self):
        if self.wd is not None:
            return self.wd.iscanceled()
        else:
            return False

    def update(self, percent):
        if self.wd is not None:
            self.wd.update(percent)


class ProgressDialog(object):
    pd = None

    def __init__(self, heading, line1='', line2='', line3='', background=False, active=True, timer=0):
        self.begin = time.time()
        self.timer = timer
        self.background = background
        self.heading = heading

        if active and not timer:
            self.pd = self.__create_dialog(line1, line2, line3)
            self.pd.update(0)

    def __create_dialog(self, line1, line2, line3):
        if self.background:
            pd = xbmcgui.DialogProgressBG()
            msg = line1 + line2 + line3
            pd.create(self.heading, msg)
        else:
            pd = xbmcgui.DialogProgress()
            pd.create(self.heading, line1, line2, line3)
        return pd

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.pd is not None:
            self.pd.close()

    def is_canceled(self):
        if self.pd is not None and not self.background:
            return self.pd.iscanceled()
        else:
            return False

    def update(self, percent, line1='', line2='', line3=''):
        if self.pd is None and self.timer and (time.time() - self.begin) >= self.timer:
            self.pd = self.__create_dialog(line1, line2, line3)

        if self.pd is not None:
            if self.background:
                msg = line1 + line2 + line3
                self.pd.update(percent, self.heading, msg)
            else:
                self.pd.update(percent, line1, line2, line3)


class CountdownDialog(object):
    __INTERVALS = 5
    pd = None

    def __init__(self, heading, line1='', line2='', line3='', active=True, countdown=60, interval=5):
        self.heading = heading
        self.countdown = countdown
        self.interval = interval
        self.line3 = line3
        if active:
            pd = xbmcgui.DialogProgress()
            if not self.line3: line3 = 'Expires in: %s seconds' % (countdown)
            pd.create(self.heading, line1, line2, line3)
            pd.update(100)
            self.pd = pd

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.pd is not None:
            self.pd.close()

    def start(self, func, args=None, kwargs=None):
        if args is None: args = []
        if kwargs is None: kwargs = {}
        result = func(*args, **kwargs)
        if result:
            return result

        start = time.time()
        expires = time_left = int(self.countdown)
        interval = self.interval
        while time_left > 0:
            for _ in range(CountdownDialog.__INTERVALS):
                sleep(interval * 1000 / CountdownDialog.__INTERVALS)
                if self.is_canceled(): return
                time_left = expires - int(time.time() - start)
                if time_left < 0: time_left = 0
                progress = time_left * 100 / expires
                line3 = 'Expires in: %s seconds' % (time_left) if not self.line3 else ''
                self.update(progress, line3=line3)

            result = func(*args, **kwargs)
            if result:
                return result

    def is_canceled(self):
        if self.pd is None:
            return False
        else:
            return self.pd.iscanceled()

    def update(self, percent, line1='', line2='', line3=''):
        if self.pd is not None:
            self.pd.update(percent, line1, line2, line3)


class ListItem(xbmcgui.ListItem):
    def setArt(self, dictionary):
        if get_kodi_version().major < 16 and 'icon' in dictionary:
            self.setIconImage(dictionary['icon'])
            del dictionary['icon']
        super(ListItem, self).setArt(dictionary)
