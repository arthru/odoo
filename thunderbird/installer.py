# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields
from osv import osv
from tools import config

import base64

class thunderbird_installer(osv.osv_memory):
    _name = 'thunderbird.installer'
    _inherit = 'res.config.installer'

    def process_plugin(self, cr, uid, ids, context):
        """
        Default Attach Thunderbird Plug-in File.
        """
        data = {}
        file = open(config['addons_path'] + "/thunderbird/plugin/tiny_plugin-2.0.xpi", 'r')
        data['plugin_file'] = base64.encodestring(file.read())
        self.write(cr, uid, ids, data)
        return False

    _columns = {
        'name':fields.char('File name', size=34, required=True, help='Save Thunderbird plugin file.'),
        'thunderbird':fields.boolean('Thunderbird Module ', help="Allows you to select an object that you’d like to add to your email and its attachments."),
        'plugin_file':fields.binary('Thunderbird Plug-in', readonly=True, help="Thunderbird plug-in file. Save as this file and install this plug-in in thunderbir."),
        
        }
    _defaults = {
        'thunderbird' : True,
        'name' : 'tiny_plugin-2.0.xpi',
        }

thunderbird_installer()
