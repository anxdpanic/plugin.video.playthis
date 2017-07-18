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
from addon_lib import kodi, cache
from addon_lib.utils import PlayHistory, M3UUtils, STRMUtils
from addon_lib.constants import DISPATCHER, MODES, COOKIE_FILE, THUMBNAILS_DIR
from addon_lib.remote import HttpJSONRPC
from urllib2 import unquote


@DISPATCHER.register(MODES.MAIN, kwargs=['content_type'])
def main_route(content_type=''):
    if not content_type:
        return
    content = 'files'
    if content_type == 'audio':
        content = 'songs'
    elif content_type == 'image':
        content = 'images'
    elif content_type == 'video':
        content = 'videos'
    kodi.set_content(content)
    play_history = PlayHistory()
    if play_history.use_directory():
        play_history.history_directory(content_type)
    else:
        playback_item = play_history.history_dialog(content_type)
        if playback_item:
            from addon_lib.playback import play_this
            play_this(unquote(playback_item), player=True)


@DISPATCHER.register(MODES.NEW, kwargs=['player'])
def get_new_item(player=True):
    play_history = PlayHistory()
    playback_item = play_history.get_input()
    if playback_item:
        from addon_lib.playback import play_this
        play_this(unquote(playback_item), title=unquote(playback_item), player=player)


@DISPATCHER.register(MODES.ADD, ['path'])
def add_url(path):
    from addon_lib.playback import play_this
    play_this(path, title=path, player='history')


@DISPATCHER.register(MODES.RENAME, ['row_id'], ['refresh'])
def rename_row_id(row_id, refresh=True):
    label = kodi.get_keyboard(kodi.i18n('input_new_label'))
    if label:
        play_history = PlayHistory()
        result = play_history.rename_row_id(row_id, label)
        if result and refresh:
            kodi.refresh_container()


@DISPATCHER.register(MODES.CHANGETHUMB, ['row_id'], ['local', 'refresh'])
def change_thumb_by_row_id(row_id, local=True, refresh=True):
    if local:
        thumbnail = kodi.Dialog().browse(2, kodi.i18n('choose_thumbnail'), 'pictures', '', True, False, THUMBNAILS_DIR)
    else:
        thumbnail = kodi.get_keyboard(kodi.i18n('input_new_thumb'))
    if thumbnail and (not thumbnail.endswith('/')) and (not thumbnail.endswith('\\')):
        play_history = PlayHistory()
        result = play_history.change_thumb(row_id, thumbnail)
        if result and refresh:
            kodi.refresh_container()


@DISPATCHER.register(MODES.DELETE, ['row_id'], ['title', 'refresh'])
def delete_row(row_id, title='', refresh=True):
    confirmed = kodi.Dialog().yesno(kodi.i18n('confirm'), '%s \'%s\'%s' % (kodi.i18n('delete_url'), unquote(title), '?'))
    if confirmed:
        play_history = PlayHistory()
        result, rowcount = play_history.delete_row_id(row_id)
        if (result, rowcount) == (1, 1) and refresh:
            kodi.refresh_container()


@DISPATCHER.register(MODES.PLAY, ['path'], ['player', 'history', 'thumb', 'title'])
def play(path, player=True, history=None, thumb='', title=''):
    from addon_lib.playback import play_this
    play_this(unquote(path), player=player, history=history, thumbnail=unquote(thumb), title=unquote(title))


@DISPATCHER.register(MODES.SENDREMOTE, ['path'], ['thumb', 'title'])
def play_remote(path, thumb='', title=''):
    rpc_client = HttpJSONRPC()
    command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Player.GetActivePlayers'}
    response = rpc_client.execute_rpc(command)
    if 'error' in response:
        kodi.notify(kodi.get_name(), response['error'], duration=7000)
        return
    try:
        player_id = response['result'][0]['playerid']
    except IndexError:
        player_id = None
    if player_id == 2:  # stop picture player if active, it will block
        command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Player.Stop', 'params': {'playerid': player_id}}
        response = rpc_client.execute_rpc(command)
        if 'error' in response:
            kodi.notify(kodi.get_name(), response['error'], duration=7000)
            return
    filename = kodi.get_plugin_url({'mode': MODES.PLAY, 'player': 'false', 'path': path, 'thumb': thumb, 'title': title})
    command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Player.Open', 'params': {'item': {'file': filename}}}
    response = rpc_client.execute_rpc(command)
    if 'error' in response:
        kodi.notify(kodi.get_name(), response['error'], duration=7000)
    else:
        if 'No Response' not in response['result']:
            kodi.notify(kodi.get_name(), kodi.i18n('send_success'))


@DISPATCHER.register(MODES.EXPORT_MENU, args=['row_id', 'ctype'])
def export_context(row_id, ctype):
    context_items = ['export_strm(row_id=row_id)', 'export_m3u(ctype=ctype)']
    select_items = [kodi.i18n('export_to_strm'), kodi.i18n('export_list_m3u')]
    result = kodi.Dialog().select(kodi.i18n('export'), select_items)
    if result != -1:
        eval(context_items[result])


@DISPATCHER.register(MODES.MANAGE_MENU, args=['row_id', 'title'])
def manage_context(row_id, title):
    context_items = ['rename_row_id(row_id=row_id)', 'change_thumb_by_row_id(row_id=row_id)',
                     'change_thumb_by_row_id(row_id=row_id, local=False)', 'delete_row(row_id=row_id, title=unquote(title))']
    select_items = [kodi.i18n('rename'), kodi.i18n('local_thumb'), kodi.i18n('url_thumb'), kodi.i18n('delete_url')]
    result = kodi.Dialog().select(kodi.i18n('manage'), select_items)
    if result != -1:
        eval(context_items[result])


@DISPATCHER.register(MODES.EXPORT_M3U, kwargs=['export_path', 'from_list', 'ctype'])
def export_m3u(export_path=None, from_list='history', ctype='video'):
    if export_path is None:
        export_path = kodi.get_setting('export_path')
        if not export_path:
            export_path = kodi.Dialog().browse(3, kodi.i18n('export_path'), 'files', '', False, False)
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
            M3UUtils(m3u_file, from_list).export(ctype=ctype)


@DISPATCHER.register(MODES.EXPORT_STRM, args=['row_id'], kwargs=['export_path'])
def export_strm(row_id, export_path=None):
    if export_path is None:
        export_path = kodi.get_setting('export_path_strm')
        if not export_path:
            export_path = kodi.Dialog().browse(3, kodi.i18n('export_path_strm'), 'files', '', False, False)
            kodi.set_setting('export_path_strm', export_path)
    if export_path:
        default_filename = ''
        play_history = PlayHistory()
        rows = play_history.get(row_id=row_id)
        if rows:
            url, content_type, title, thumb = rows[0]
            default_filename = kodi.string_to_filename(title) + '.strm'
        strm_name = kodi.get_keyboard(kodi.i18n('strm_filename'), default_filename)
        if strm_name:
            if export_path.startswith('special://'):
                if not export_path.endswith('/'):
                    export_path += '/'
                    kodi.set_setting('export_path_strm', export_path)
                strm_file = kodi.translate_path(export_path + strm_name)
            else:
                strm_file = os.path.join(export_path, strm_name)
            STRMUtils(strm_file).export(row_id)


@DISPATCHER.register(MODES.CLEARHISTORY, kwargs=['ctype'])
def clear_history(ctype=None):
    ltype = ctype
    if ltype is None:
        ltype = 'all'
    confirmed = kodi.Dialog().yesno(kodi.i18n('confirm'), kodi.i18n('clear_yes_no') % ltype)
    if confirmed:
        play_history = PlayHistory()
        play_history.clear(ctype)
        kodi.refresh_container()


@DISPATCHER.register(MODES.CLEARCACHE)
def clear_cache():
    confirmed = kodi.Dialog().yesno(kodi.i18n('confirm'), kodi.i18n('cache_yes_no'))
    if confirmed:
        result = cache.reset_cache()
        if result:
            kodi.notify(msg=kodi.i18n('cache_success'), sound=False)
        else:
            kodi.notify(msg=kodi.i18n('cache_failed'), sound=False)


@DISPATCHER.register(MODES.CLEARCOOKIES)
def clear_cookies():
    confirmed = kodi.Dialog().yesno(kodi.i18n('confirm'), kodi.i18n('cookies_yes_no'))
    if confirmed:
        try:
            if kodi.vfs.exists(COOKIE_FILE):
                result = kodi.vfs.delete(COOKIE_FILE)
            else:
                result = True
        except:
            result = False
        if result:
            kodi.notify(msg=kodi.i18n('cookies_success'), sound=False)
        else:
            kodi.notify(msg=kodi.i18n('cookies_failed'), sound=False)


@DISPATCHER.register(MODES.URLRESOLVER)
def urlresolver_settings():
    kodi.Addon(id='script.module.urlresolver').openSettings()


@DISPATCHER.register(MODES.YOUTUBEDL)
def youtubedl_settings():
    kodi.Addon(id='script.module.youtube.dl').openSettings()
