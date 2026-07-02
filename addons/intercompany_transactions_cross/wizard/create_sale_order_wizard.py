# intercompany_transactions_cross/wizard/create_sale_order_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CreateSaleOrderWizard(models.TransientModel):
    _name = 'create.sale.order.wizard'
    _description = 'Wizard to create SO from PO'

    company_id = fields.Many2one('res.company', string='Compañía', compute='_compute_company_id', store=True)
    purchase_id = fields.Many2one('purchase.order', string='Orden de Compra', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Moneda Compra', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, 
                                domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('customer_rank', '>', 0)]")
    calculation_method = fields.Selection([
        ('global', 'Margen Global (%)'),
        ('manual', 'Manual (Línea por línea)')
    ], string='Método de Cálculo', default='global', required=True)
    
    global_margin = fields.Float(string='Margen Global (%)', default=0.0)
    line_ids = fields.One2many('create.sale.order.wizard.line', 'wizard_id', string='Productos')

    @api.depends('purchase_id')
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.purchase_id.company_id or self.env.company

    @api.onchange('global_margin', 'calculation_method', 'partner_id')
    def _onchange_prices(self):
        if self.calculation_method == 'global' and self.partner_id:
            # Get target currency from partner's pricelist
            target_currency = self.partner_id.property_product_pricelist.currency_id
            source_currency = self.currency_id or self.purchase_id.currency_id
            
            for line in self.line_ids:
                price = line.purchase_price * (1 + self.global_margin / 100.0)
                if source_currency and target_currency and source_currency != target_currency:
                    price = source_currency._convert(price, target_currency, self.company_id, fields.Date.today())
                line.sale_price = price

    def action_create_sale_order(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("No hay líneas para crear la venta."))

        company = self.purchase_id.company_id or self.env.company
        
        # Create SO with company context
        sale_order = self.env['sale.order'].with_company(company).create({
            'partner_id': self.partner_id.id,
            'origin': self.purchase_id.name,
            'company_id': company.id,
        })

        for line in self.line_ids:
            # Use price from line directly if manual, or recalculated if global (though onchange should handle it)
            sale_price = line.sale_price
            
            # Handle cost (purchase_price) conversion if currencies differ
            source_currency = self.currency_id or self.purchase_id.currency_id
            target_currency = sale_order.currency_id
            purchase_price = line.purchase_price
            if source_currency and target_currency and source_currency != target_currency:
                purchase_price = source_currency._convert(purchase_price, target_currency, self.company_id, fields.Date.today())

            # Use new() to get taxes and other defaults, then create
            sol_model = self.env['sale.order.line'].with_company(company)
            line_vals = {
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'price_unit': sale_price,
                'purchase_price': purchase_price,
            }
            
            # This triggers all default values including taxes
            new_line = sol_model.new(line_vals)
            new_line._onchange_product_id_warning()
            
            # Convert the fake record back to values for creation
            final_vals = new_line._convert_to_write(new_line._cache)
            
            # Ensure our specific overrides are applied
            final_vals.update({
                'price_unit': sale_price,
                'purchase_price': purchase_price,
                'product_uom_qty': line.quantity,
                'product_uom': line.uom_id.id,
                'name': line.name or new_line.name,
            })
            
            sol_model.create(final_vals)

        return {
            'name': sale_order.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'target': 'current',
        }

class CreateSaleOrderWizardLine(models.TransientModel):
    _name = 'create.sale.order.wizard.line'
    _description = 'Wizard Line'

    wizard_id = fields.Many2one('create.sale.order.wizard')
    product_id = fields.Many2one('product.product', string='Producto')
    name = fields.Text(string='Descripción')
    quantity = fields.Float(string='Cantidad')
    uom_id = fields.Many2one('uom.uom', string='UdM')
    purchase_price = fields.Float(string='Costo (Compra)')
    sale_price = fields.Float(string='Precio de Venta')
