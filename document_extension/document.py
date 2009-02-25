# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
import re
from osv import osv, fields
from osv.orm import except_orm
import pooler

class document_directory(osv.osv):
    _inherit='document.directory'
    _columns = {
        'versioning': fields.boolean('Automatic Versioning'),
        'version_regex' : fields.char('Reg. Ex.',size=64,required=True),
        'version_replace': fields.char('Replace',size=64,required=True)
    }
    _defaults={
        'versioning':lambda *a:1,
        'version_regex':lambda *a:'^(.*)(\..*)$',
        'version_replace':lambda *a:"\\1.vcount\\2"
    }
document_directory()
class document_file(osv.osv):
    _inherit = 'ir.attachment'
    def write(self, cr, uid, ids, vals, context=None):
        for document in self.browse(cr,uid,ids,context=context):
            if document.parent_id and document.parent_id.versioning:
                count=1
                if  self._check_duplication(cr,uid,vals,[document.id]):
                         #version code
                         newname=''
                         filename=vals.get('datas_fname',False)
                         temp=vals.get('datas',False)
                         pattern=document.parent_id.version_regex
                         replace=document.parent_id.version_replace.replace('count',str(count))
                         newname=re.sub(pattern,replace, filename)

                         pool = pooler.get_pool(cr.dbname)
                         data = self.browse(cr, uid, ids[0], context=context)
                         if not 'name' in vals :
                             vals.update({'name':data.name,'datas':temp,'parent_id':data.parent_id.id,'datas_fname':filename})
                         self.create(cr, uid, vals, context=context)
                         vals['datas_fname'] = newname
                         vals['datas']=data.datas

        result = super(document_file,self).write(cr,uid,ids,vals,context=context)
        cr.commit()
        return result

document_file()
