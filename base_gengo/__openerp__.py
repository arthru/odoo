# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
{
    'name': 'Automated Translations through Gengo API',
    'version': '0.1',
    'category': 'Tools',
    'description': """
Automated Translations through Gengo API
----------------------------------------
    The module will install passive Scheduler job for Automated Translations 
using Gnego API. To active translation Configure your gengo authentication 
parameters under `Settings > Companies > Gengo Parameters1 and Launch the 
Gengo Language Sync Wizard under `Settings > Application Terms > 
Gengo: Manual Request of Translation` and follow the wizard. This wizard will
active the Scheduler and will start active translation via Gengo Services,
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'init_xml': ['gengo_sync_schedular_data.xml'],
    'update_xml': [
        'ir_translation.xml',
        'res_company_view.xml',
        'wizard/base_gengo_translations_view.xml',
           ],
    'demo_xml': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    #'qweb': ['static/src/xml/base_gengo.xml'],
    #'js': ['static/src/js/base_gengo.js'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
