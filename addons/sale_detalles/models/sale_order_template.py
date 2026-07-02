from odoo import models, fields, api

class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    code = fields.Char(string='Código', help='Código de la plantilla de cotización')

    def name_get(self):
        """Mostrar nombre (código) en lugar de solo nombre"""
        result = []
        for record in self:
            name = record.name or ''
            if record.code:
                name = f"{name} ({record.code})"
            result.append((record.id, name))
        return result

