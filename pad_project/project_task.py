# -*- coding: utf-8 -*-
from tools.translate import _
from osv import fields, osv

class task(osv.osv):
    _name = "project.task"
    _inherit = ["project.task",'pad.common']
    _columns = {
        'description_pad': fields.char('Description PAD', pad_content_field='description')
    }
