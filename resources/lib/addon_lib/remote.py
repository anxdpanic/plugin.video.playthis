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

    example:
        def play_remote(filename):
            rpc_client = HttpJSONRPC(ip_address='192.168.1.25', port='8080', username='kodi', password='kodi')
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
            command = {'jsonrpc': '2.0', 'id': 1, 'method': 'Player.Open', 'params': {'item': {'file': filename}}}
            response = rpc_client.execute_rpc(command)
            if 'error' in response:
                kodi.notify(kodi.get_name(), response['error'], duration=7000)
            else:
                kodi.notify(kodi.get_name(), kodi.i18n('remote_play_success'))
"""

import json
import base64
import urllib2
import socket
import kodi
import log_utils


class HttpJSONRPC:
    def __init__(self, ip_address=None, port=None, username=None, password=None):
        self.ip_address = kodi.get_setting('remote-ip') if ip_address is None else ip_address
        self.port = kodi.get_setting('remote-port') if port is None else port
        self.username = kodi.get_setting('remote-username').strip() if username is None else username
        self.password = kodi.get_setting('remote-password') if password is None else password
        self.has_connection_details = self.ip_address and self.port and self.username and self.password
        self.url = 'http://%s:%s/jsonrpc' % (self.ip_address, self.port) if self.has_connection_details else None
        self.authorization = base64.b64encode(self.username + b':' + self.password) if self.has_connection_details else None
        self.headers = {'User-Agent': '%s/%s' % (kodi.get_name(), kodi.get_version()),
                        'Content-Type': 'application/json'}
        if self.authorization:
            self.headers.update({'Authorization': b'Basic ' + self.authorization})

        self.connection_details_error = ''
        if not self.has_connection_details:
            self.connection_details_error = 'Missing connection details:'
            if not self.ip_address:
                self.connection_details_error += ' |IP address|'
            if not self.port:
                self.connection_details_error += ' |Port|'
            if not self.username:
                self.connection_details_error += ' |Username|'
            if not self.password:
                self.connection_details_error += ' |Password|'

    def execute_rpc(self, command):
        if not self.has_connection_details:
            log_utils.log('JSON-RPC Unable to complete request. %s' % self.connection_details_error, log_utils.LOGINFO)
            return {'error': self.connection_details_error}
        log_utils.log('JSON-RPC request |%s|' % command, log_utils.LOGDEBUG)
        null_response = None
        data = json.dumps(command)
        request = urllib2.Request(self.url, headers=self.headers, data=data)
        method = 'POST'
        request.get_method = lambda: method
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as e:
            error = 'JSON-RPC received HTTPError |[Code %s] %s|' % (e.code, e.msg)
            log_utils.log(error, log_utils.LOGINFO)
            return {'error': 'HTTPError |[Code %s] %s|' % (e.code, e.msg)}
        except urllib2.URLError as e:
            error = 'JSON-RPC received URLError |%s|' % e.args
            log_utils.log(error, log_utils.LOGINFO)
            return {'error': 'URLError |%s|' % e.args}
        except socket.timeout as e:
            response = None
            null_response = {'result': 'No response/Timed out'}  # some requests do not respond timely. (ie. Player.Open + picture)

        if not null_response and response:
            contents = response.read()
            log_utils.log('JSON-RPC response |%s|' % contents, log_utils.LOGDEBUG)
            json_response = json.loads(contents)
            response.close()
        else:
            json_response = null_response
            log_utils.log('JSON-RPC response |%s|' % null_response, log_utils.LOGDEBUG)
        return self._eval_response(json_response)

    @staticmethod
    def _eval_response(response):
        if 'error' in response:
            message = response['error']['message']
            code = response['error']['code']
            error = 'JSON-RPC received error |%s| and code: |%s|' % (message, code)
            log_utils.log(error, log_utils.LOGINFO)
            return {'error': 'JSON-RPC error |[Code %s] %s|' % (code, message)}
        elif 'result' in response:
            return {'result': response['result']}
        else:
            return {'error': 'JSON-RPC received an unknown response'}
