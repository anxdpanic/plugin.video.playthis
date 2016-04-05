"""
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
import strings
import json

addon = xbmcaddon.Addon()
get_setting = addon.getSetting
show_settings = addon.openSettings
sleep = xbmc.sleep
__log = xbmc.log

def execute_jsonrpc(command):
    if not isinstance(command, basestring):
        command = json.dumps(command)
    response = xbmc.executeJSONRPC(command)
    return json.loads(response)

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

def create_item(queries, label, thumb='', fanart='', is_folder=None, is_playable=None, total_items=0, menu_items=None, replace_menu=False):
    list_item = xbmcgui.ListItem(label, iconImage=thumb, thumbnailImage=thumb)
    add_item(queries, list_item, fanart, is_folder, is_playable, total_items, menu_items, replace_menu)

def add_item(queries, list_item, fanart='', is_folder=None, is_playable=None, total_items=0, menu_items=None, replace_menu=False):
    if menu_items is None: menu_items = []
    if is_folder is None:
        is_folder = False if is_playable else True

    if is_playable is None:
        playable = 'false' if is_folder else 'true'
    else:
        playable = 'true' if is_playable else 'false'

    liz_url = get_plugin_url(queries)
    if fanart: list_item.setProperty('fanart_image', fanart)
    list_item.setInfo('video', {'title': list_item.getLabel()})
    list_item.setProperty('isPlayable', playable)
    list_item.addContextMenuItems(menu_items, replaceItems=replace_menu)
    xbmcplugin.addDirectoryItem(int(sys.argv[1]), liz_url, list_item, isFolder=is_folder, totalItems=total_items)

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
        builtin = "XBMC.Notification(%s,%s, %s, %s)" % (header, msg, duration, icon_path)
        xbmc.executebuiltin(builtin)

def get_current_view():
    skinPath = translate_path('special://skin/')
    xml = os.path.join(skinPath, 'addon.xml')
    f = xbmcvfs.File(xml)
    read = f.read()
    f.close()
    try: src = re.search('defaultresolution="([^"]+)', read, re.DOTALL).group(1)
    except: src = re.search('<res.+?folder="([^"]+)', read, re.DOTALL).group(1)
    src = os.path.join(skinPath, src, 'MyVideoNav.xml')
    f = xbmcvfs.File(src)
    read = f.read()
    f.close()
    match = re.search('<views>([^<]+)', read, re.DOTALL)
    if match:
        views = match.group(1)
        for view in views.split(','):
            if xbmc.getInfoLabel('Control.GetLabel(%s)' % (view)): return view

def refresh_container():
    xbmc.executebuiltin("XBMC.Container.Refresh")

def update_container(url):
    xbmc.executebuiltin('Container.Update(%s)' % (url))

def get_keyboard(heading, default=''):
    keyboard = xbmc.Keyboard()
    keyboard.setHeading(heading)
    if default: keyboard.setDefault(default)
    keyboard.doModal()
    if keyboard.isConfirmed():
        return keyboard.getText()
    else:
        return None

def i18n(string_id):
    try:
        return addon.getLocalizedString(strings.STRINGS[string_id]).encode('utf-8', 'ignore')
    except Exception as e:
        xbmc.log('%s: Failed String Lookup: %s (%s)' % (get_name(), string_id, e), xbmc.LOGWARNING)
        return string_id

class WorkingDialog(object):
    def __init__(self):
        xbmc.executebuiltin('ActivateWindow(busydialog)')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        xbmc.executebuiltin('Dialog.Close(busydialog)')

class ProgressDialog(object):
    def __init__(self, heading, line1='', line2='', line3='', background=False, active=True):
        if active:
            if background:
                self.pd = xbmcgui.DialogProgressBG()
                msg = line1 + line2 + line3
                self.pd.create(heading, msg)
            else:
                self.pd = xbmcgui.DialogProgress()
                self.pd.create(heading, line1, line2, line3)
            self.background = background
            self.heading = heading
            self.pd.update(0)
        else:
            self.pd = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.pd is not None:
            self.pd.close()
            del self.pd

    def is_canceled(self):
        if self.pd is not None and not self.background:
            return self.pd.iscanceled()
        else:
            return False

    def update(self, percent, line1='', line2='', line3=''):
        if self.pd is not None:
            if self.background:
                msg = line1 + line2 + line3
                self.pd.update(percent, self.heading, msg)
            else:
                self.pd.update(percent, line1, line2, line3)
