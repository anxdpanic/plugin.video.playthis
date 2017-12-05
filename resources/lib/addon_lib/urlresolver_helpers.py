"""
    URLResolver Addon for Kodi
    Copyright (C) 2016 t0mm0, tknorris

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
import re
import urllib
import jsunpack
import log_utils
from kodi import i18n


class ResolverError(Exception):
    pass


def get_hidden(html, form_id=None, index=None, include_submit=True):
    hidden = {}
    if form_id:
        pattern = '''<form [^>]*(?:id|name)\s*=\s*['"]?%s['"]?[^>]*>(.*?)</form>''' % (form_id)
    else:
        pattern = '''<form[^>]*>(.*?)</form>'''

    html = cleanse_html(html)

    for i, form in enumerate(re.finditer(pattern, html, re.DOTALL | re.I)):
        log_utils.log(form.group(1))
        if index is None or i == index:
            for field in re.finditer('''<input [^>]*type=['"]?hidden['"]?[^>]*>''', form.group(1)):
                match = re.search('''name\s*=\s*['"]([^'"]+)''', field.group(0))
                match1 = re.search('''value\s*=\s*['"]([^'"]*)''', field.group(0))
                if match and match1:
                    hidden[match.group(1)] = match1.group(1)

            if include_submit:
                match = re.search('''<input [^>]*type=['"]?submit['"]?[^>]*>''', form.group(1))
                if match:
                    name = re.search('''name\s*=\s*['"]([^'"]+)''', match.group(0))
                    value = re.search('''value\s*=\s*['"]([^'"]*)''', match.group(0))
                    if name and value:
                        hidden[name.group(1)] = value.group(1)

        log_utils.log('Hidden fields are: %s' % (hidden))
    return hidden


def pick_source(sources):
    if len(sources) >= 1:
        return sources[0][1]
    else:
        raise ResolverError(i18n('no_video_link'))


def append_headers(headers):
    return '|%s' % '&'.join(['%s=%s' % (key, urllib.quote_plus(headers[key])) for key in headers])


def get_packed_data(html):
    packed_data = ''
    for match in re.finditer('(eval\s*\(function.*?)</script>', html, re.DOTALL | re.I):
        try:
            js_data = jsunpack.unpack(match.group(1))
            js_data = js_data.replace('\\', '')
            packed_data += js_data
        except:
            pass

    return packed_data


def parse_sources_list(html):
    sources = []
    match = re.search('''['"]?sources['"]?\s*:\s*\[(.*?)\]''', html, re.DOTALL)
    if match:
        sources = [(match[1], match[0].replace('\/', '/')) for match in re.findall('''['"]?file['"]?\s*:\s*['"]([^'"]+)['"][^}]*['"]?label['"]?\s*:\s*['"]([^'"]*)''', match.group(1), re.DOTALL)]
    return sources


def parse_html5_source_list(html):
    label_attrib = 'type' if not re.search('''<source\s+src\s*=.*?data-res\s*=.*?/\s*>''', html) else 'data-res'
    sources = [(match[1], match[0].replace('\/', '/')) for match in re.findall('''<source\s+src\s*=\s*['"]([^'"]+)['"](?:.*?''' + label_attrib + '''\s*=\s*['"](?:video/)?([^'"]+)['"])''', html, re.DOTALL)]
    return sources


def parse_smil_source_list(smil):
    sources = []
    base = re.search('base\s*=\s*"([^"]+)', smil).groups()[0]
    for i in re.finditer('src\s*=\s*"([^"]+)(?:"\s*(?:width|height)\s*=\s*"([^"]+))?', smil):
        label = 'Unknown'
        if (len(i.groups()) > 1) and (i.group(2) is not None):
            label = i.group(2)
        sources += [(label, '%s playpath=%s' % (base, i.group(1)))]
    return sources


def cleanse_html(html):
    for match in re.finditer('<!--(.*?)-->', html, re.DOTALL):
        if match.group(1)[-2:] != '//': html = html.replace(match.group(0), '')

    html = re.sub('''<(div|span)[^>]+style=["'](visibility:\s*hidden|display:\s*none);?["']>.*?</\\1>''', '', html, re.I | re.DOTALL)
    return html
