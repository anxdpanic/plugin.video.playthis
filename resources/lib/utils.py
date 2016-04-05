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
from addon_lib.constants import DATABASE
from urllib2 import quote, unquote


class PlayHistory:
    TABLE = 'play_0_0_1'
    ID = kodi.get_id()

    def __init__(self):
        self.create_table()

    @staticmethod
    def size_limit():
        return int(kodi.get_setting('history-size-limit'))

    def add(self, url):
        execute = 'INSERT INTO {0!s} (addon_id, url) VALUES (?, ?)'.format(self.TABLE)
        inserted = DATABASE.execute(execute, (self.ID, str(url)))
        if inserted == 1:
            execute = 'SELECT COUNT(*) FROM {0!s} WHERE addon_id=?'.format(self.TABLE)
            result = int(DATABASE.fetch(execute, (self.ID,))[0][0])
            if result > self.size_limit():
                execute = 'DELETE FROM {0!s} WHERE ROWID = (SELECT MIN(ROWID) FROM {0!s}) AND addon_id=?'.format(self.TABLE)
                result = DATABASE.execute(execute, (self.ID,))
                if result == 0:
                    execute = 'DELETE * FROM {0!s} WHERE addon_id=?'.format(self.TABLE)
                    result = DATABASE.execute(execute, (self.ID,))
                    if result == 0:
                        result = DATABASE.execute('DROP TABLE {0!s}'.format(self.TABLE))
                        self.create_table()

    def get(self):
        execute = 'SELECT * FROM {0!s} WHERE addon_id=? ORDER BY id DESC'.format(self.TABLE)
        selected = DATABASE.fetch(execute, (self.ID,))
        results = []
        if selected:
            for id_key, addon_id, query in selected:
                results.extend([unquote(query)])
            return results
        else:
            return False

    def clear(self):
        result = DATABASE.execute('DROP TABLE {0!s}'.format(self.TABLE), '')
        if result == 1:
            DATABASE.execute('VACUUM {0!s}'.format(self.TABLE))
            kodi.notify(msg=kodi.i18n('history_cleared'), sound=False)
        else:
            kodi.notify(msg=kodi.i18n('fail_history_clear'), sound=False)

    def input(self):
        if self.size_limit() != 0:
            queries = self.get()
            if queries:
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
        got_input = kodi.Dialog().input(kodi.i18n('enter_for_playback'))
        got_input = got_input.strip()
        if got_input:
            got_input = quote(re.sub(r'\s+', ' ', got_input))
            self.add(got_input)
            return got_input
        return ''

    def create_table(self):
        DATABASE.execute('CREATE TABLE IF NOT EXISTS {0!s} (id INTEGER PRIMARY KEY AUTOINCREMENT, '
                         'addon_id, url, CONSTRAINT unq UNIQUE (addon_id, url))'.format(self.TABLE), '')
