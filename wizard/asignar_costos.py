# -*- encoding: utf-8 -*-

from openerp.osv import osv, fields
import logging
from dateutil import relativedelta
from dateutil import parser
import datetime

class asignar_costos(osv.osv_memory):
    _name = 'produccion.asignar_costos.wizard'

    _columns = {
        'fecha_inicio': fields.date('Fecha inicio', required=True),
        'fecha_fin': fields.date('Fecha fin', required=True),
        'wizard_move_ids': fields.many2many('account.move', 'produccion_wizard_move_rel', 'wizard_id', 'move_id', string='Costos asociados'),
        'cuentas_costos_ids': fields.many2many('account.account', 'produccion_wizard_cuentas_costos_rel', 'wizard_id', 'cuenta_costo_id', string='Cuentas de costos'),
        'cuenta_inventario_id': fields.many2one('account.account', 'Cuenta de inventario'),
        'cuenta_costo_ventas_id': fields.many2one('account.account', 'Cuenta de costo de ventas'),
        'diario_id': fields.many2one('account.journal', 'Diario'),
    }

    def boton_asignar_costos(self, cr, uid, ids, context=None):
        logging.warn(ids)
        for w in self.browse(cr, uid, ids, context):
            totales_cuentas_costos = {}
            for account in w.cuentas_costos_ids:
                totales_cuentas_costos[account.id] = 0

            total_costos_asociados = 0
            for move in w.wizard_move_ids:
                for line in move.line_id:
                    if line.account_id.id in totales_cuentas_costos:
                        totales_cuentas_costos[line.account_id.id] += line.debit - line.credit
                        total_costos_asociados += line.debit - line.credit

#            sale_ids = self.pool.get('sale.order').search(cr, uid, [('date_order', '>=', w.fecha_inicio), ('date_order', '<=', w.fecha_fin)])
            sale_ids = self.pool.get('sale.order').search(cr, uid, [('state', '=', 'sent'),('date_confirm', '>=', w.fecha_inicio), ('date_confirm', '<=', w.fecha_fin)])
            total_costos_general = 0
            for sale in self.pool.get('sale.order').browse(cr, uid, sale_ids, context=context):
                total_costos_pedido = 0
                for order_line in sale.order_line:
                    if order_line.product_id.type == 'product':
                        for route in order_line.product_id.route_ids:
                            if route.name == 'Manufacture':
                                total_costos_pedido += order_line.product_id.standard_price * product_uom_qty
                self.pool.get('sale.order').write(cr, uid, sale.id, {'total_costos': total_costos_pedido})
                total_costos_general += total_costos_pedido

            for sale in self.pool.get('sale.order').browse(cr, uid, sale_ids, context=context):
                porcentaje_costos = 0
                if total_costos_general > 0:
                    porcentaje_costos = sale.total_costos / total_costos_general
                self.pool.get('sale.order').write(cr, uid, sale.id, {'costos_extras': total_costos_asociados * porcentaje_costos})

            move_id = self.pool.get('account.move').create(cr, uid, {'journal_id': w.diario_id.id}, context=context)
            for cuenta_costo_id in totales_cuentas_costos:
                self.pool.get('account.move.line').create(cr, uid, {'move_id': move_id, 'name':'Cuenta de costos', 'account_id': cuenta_costo_id, 'debit': totales_cuentas_costos[cuenta_costo_id]}, context=context)
            self.pool.get('account.move.line').create(cr, uid, {'move_id': move_id, 'name':'Cuenta de inventario', 'account_id': w.cuenta_inventario_id.id, 'credit': total_costos_asociados}, context=context)
            self.pool.get('account.move.line').create(cr, uid, {'move_id': move_id, 'name':'Cuenta de inventario', 'account_id': w.cuenta_inventario_id.id, 'debit': total_costos_asociados}, context=context)
            self.pool.get('account.move.line').create(cr, uid, {'move_id': move_id, 'name':'Cuenta de costo de ventas', 'account_id': w.cuenta_costo_ventas_id.id, 'credit': total_costos_asociados}, context=context)
        return {'type': 'ir.actions.act_window_close'}
