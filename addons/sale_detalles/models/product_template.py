from odoo import models, fields, api


def _build_utex_product_code(product):
    """
    Construye el código cuando hay datos de utex_stock_cross (product_initial_id).
    Formato: CÓD_CATEGORÍA/ID-PROD_INICIAL-MODELO-TELA-TALLA
    Ejemplo: MER-PER/4564-CAMP-CNCP-06
    """
    template = product.product_tmpl_id
    category = product.categ_id or template.categ_id

    # 1. Código categoría
    cat_code = ''
    if category and category.exists():
        cat_code = getattr(category, 'code', None) or ''
        if not cat_code and category.name:
            cat_code = category.name[:3].upper()
        if category.parent_id:
            parent_code = getattr(category.parent_id, 'code', None)
            if not parent_code and category.parent_id.name:
                parent_code = category.parent_id.name[:3].upper()
            if parent_code:
                cat_code = f"{parent_code}-{cat_code}" if cat_code else parent_code

    # 2. ID secuencia (sale_detalles.product.product)
    sequence_number = product.env['ir.sequence'].next_by_code('sale_detalles.product.product') or ''

    # 3-5. Producto inicial, modelo, tela (campos de utex_stock_cross)
    code_initial = (template.product_initial_id.code or '') if template.product_initial_id else ''
    code_model = (template.product_model_id.code or '') if template.product_model_id else ''
    code_fabric = ''
    fabrics = getattr(template, 'product_combination_fabrics_id', None)
    if fabrics:
        code_fabric = '-'.join(
            (f.code or (f.name[:3].upper() if f.name else ''))
            for f in fabrics
        ).strip('-')

    # 6. Talla (atributos de variante)
    size_value = ''
    if product.product_template_attribute_value_ids:
        size_values = [
            v.name for v in product.product_template_attribute_value_ids.sorted(key=lambda x: x.attribute_id.sequence)
        ]
        size_value = '-'.join(size_values) if size_values else ''

    after_slash = [p for p in [code_initial, code_model, code_fabric, size_value] if p]
    result = f"{cat_code}/{sequence_number}" if cat_code else sequence_number
    if after_slash:
        result += '-' + '-'.join(after_slash)
    return result


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    reference_code = fields.Char(string='Código de Referencia Base', help='Código base para generar la referencia interna de las variantes')
    show_in_import_reference = fields.Boolean(string='Mostrar en Importación de Referencias', default=False)
    hs_code = fields.Char(string='Código HS', help='Código del Sistema Armonizado para clasificación de productos')
    country_of_origin = fields.Many2one('res.country', string='País de Origen', help='País de origen del producto')

    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        if res.reference_code:
            res._update_variant_references()
        return res

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if 'reference_code' in vals:
            self._update_variant_references()
        return res

    def _update_variant_references(self):
        for template in self:
            for variant in template.product_variant_ids:
                # Formato utex (product_initial_id) tiene prioridad si existe
                if getattr(template, 'product_initial_id', None) and template.product_initial_id:
                    code = _build_utex_product_code(variant)
                    if code:
                        variant.default_code = code
                elif template.reference_code:
                    variant_name = "-".join(
                        v.name for v in variant.product_template_attribute_value_ids.sorted(key=lambda x: x.attribute_id.sequence)
                    )
                    variant.default_code = f"{template.reference_code}-{variant_name}" if variant_name else template.reference_code

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        res = super(ProductProduct, self).create(vals)
        template = res.product_tmpl_id
        if getattr(template, 'product_initial_id', None) and template.product_initial_id:
            code = _build_utex_product_code(res)
            if code:
                res.default_code = code
        elif template.reference_code:
            variant_name = "-".join(
                v.name for v in res.product_template_attribute_value_ids.sorted(key=lambda x: x.attribute_id.sequence)
            )
            res.default_code = f"{template.reference_code}-{variant_name}" if variant_name else template.reference_code
        return res

    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        if 'product_template_attribute_value_ids' in vals:
            for product in self:
                template = product.product_tmpl_id
                if getattr(template, 'product_initial_id', None) and template.product_initial_id:
                    code = _build_utex_product_code(product)
                    if code:
                        product.default_code = code
                elif template.reference_code:
                    variant_name = "-".join(
                        v.name for v in product.product_template_attribute_value_ids.sorted(key=lambda x: x.attribute_id.sequence)
                    )
                    product.default_code = f"{template.reference_code}-{variant_name}" if variant_name else template.reference_code
        return res 