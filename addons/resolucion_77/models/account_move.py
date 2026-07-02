# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Relación con Resolución 77
    resolucion_77_line_id = fields.Many2one(
        'resolucion.77.line',
        string='Línea Resolución 77',
        help='Línea del cuadro de depreciación que generó este asiento'
    )
    
    # Campos adicionales para identificación
    is_depreciation_move = fields.Boolean(string="Es Asiento de Depreciación",
                                         compute='_compute_is_depreciation_move',
                                         store=True)
    
    def _compute_is_depreciation_move(self):
        """Determina si el asiento es de depreciación"""
        for record in self:
            record.is_depreciation_move = bool(record.resolucion_77_line_id)

    def action_view_resolucion_77_line(self):
        """Acción para ver la línea de resolución 77 asociada"""
        self.ensure_one()
        if self.resolucion_77_line_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Línea Resolución 77',
                'res_model': 'resolucion.77.line',
                'res_id': self.resolucion_77_line_id.id,
                'view_mode': 'form',
                'target': 'current',
            } 