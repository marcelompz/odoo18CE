from odoo import fields, models

class ProductDescriptionWizard(models.TransientModel):
    _name = "product.description.wizard"
    _description = "Asistente de Descripción del Producto"

    product_id = fields.Many2one("product.template", string="Producto", required=True)
    description = fields.Text(string="Descripción", related="product_id.description_sale", readonly=True)


