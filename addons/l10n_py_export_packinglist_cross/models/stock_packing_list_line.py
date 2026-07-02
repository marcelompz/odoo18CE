# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPackingListLine(models.Model):
    """Linea de producto dentro de un Bulto (stock.packing.list.package).

    Cada linea representa un producto/cantidad dentro de UN bulto fisico.
    Multiples lineas pueden compartir el mismo bulto (productos mezclados).
    """
    _name = 'stock.packing.list.line'
    _description = 'Linea de Packing List'
    _order = 'package_id, sequence, id'

    package_id = fields.Many2one(
        comodel_name='stock.packing.list.package',
        string='Bulto / BOX',
        required=True, ondelete='cascade', index=True,
    )
    packing_list_id = fields.Many2one(
        comodel_name='stock.packing.list', string='Packing List',
        related='package_id.packing_list_id', store=True, index=True,
    )
    sequence = fields.Integer(string='Sec. en BOX', default=10)
    product_id = fields.Many2one(comodel_name='product.product', string='Producto')
    description = fields.Char(string='Descripcion', required=True)
    ncm = fields.Char(
        string='NCM',
        help='Nomenclatura Comun del Mercosur (codigo arancelario).',
    )

    # ----------------------------------------------------------------------
    # Atributos heredados del producto (related defensivos al modulo
    # utex_stock_cross). Si el modulo no esta instalado, los relateds quedan
    # vacios sin romper.
    # ----------------------------------------------------------------------
    product_model_id = fields.Many2one(
        comodel_name='product.model',
        string='Modelo',
        related='product_id.product_model_id',
        store=True, readonly=True,
    )
    product_type_use_id = fields.Many2one(
        comodel_name='product.type.use',
        string='Tipo',
        related='product_id.product_type_use_id',
        store=True, readonly=True,
    )
    product_gender_id = fields.Many2one(
        comodel_name='product.gender',
        string='Genero',
        related='product_id.product_gender_id',
        store=True, readonly=True,
    )

    quantity = fields.Float(string='Cantidad', digits='Product Unit of Measure', default=1.0)
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Unidad de Medida')
    net_weight = fields.Float(
        string='Peso Neto Linea (kg)', digits=(16, 3),
        help='Peso neto de los productos de esta linea (cantidad x peso unitario). '
             'El peso bruto se calcula a nivel de bulto.',
    )
    volume = fields.Float(string='Volumen (m3)', digits=(16, 4))

    company_id = fields.Many2one(related='package_id.company_id', store=True)
    currency_id = fields.Many2one(related='package_id.currency_id', store=True)

    @api.onchange('product_id', 'quantity')
    def _onchange_product_or_qty(self):
        if self.product_id:
            product = self.product_id
            if not self.description:
                self.description = product.name
            if not self.uom_id:
                self.uom_id = product.uom_id.id
            if not self.ncm and product.ncm:
                self.ncm = product.ncm
            qty = self.quantity or 0.0
            if qty > 0:
                # Peso neto de la linea: cantidad x peso unitario del producto
                self.net_weight = (product.weight or 0.0) * qty
                if not self.volume and product.volume:
                    self.volume = product.volume * qty
