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

import installer
import todo
import gtk_contact_form
import wizard
import os
import base64
import random
import tools
from osv import fields, osv
import netsvc
from tools.translate import _

class base_setup_config_choice(osv.osv_memory):
    """
    """
    _name = 'base.setup.config'
    logger = netsvc.Logger()

    def _get_image(self, cr, uid, context=None):
        file_no = str(random.randint(1,3))
        path = os.path.join('base','res','config_pixmaps/%s.png'%file_no)
        file_data = tools.file_open(path,'rb').read()
        return base64.encodestring(file_data)

    def get_users(self, cr, uid, context={}):
        user_obj = self.pool.get('res.users')
        user_ids = user_obj.search(cr, uid, [])
        users = user_obj.browse(cr, uid, user_ids)
        user_str = '\n'.join(map(lambda x: '    - %s :\n\t\tLogin : %s \n\t\tPassword : %s' % (x.name, x.login, x.password), users))
        return _('The following users have been installed : \n')+ user_str

    _columns = {
        'installed_users':fields.text('Installed Users', readonly=True),
        'config_logo' : fields.binary('Image', readonly=True),
        }

    _defaults = {
        'installed_users':get_users,
         'config_logo' : _get_image
        }

    def set_default_menu(self, cr, uid, menu, context=None):
        user = self.pool.get('res.users')\
                        .browse(cr, uid, uid, context=context)

        user.write({'action_id': menu.id,
                    'menu_id': menu.id})

    def get_default_menu(self, cr, uid, context=None):
        actions = self.pool.get('ir.actions.act_window')

        current_menu_id = actions.search(cr, uid, [('name','=','Menu')],
                                         context=context)
        assert len(current_menu_id) == 1,\
               'A given user should only have one menu item'
        return actions.browse(cr, uid, current_menu_id[0], context=context)

    def menu(self, cr, uid, ids, context=None):
        menu = self.get_default_menu(cr, uid, context=context)
        self.set_default_menu(cr, uid, menu, context=context)

        if menu.view_id.id:
            view_id = (menu.view_id.id, menu.view_id.name)
        else:
            view_id = False

        return {
            'name': menu.name,
            'type': menu.type,
            'view_id': view_id,
            'domain': menu.domain,
            'res_model': menu.res_model,
            'src_model': menu.src_model,
            'view_type': menu.view_type,
            'view_mode': menu.view_mode,
            'views': menu.views,
        }

    def config(self, cr, uid, ids, context=None):
        menu = self.get_default_menu(cr, uid, context=context)
        self.set_default_menu(cr, uid, menu, context=context)

        return self.pool.get('res.config').next(cr, uid, [], context=context)

base_setup_config_choice()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

