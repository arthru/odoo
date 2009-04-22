# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import urllib
from urllib import urlopen, urlencode, unquote

import wizard
from osv import fields, osv
import pooler
import re

trans_form = '''<?xml version="1.0"?>
    <form string="Translate" colspan="4">
         <newline/>
         <label string="Translate Terms using google" align="0.0" colspan="3"/>
         <newline/>
     </form>
         '''
trans_fields = { }

trans_sum = '''<?xml version="1.0"?>
        <form string=" " colspan="4">
             <newline/>
             <label string="Successfullly Translat" align="0.0" colspan="3"/>
             <newline/>
        </form>
         '''
trans_sum_fields = { }

def setUserAgent(userAgent):
    urllib.FancyURLopener.version = userAgent
    pass

def translate(self,cr,uid,data,context):
    pool = pooler.get_pool(cr.dbname)
    translation_obj=pool.get('ir.translation').browse(cr, uid,data['id'], context)
    in_lang=context['lang'][:2].lower().encode('utf-8')
    out_lang= translation_obj['lang'][:2].lower().encode('utf-8')
    src=translation_obj['src'].encode('utf-8')
    setUserAgent("Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008070400 SUSE/3.0.1-0.1 Firefox/3.0.1")
    try:
        post_params = urllib.urlencode({"langpair":"%s|%s" %(in_lang,out_lang), "text":src,"ie":"UTF8", "oe":"UTF8"})
    except KeyError, error:
        return
    page = urllib.urlopen("http://translate.google.com/translate_t", post_params)
    content = page.read()
    page.close()
    match = re.search("<div id=result_box dir=\"ltr\">(.*?)</div>", content)
    value = match.groups()[0]
    pool.get('ir.translation').write(cr, uid, data['id'],{'value':value})
    return {}

class Transaltor(wizard.interface):
    states = {
            'init': {
             'actions': [],
                'result': {'type': 'form', 'arch':trans_form, 'fields':trans_fields, 'state':[('end','Cancel','gtk-cancel'),('translate','Translate','gtk-ok')]}
                },
            'translate': {
                'actions': [translate],
                'result': {'type': 'form', 'arch':trans_sum, 'fields':trans_sum_fields, 'state':[('end','OK','gtk-ok')]}
                },
            }

Transaltor('trans_wizard')