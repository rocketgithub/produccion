# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
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

from openerp.osv import osv
from openerp.tools.translate import _
import logging

class ReportCostoProduccion(osv.AbstractModel):
    _name = 'report.produccion.costo_produccion'

    def total_costo(self, o):
        costo = 0
        for l in o.move_lines2:
            if l.state == 'done':
                cantidad = l.product_qty
                if l.location_dest_id.id == o.location_src_id.id:
                    cantidad *= -1
                if l.state == 'done':
                    costo += l.price_unit * cantidad
        return costo

    def lineas(self, lineas):
        filtradas = []
        for l in lineas:
            if l.state == 'done':
                filtradas.append(l)
        return filtradas

    def render_html(self, cr, uid, ids, data=None, context=None):
        report_obj = self.pool['report']
        production_obj = self.pool['mrp.production']
        user_obj = self.pool['res.users']

        report = report_obj._get_report_from_name(cr, uid, 'produccion.costo_produccion')
        production = production_obj.browse(cr, uid, ids, context=context)
        user = user_obj.browse(cr, uid, uid, context=context)
        logging.warn([x.name for x in user.groups_id])
        mostrar_costo = 'Contable' in [x.name for x in user.groups_id]

        docargs = {
            'doc_ids': ids,
            'doc_model': report.model,
            'docs': production,
            'total_costo': self.total_costo,
            'lineas': self.lineas,
            'mostrar_costo': mostrar_costo
        }

        return report_obj.render(cr, uid, ids, 'produccion.costo_produccion', docargs, context=context)
