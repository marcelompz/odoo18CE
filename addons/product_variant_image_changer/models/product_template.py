from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    variant_image_ids = fields.One2many(
        'product.variant.image',
        'product_tmpl_id',
        string='Imágenes de Variantes'
    )


class ProductVariantImage(models.Model):
    _name = 'product.variant.image'
    _description = 'Imágenes de Variantes de Producto'
    _order = 'sequence, id'

    name = fields.Char(string='Nombre', required=True)
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Plantilla de Producto',
        ondelete='cascade',
        required=True
    )
    product_variant_id = fields.Many2one(
        'product.product',
        string='Variante de Producto',
        ondelete='cascade',
        required=True
    )
    image = fields.Binary(
        string='Imagen',
        required=True
    )
    image_url = fields.Char(
        string='URL de Imagen',
        compute='_compute_image_url'
    )
    sequence = fields.Integer(
        string='Secuencia',
        default=10
    )
    active = fields.Boolean(
        string='Activo',
        default=True
    )

    @api.depends(
        'image'
    )
    def _compute_image_url(self):
        for record in self:
            if record.id:
                record.image_url = f'/web/image/product.variant.image/{record.id}/image'
            else:
                record.image_url = False

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            product_variant = self.env['product.product'].browse(vals.get('product_variant_id'))
            if product_variant:
                vals['name'] = f"Imagen - {product_variant.display_name}"
        return super().create(vals)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    variant_image_ids = fields.One2many(
        'product.variant.image',
        'product_variant_id',
        string='Imágenes de Variante'
    )

    def get_variant_info(self):
        """Método para obtener información de la variante para AJAX"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.display_name,
            'price': self.list_price,
            'currency_symbol': self.currency_id.symbol,
            'image_url': f'/web/image/product.product/{self.id}/image_1920',
            'variant_images': [
                {
                    'id': img.id,
                    'url': img.image_url,
                    'name': img.name
                } for img in self.variant_image_ids
            ]
        }

