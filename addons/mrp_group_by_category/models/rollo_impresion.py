from odoo import models, fields, api, _

class RolloImpresion(models.Model):
    _name = 'rollo.impresion'
    _description = 'Rollo de Impresión'
    _order = 'id desc'

    name = fields.Char('Código', required=True, copy=False, default=lambda self: _('Nuevo'))
    line_ids = fields.One2many('rollo.impresion.line', 'rollo_id', string='Líneas')
    cantidad_total = fields.Float('Cantidad Total', compute='_compute_cantidad_total', store=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Nuevo')) == _('Nuevo'):
            vals['name'] = self.env['ir.sequence'].next_by_code('rollo.impresion') or _('Nuevo')
        return super().create(vals)

    @api.depends('line_ids.cantidad')
    def _compute_cantidad_total(self):
        for rec in self:
            rec.cantidad_total = sum(line.cantidad for line in rec.line_ids)

class RolloImpresionLine(models.Model):
    _name = 'rollo.impresion.line'
    _description = 'Línea de Rollo de Impresión'
    _order = 'id desc'

    rollo_id = fields.Many2one('rollo.impresion', string='Rollo', ondelete='cascade', required=True)
    production_id = fields.Many2one(
        'mrp.production',
        string='Orden de Fabricación',
        domain="[('origin', '!=', False)]",
        required=True
    )
    descripcion = fields.Char('Descripción')
    cantidad = fields.Float('Cantidad', required=True) 