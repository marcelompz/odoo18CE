# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPackingListWizard(models.TransientModel):
    _name = 'stock.packing.list.wizard'
    _description = 'Wizard de Generacion de Packing List'

    picking_id = fields.Many2one(
        comodel_name='stock.picking', string='Nota de Remision',
        required=True, readonly=True,
    )
    date = fields.Date(string='Fecha', default=fields.Date.context_today, required=True)
    incoterm_id = fields.Many2one(comodel_name='account.incoterms', string='Incoterm')
    transport_mode = fields.Selection(
        selection=[('air', 'Aereo'), ('sea', 'Maritimo'), ('road', 'Terrestre / Carretera'), ('rail', 'Ferroviario')],
        string='Modo de Transporte', default='road',
    )
    port_origin = fields.Char(string='Puerto / Aeropuerto de Salida')
    port_destination = fields.Char(string='Puerto / Aeropuerto de Llegada')
    country_dest_id = fields.Many2one(comodel_name='res.country', string='Pais de Destino')
    consignee_partner_id = fields.Many2one(comodel_name='res.partner', string='Consignatario')
    invoice_id = fields.Many2one(comodel_name='account.move', string='Factura de Exportacion')
    notes = fields.Text(string='Observaciones')

    # Estrategia de pre-poblacion de bultos
    grouping_mode = fields.Selection(
        selection=[
            ('one_box_per_product', 'Un BOX por producto (rapido)'),
            ('one_box_all', 'Un solo BOX con todos los productos'),
        ],
        string='Modo de agrupacion',
        default='one_box_all',
        required=True,
        help='Define como pre-poblar los bultos. Despues de generar, podes '
             'reorganizar las lineas entre bultos manualmente.',
    )
    line_ids = fields.One2many(
        comodel_name='stock.packing.list.wizard.line',
        inverse_name='wizard_id', string='Lineas',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        picking_id = self.env.context.get('default_picking_id') or self.env.context.get('active_id')
        if picking_id:
            picking = self.env['stock.picking'].browse(picking_id)
            res['picking_id'] = picking.id
            if picking.partner_id:
                res['consignee_partner_id'] = picking.partner_id.id
                if picking.partner_id.country_id:
                    res['country_dest_id'] = picking.partner_id.country_id.id

            invoice = self.env['account.move']
            if picking.sale_id:
                invoice = picking.sale_id.invoice_ids.filtered(
                    lambda m: m.move_type == 'out_invoice' and m.state in ('draft', 'posted')
                )[:1]
            if invoice:
                res['invoice_id'] = invoice.id

            grouped = defaultdict(lambda: {'qty': 0.0, 'uom_id': False})
            for ml in picking.move_line_ids:
                qty = ml.quantity if 'quantity' in ml._fields else ml.qty_done
                if not qty:
                    continue
                key = ml.product_id.id
                if not grouped[key]['uom_id']:
                    grouped[key]['uom_id'] = ml.product_uom_id.id
                grouped[key]['qty'] += qty

            lines = []
            seq = 10
            for product_id, data in grouped.items():
                product = self.env['product.product'].browse(product_id)
                lines.append((0, 0, {
                    'sequence': seq,
                    'product_id': product.id,
                    'description': product.name,
                    'ncm': product.ncm or '',
                    'quantity': data['qty'],
                    'uom_id': data['uom_id'] or product.uom_id.id,
                    'net_weight': (product.weight or 0.0) * data['qty'],
                    'volume': (product.volume or 0.0) * data['qty'],
                }))
                seq += 10
            res['line_ids'] = lines
        return res

    def action_generate(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_(
                'No hay lineas para generar el Packing List. '
                'Verifique que el picking tenga movimientos confirmados.'
            ))

        # Crear el Packing List
        pl_vals = {
            'picking_id': self.picking_id.id,
            'date': self.date,
            'incoterm_id': self.incoterm_id.id if self.incoterm_id else False,
            'transport_mode': self.transport_mode,
            'port_origin': self.port_origin,
            'port_destination': self.port_destination,
            'country_dest_id': self.country_dest_id.id if self.country_dest_id else False,
            'consignee_partner_id': self.consignee_partner_id.id if self.consignee_partner_id else False,
            'invoice_id': self.invoice_id.id if self.invoice_id else False,
            'notes': self.notes,
        }
        packing_list = self.env['stock.packing.list'].create(pl_vals)

        Package = self.env['stock.packing.list.package']
        Line = self.env['stock.packing.list.line']

        if self.grouping_mode == 'one_box_all':
            # Un solo BOX con todas las lineas
            pkg = Package.create({
                'packing_list_id': packing_list.id,
                'sequence': 10,
                'name': 'BOX 1',
            })
            for idx, line in enumerate(self.line_ids, start=1):
                Line.create({
                    'package_id': pkg.id,
                    'sequence': idx * 10,
                    'product_id': line.product_id.id if line.product_id else False,
                    'description': line.description,
                    'ncm': line.ncm,
                    'quantity': line.quantity,
                    'uom_id': line.uom_id.id if line.uom_id else False,
                    'net_weight': line.net_weight,
                    'volume': line.volume,
                })
        else:
            # Un BOX por producto/linea
            for idx, line in enumerate(self.line_ids, start=1):
                pkg = Package.create({
                    'packing_list_id': packing_list.id,
                    'sequence': idx * 10,
                    'name': 'BOX %d' % idx,
                })
                Line.create({
                    'package_id': pkg.id,
                    'sequence': 10,
                    'product_id': line.product_id.id if line.product_id else False,
                    'description': line.description,
                    'ncm': line.ncm,
                    'quantity': line.quantity,
                    'uom_id': line.uom_id.id if line.uom_id else False,
                    'net_weight': line.net_weight,
                    'volume': line.volume,
                })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Packing List'),
            'res_model': 'stock.packing.list',
            'view_mode': 'form',
            'res_id': packing_list.id,
            'target': 'current',
        }


class StockPackingListWizardLine(models.TransientModel):
    _name = 'stock.packing.list.wizard.line'
    _description = 'Linea del Wizard de Packing List'
    _order = 'sequence, id'

    wizard_id = fields.Many2one(
        comodel_name='stock.packing.list.wizard',
        required=True, ondelete='cascade',
    )
    sequence = fields.Integer(string='Sec', default=10)
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    description = fields.Char(string='Descripcion', required=True)
    ncm = fields.Char(string='NCM')
    quantity = fields.Float(string='Cantidad', digits='Product Unit of Measure')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='UdM')
    net_weight = fields.Float(string='Peso Neto (kg)', digits=(16, 3))
    volume = fields.Float(string='Volumen (m3)', digits=(16, 4))

    @api.onchange('product_id', 'quantity')
    def _onchange_product_or_qty(self):
        if self.product_id:
            p = self.product_id
            if not self.description:
                self.description = p.name
            if not self.uom_id:
                self.uom_id = p.uom_id.id
            if not self.ncm and p.ncm:
                self.ncm = p.ncm
            qty = self.quantity or 0.0
            if qty > 0:
                self.net_weight = (p.weight or 0.0) * qty
                if not self.volume and p.volume:
                    self.volume = p.volume * qty
