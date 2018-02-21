from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp


class sale_order(osv.osv):
    _inherit = "sale.order"

    _columns = {
        'costos_extras': fields.float('Costos extras', digits_compute= dp.get_precision('Product Price')),
        'total_costos': fields.float('Total costos', digits_compute= dp.get_precision('Product Price')),
    }
