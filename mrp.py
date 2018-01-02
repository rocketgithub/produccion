# -*- encoding: utf-8 -*-

from openerp.osv import osv, fields
from openerp.tools import float_compare, float_is_zero
from openerp.tools.translate import _
import logging

class mrp_production(osv.osv):
    _inherit = 'mrp.production'

    def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        """ To produce final product based on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        @param production_id: the ID of mrp.production object
        @param production_qty: specify qty to produce in the uom of the production order
        @param production_mode: specify production mode (consume/consume&produce).
        @param wiz: the mrp produce product wizard, which will tell the amount of consumed products needed
        @return: True
        """
        stock_mov_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get("product.uom")
        production = self.browse(cr, uid, production_id, context=context)
        production_qty_uom = uom_obj._compute_qty(cr, uid, production.product_uom.id, production_qty, production.product_id.uom_id.id)
        precision = self.pool['decimal.precision'].precision_get(cr, uid, 'Product Unit of Measure')

        ##
        ## Cambiar orden de calculo, primero consumir y luego producirs
        ##
        main_production_move = False
        if production_mode == 'consume_produce':
            for produce_product in production.move_created_ids:
                if produce_product.product_id.id == production.product_id.id:
                    main_production_move = produce_product.id

        if production_mode in ['consume', 'consume_produce']:
            if wiz:
                consume_lines = []
                for cons in wiz.consume_lines:
                    consume_lines.append({'product_id': cons.product_id.id, 'lot_id': cons.lot_id.id, 'product_qty': cons.product_qty})
            else:
                consume_lines = self._calculate_qty(cr, uid, production, production_qty_uom, context=context)
            for consume in consume_lines:
                remaining_qty = consume['product_qty']
                for raw_material_line in production.move_lines:
                    if raw_material_line.state in ('done', 'cancel'):
                        continue
                    if remaining_qty <= 0:
                        break
                    if consume['product_id'] != raw_material_line.product_id.id:
                        continue
                    consumed_qty = min(remaining_qty, raw_material_line.product_qty)
                    stock_mov_obj.action_consume(cr, uid, [raw_material_line.id], consumed_qty, raw_material_line.location_id.id,
                                                 restrict_lot_id=consume['lot_id'], consumed_for=main_production_move, context=context)
                    remaining_qty -= consumed_qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    #consumed more in wizard than previously planned
                    product = self.pool.get('product.product').browse(cr, uid, consume['product_id'], context=context)
                    extra_move_id = self._make_consume_line_from_data(cr, uid, production, product, product.uom_id.id, remaining_qty, False, 0, context=context)
                    stock_mov_obj.write(cr, uid, [extra_move_id], {'restrict_lot_id': consume['lot_id'],
                                                                    'consumed_for': main_production_move}, context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)

        ##
        ## Calcular costo
        ##
        costo = 0
        for l in production.move_lines2:
            if l.state == 'done':
                cantidad = l.product_qty
                if l.location_dest_id.id == production.location_src_id.id:
                    cantidad *= -1
                if l.state == 'done':
                    costo += l.price_unit * cantidad
        logging.warn("costo")
        logging.warn(costo)

        main_production_move = False
        if production_mode == 'consume_produce':
            # To produce remaining qty of final product
            produced_products = {}
            for produced_product in production.move_created_ids2:
                if produced_product.scrapped:
                    continue
                if not produced_products.get(produced_product.product_id.id, False):
                    produced_products[produced_product.product_id.id] = 0
                produced_products[produced_product.product_id.id] += produced_product.product_qty
            for produce_product in production.move_created_ids:
                subproduct_factor = self._get_subproduct_factor(cr, uid, production.id, produce_product.id, context=context)
                lot_id = False
                if wiz:
                    lot_id = wiz.lot_id.id
                qty = min(subproduct_factor * production_qty_uom, produce_product.product_qty) #Needed when producing more than maximum quantity
                ##
                ## Escribir nuevo costo
                ##
                logging.warn("costo/qty")
                logging.warn(costo/qty)
                stock_mov_obj.write(cr, uid, [produce_product.id], {'price_unit': costo/qty}, context=context)
                new_moves = stock_mov_obj.action_consume(cr, uid, [produce_product.id], qty,
                                                         location_id=produce_product.location_id.id, restrict_lot_id=lot_id, context=context)
                stock_mov_obj.write(cr, uid, new_moves, {'production_id': production_id}, context=context)
                remaining_qty = subproduct_factor * production_qty_uom - qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    # In case you need to make more than planned
                    #consumed more in wizard than previously planned
                    extra_move_id = stock_mov_obj.copy(cr, uid, produce_product.id, default={'product_uom_qty': remaining_qty,
                                                                                             'production_id': production_id}, context=context)
                    stock_mov_obj.action_confirm(cr, uid, [extra_move_id], context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)

                if produce_product.product_id.id == production.product_id.id:
                    main_production_move = produce_product.id

            ##
            ## Cambiar el costo del producto
            ##
            for produce_product in production.move_created_ids2:
                stock_mov_obj._store_average_cost_price(cr, uid, produce_product, context=context)

        self.message_post(cr, uid, production_id, body=_("%s produced") % self._description, context=context)

        # Remove remaining products to consume if no more products to produce
        if not production.move_created_ids and production.move_lines:
            stock_mov_obj.action_cancel(cr, uid, [x.id for x in production.move_lines], context=context)

        self.signal_workflow(cr, uid, [production_id], 'button_produce_done')
        return True

    # def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
    #     stock_mov_obj = self.pool.get('stock.move')
    #     uom_obj = self.pool.get("product.uom")
    #     production = self.browse(cr, uid, production_id, context=context)
    #     production_qty_uom = uom_obj._compute_qty(cr, uid, production.product_uom.id, production_qty, production.product_id.uom_id.id)
    #
    #     #
    #     # Calcular el costo
    #     #
    #     if wiz:
    #         consume_lines = []
    #         for cons in wiz.consume_lines:
    #             consume_lines.append({'product': cons.product_id, 'product_qty': cons.product_qty})
    #     else:
    #         consume_lines = self._calculate_qty(cr, uid, production, production_qty_uom, context=context)
    #
    #     total_cost = 0
    #     for consume in consume_lines:
    #         total_cost += consume['product'].standard_price * consume['product_qty']
    #
    #     for produce_product in production.move_created_ids:
    #         subproduct_factor = self._get_subproduct_factor(cr, uid, production.id, produce_product.id, context=context)
    #         qty = min(subproduct_factor * production_qty_uom, produce_product.product_qty)
    #         stock_mov_obj.write(cr, uid, [produce_product.id], {'price_unit': total_cost/qty}, context=context)
    #
    #     res = super(mrp_production, self).action_produce(cr, uid, production_id, production_qty, production_mode, wiz=wiz, context=context)
    #
    #     #
    #     # Cambiar el costo del producto
    #     #
    #     for produce_product in production.move_created_ids2:
    #         stock_mov_obj._store_average_cost_price(cr, uid, produce_product, context=context)
    #
    #     return True
