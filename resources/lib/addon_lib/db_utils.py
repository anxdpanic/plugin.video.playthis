# -*- coding: UTF-8 -*-
"""
    Copyright (C) 2016 anxdpanic

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

import log_utils
from sqlite3 import dbapi2 as sql


class SQLite:
    BEFORE_COMMIT_SQL = ['PRAG']
    AFTER_COMMIT_SQL = ['VACU']

    def __init__(self, db_file):
        """
        :param db_file: str: containing path to sqlite database file
        """
        self.db_file = db_file

    def __db_connect_(self):
        """
        :return: instance: sqlite connection to db_file
                     None: on error
        """
        connection = None
        try:
            connection = sql.connect(self.db_file)
            connection.isolation_level = None
        except sql.Error as e:
            log_utils.log(str(e), log_utils.LOGERROR)
            connection = None
        finally:
            return connection

    def execute_w_rowcount(self, sql_statement, sql_params=None):
        """
        wrapper for cursor.execute
        :param sql_statement: str: sql_statement may be parameterized (i. e. placeholders instead of SQL literals)
        :param sql_params: tuple, dict: sql_params supports two kinds of placeholders;
                                        tuple:  question marks (qmark style)
                                        dict:   named placeholders (named style).
        :return: tuple: int:   0: on error
                               1: sql_statement successfully executed, committed
                               2: duplicate record on insert
                        int:   rows affected

        """
        if not sql_params: sql_params = ''
        connection = self.__db_connect_()
        if not connection: return 0
        connection.text_factory = str
        cursor = connection.cursor()
        result = 0
        rowcount = -1
        try:
            cursor.execute(sql_statement, sql_params)
            connection.commit()
            result = 1
        except sql.IntegrityError:
            result = 2
        except sql.Error as e:
            connection.rollback()
            log_utils.log(str(e), log_utils.LOGERROR)
            result = 0
        finally:
            rowcount = cursor.rowcount
            cursor.close()
            connection.close()
            return result, rowcount

    def execute(self, sql_statement, sql_params=None, suppress=False):
        """
        wrapper for cursor.execute
        :param sql_statement: str: sql_statement may be parameterized (i. e. placeholders instead of SQL literals)
        :param sql_params: tuple, dict: sql_params supports two kinds of placeholders;
                                        tuple:  question marks (qmark style)
                                        dict:   named placeholders (named style).
        :param suppress: bool: suppress error log output

        :return: int:   0: on error
                        1: sql_statement successfully executed, committed
                        2: duplicate record on insert

        """
        if not sql_params: sql_params = ''
        connection = self.__db_connect_()
        if not connection: return 0
        connection.text_factory = str
        cursor = connection.cursor()
        try:
            if sql_statement[:4] in self.BEFORE_COMMIT_SQL:
                cursor.execute(sql_statement, sql_params)
            if (sql_statement[:4] not in self.BEFORE_COMMIT_SQL) and (sql_statement[:4] not in self.AFTER_COMMIT_SQL):
                cursor.execute('BEGIN', '')
                cursor.execute(sql_statement, sql_params)
                cursor.execute('COMMIT', '')
            if sql_statement[:4] in self.AFTER_COMMIT_SQL:
                cursor.execute(sql_statement, sql_params)
            connection.commit()
        except sql.IntegrityError:
            return 2
        except sql.Error as e:
            connection.rollback()
            if not suppress:
                log_utils.log(str(e), log_utils.LOGERROR)
            return 0
        finally:
            cursor.close()
            connection.close()
        return 1

    def execute_many(self, sql_statements):
        """
        wrapper for cursor.execute, list of statements in single transaction
        (performance increase over execute when multiple statements)
        :param sql_statements: list of [sql_statement, params]
        :param sql_statement: str: sql_statement may be parameterized (i. e. placeholders instead of SQL literals)
        :param sql_params: tuple, dict: sql_params supports two kinds of placeholders;
                                        tuple:  question marks (qmark style)
                                        dict:   named placeholders (named style).
        :return: int:   0: on error
                        1: sql_statement successfully executed, committed
                        2: duplicate record on insert

        """
        connection = self.__db_connect_()
        if not connection: return 0
        connection.text_factory = str
        cursor = connection.cursor()
        try:
            cursor.execute('BEGIN', '')
            for sql_statement, sql_params in sql_statements:
                if not sql_params: sql_params = ''
                cursor.execute(sql_statement, sql_params)
            cursor.execute('COMMIT', '')
            connection.commit()
        except sql.IntegrityError:
            return 2
        except sql.Error as e:
            connection.rollback()
            log_utils.log(str(e), log_utils.LOGERROR)
            return 0
        finally:
            cursor.close()
            connection.close()
        return 1

    def fetch(self, sql_statement, sql_params=None):
        """
        wrapper for cursor.fetchall
        :param sql_statement: str: sql_statement may be parameterized (i. e. placeholders instead of SQL literals)
        :param sql_params: tuple, dict: sql_params supports two kinds of placeholders;
                                        tuple:  question marks (qmark style)
                                        dict:   named placeholders (named style).
        :return:        list of tuples: results of cursor.fetchall()
                                  None: on error
        """
        if not sql_params: sql_params = ''
        connection = self.__db_connect_()
        if not connection: return None
        connection.text_factory = str
        cursor = connection.cursor()
        try:
            cursor.execute(sql_statement, sql_params)
            try:
                return cursor.fetchall()
            except:
                return cursor.fetchone()
        except sql.Error as e:
            log_utils.log(str(e), log_utils.LOGERROR)
            return None
        finally:
            cursor.close()
            connection.close()
