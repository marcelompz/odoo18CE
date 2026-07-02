# -*- coding: utf-8 -*-
"""
Created on 2025-06-10 09:44:32

@author: drojo
"""
# python
import logging

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    stamped_id = fields.Many2one(
        'account.supplier.stamping', string='Timbrado', domain="[('partner_id', '=', partner_id)]",
        help='Timbrado vigente del proveedor')
    stamped_date_end = fields.Date(
        related='stamped_id.date_end', string='Vencimiento Timbrado')
    expired_stamped = fields.Boolean(string='Timbrado vencido', compute='_compute_expired_stamped')

    @api.depends('stamped_id', 'stamped_id.date_end', 'invoice_date')
    def _compute_expired_stamped(self):
        for record in self:
            if record.stamped_id and record.stamped_id.date_end:
                ref_date = record.invoice_date or fields.Date.today()
                record.expired_stamped = ref_date > record.stamped_id.date_end
            else:
                record.expired_stamped = False

    @api.onchange('invoice_number')
    def _onchange_invoice_number(self):
        if self.invoice_number:
            # Quitar espacios y normalizar el valor
            raw_number = self.invoice_number.replace(" ", "")
            parts = raw_number.split("-")

            if len(parts) != 3:  # Si no tiene 3 partes, asumimos que es un numero que no necesita ser formateado
                return
            # Asegurar que cada parte tenga el formato esperado
            try:
                part1 = parts[0].zfill(3) if len(parts) > 0 else "000"
                part2 = parts[1].zfill(3) if len(parts) > 1 else "000"
                part3 = parts[2].zfill(7) if len(parts) > 2 else "0000000"

                # Actualizar el campo con el formato estándar
                self.invoice_number = f"{part1}-{part2}-{part3}"
            except IndexError:
                self.invoice_number = ""  # Limpia si hay un error en el formato 

    @api.onchange('stamped_id', 'invoice_number')
    def onchange_stamped_id(self):
        text_concatenated = ''

        if self.invoice_number:
            text_concatenated += self.invoice_number

        if self.stamped_id:
            if text_concatenated:
                text_concatenated += ' | '
            text_concatenated += f'Timbrado: {self.stamped_id.name}'

        self.ref = text_concatenated
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Al cambiar el partner, cargar el último `account.supplier.stamping` disponible.

        Busca por `partner_id` ordenando por `id` descendente
        y asigna el primero encontrado a `stamped_id`.
        """
        if not self.partner_id:
            self.stamped_id = False
            return

        stamping = self.env['account.supplier.stamping'].search(
            [('partner_id', '=', self.partner_id.id)],
            order='id desc',
            limit=1,
        )

        if stamping:
            self.stamped_id = stamping
        else:
            self.stamped_id = False
