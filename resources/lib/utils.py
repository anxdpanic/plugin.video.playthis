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

import re
from addon_lib import kodi
from addon_lib import log_utils
from addon_lib.constants import DATABASE, MODES
from addon_lib.playback import resolve
from urllib2 import quote, unquote


class PlayHistory:
    TABLE = 'play_0_0_1'
    ID = kodi.get_id()

    def __init__(self):
        self.create_table()

    @staticmethod
    def size_limit():
        return int(kodi.get_setting('history-size-limit'))

    @staticmethod
    def use_directory():
        if kodi.get_setting('history-list-type') == '1':
            return True
        else:
            return False

    def vacuum(self, table=None):
        if table is None:
            table = self.TABLE
        DATABASE.execute('VACUUM {0!s}'.format(table))

    def add(self, url):
        execute = 'INSERT INTO {0!s} (addon_id, url) VALUES (?, ?)'.format(self.TABLE)
        inserted = DATABASE.execute(execute, (self.ID, str(url)))
        if inserted == 1:
            execute = 'SELECT COUNT(*) FROM {0!s} WHERE addon_id=?'.format(self.TABLE)
            result = int(DATABASE.fetch(execute, (self.ID,))[0][0])
            if result > self.size_limit():
                execute = 'DELETE FROM {0!s} WHERE ROWID = (SELECT MIN(ROWID) FROM {0!s}) AND addon_id=?'.format(self.TABLE)
                result, rowcount = DATABASE.execute_w_rowcount(execute, (self.ID,))
                if rowcount < 1:
                    execute = 'DELETE * FROM {0!s} WHERE addon_id=?'.format(self.TABLE)
                    result, rowcount = DATABASE.execute_w_rowcount(execute, (self.ID,))
                    if rowcount < 1:
                        result = DATABASE.execute('DROP TABLE {0!s}'.format(self.TABLE))
                        self.vacuum()
                        self.create_table()
                if rowcount > 0:
                    self.vacuum()

    def delete_url(self, url):
        execute = 'DELETE FROM {0!s} WHERE url=? AND addon_id=?'.format(self.TABLE)
        result, rowcount = DATABASE.execute_w_rowcount(execute, (url, self.ID))
        if result != 1:
            kodi.notify(msg=kodi.i18n('delete_failed'), sound=False)
        if rowcount > 0:
            self.vacuum()
        return result, rowcount

    def delete_row_id(self, row_id):
        execute = 'DELETE FROM {0!s} WHERE id=? AND addon_id=?'.format(self.TABLE)
        result, rowcount = DATABASE.execute_w_rowcount(execute, (row_id, self.ID))
        if result != 1:
            kodi.notify(msg=kodi.i18n('delete_failed'), sound=False)
        return result, rowcount

    def get(self, include_ids=False):
        execute = 'SELECT * FROM {0!s} WHERE addon_id=? ORDER BY id DESC'.format(self.TABLE)
        selected = DATABASE.fetch(execute, (self.ID,))
        results = []
        if selected:
            for id_key, addon_id, query in selected:
                if not include_ids:
                    results.extend([unquote(query)])
                else:
                    results.extend([(id_key, unquote(query))])
            return results
        else:
            return []

    def clear(self):
        result = DATABASE.execute('DROP TABLE {0!s}'.format(self.TABLE), '')
        if result == 1:
            self.vacuum()
            kodi.notify(msg=kodi.i18n('history_cleared'), sound=False)
        else:
            kodi.notify(msg=kodi.i18n('fail_history_clear'), sound=False)

    def get_input(self):
        got_input = kodi.get_keyboard(kodi.i18n('enter_for_playback'), '')
        if got_input is not None:
            got_input = got_input.strip()
        if got_input:
            got_input = quote(re.sub(r'\s+', ' ', got_input))
            self.add(got_input)
            return got_input
        return ''

    def history_dialog(self):
        if self.size_limit() != 0:
            queries = self.get()
            if len(queries) > 0:
                queries.insert(0, '[B]{0!s}[/B]'.format(kodi.i18n('new_')))
                queries.insert(1, '[B]{0!s}[/B]'.format(kodi.i18n('clear_history')))
                index = kodi.Dialog().select(kodi.i18n('choose_playback'), queries)
                if index > -1:
                    if index == 1:
                        self.clear()
                        return ''
                    elif index > 1:
                        return queries[index]
                else:
                    return ''
        return self.get_input()

    def history_directory(self):
        icon_path = kodi.get_icon()
        fanart_path = kodi.get_fanart()
        total_items = None
        if self.size_limit() != 0:
            queries = self.get(include_ids=True)
            if len(queries) > 0:
                total_items = len(queries) + 2
                kodi.create_item({'mode': MODES.NEW, 'player': 'true'}, '[B]{0!s}[/B]'.format(kodi.i18n('new_')),
                                 thumb=icon_path, fanart=fanart_path, is_folder=False, is_playable=False,
                                 total_items=total_items)
                kodi.create_item({'mode': MODES.CLEARHISTORY}, '[B]{0!s}[/B]'.format(kodi.i18n('clear_history')),
                                 thumb=icon_path, fanart=fanart_path, total_items=total_items)
                for row_id, item in queries:
                    menu_items = [(kodi.i18n('delete_url'), 'RunPlugin(%s)' %
                                   (kodi.get_plugin_url({'mode': MODES.DELETE, 'row_id': row_id}))),
                                  (kodi.i18n('export_list_m3u'), 'RunPlugin(%s)' %
                                   (kodi.get_plugin_url({'mode': MODES.EXPORT_M3U})))]
                    kodi.create_item({'mode': MODES.PLAY, 'player': 'false', 'history': 'false', 'path': quote(item)},
                                     item.encode('utf-8'), thumb=icon_path, fanart=fanart_path, is_folder=False,
                                     is_playable=True, total_items=total_items, menu_items=menu_items)
        if not total_items:
            kodi.create_item({'mode': MODES.NEW, 'player': 'true'}, kodi.i18n('new_'), thumb=icon_path,
                             fanart=fanart_path, is_folder=False, is_playable=False)
        kodi.end_of_directory(cache_to_disc=False)

    def create_table(self):
        DATABASE.execute('CREATE TABLE IF NOT EXISTS {0!s} (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                         'addon_id, url, CONSTRAINT unq UNIQUE (addon_id, url))'.format(self.TABLE), '')


class M3UUtils:

    def __init__(self, filename, from_list='history'):
        if not from_list:
            from_list = 'history'
        self.from_list = from_list
        self.filename = filename

    def _get(self):
        log_utils.log('M3UUtils._get from_list: |{0!s}|'.format(self.from_list), log_utils.LOGDEBUG)
        if self.from_list == 'history':
            return PlayHistory().get()
        else:
            return []

    def export(self):
        items = self._get()
        if items:
            _m3u = '#EXTM3U\n'
            m3u = _m3u
            for item in items:
                resolved = resolve(item)
                title = item
                if resolved:
                    log_utils.log('M3UUtils.export adding resolved item: |{0!s}| as |{1!s}|'.format(resolved, title),
                                  log_utils.LOGDEBUG)
                    m3u += '#EXTINF:{0!s},{1!s}\n{2!s}\n'.format('0', title, resolved)
                else:
                    log_utils.log('M3UUtils.export adding unresolved item: |{0!s}| as |{1!s}|'.format(item, title),
                                  log_utils.LOGDEBUG)
                    m3u += '#EXTINF:{0!s},{1!s}\n{2!s}\n'.format('0', title, item)

            if m3u != _m3u:
                m3u_file = self.filename if self.filename.endswith('.m3u') else self.filename + '.m3u'
                log_utils.log('M3UUtils.export writing .m3u: |{0!s}|'.format(m3u_file), log_utils.LOGDEBUG)
                try:
                    with open(m3u_file, 'w+') as f:
                        f.write(m3u)
                    log_utils.log('M3UUtils.export writing .m3u completed.', log_utils.LOGDEBUG)
                    kodi.notify(msg=kodi.i18n('export_success'), sound=False)
                    return
                except:
                    log_utils.log('M3UUtils.export failed to write .m3u', log_utils.LOGDEBUG)
                    kodi.notify(msg=kodi.i18n('export_fail'), sound=False)
                    return
        log_utils.log('M3UUtils.export no items for export to .m3u', log_utils.LOGDEBUG)
        kodi.notify(msg=kodi.i18n('no_items_export'), sound=False)
