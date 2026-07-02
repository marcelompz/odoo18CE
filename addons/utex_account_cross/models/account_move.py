# -*- coding: utf-8 -*-
"""
Created on 2026-02-16 17:35:24

@author: drojo
"""
# python
import logging
import re

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

from odoo.addons.electronic_invoice_cross.models import jsongenerator
from odoo.addons.electronic_invoice_cross.models import account_move as cross_account_move

original_create_json_data = jsongenerator.create_json_data

def custom_create_json_data(doc, origin='invoice'):
    data = original_create_json_data(doc, origin)
    
    if origin == 'invoice':
        should_group = False
        # Avoid breaking if fields don't exist
        if hasattr(doc.company_id, 'cross_group_products_normal_invoice'):
            if doc.is_an_export_invoice and doc.company_id.cross_group_products_export_invoice:
                should_group = True
            elif not doc.is_an_export_invoice and doc.company_id.cross_group_products_normal_invoice:
                should_group = True
        
        if should_group:
            # 6 is DIPLOMATIC_DOC_ID in account_move
            is_diplomatic = doc.partner_id.l10n_latam_identification_type_id.document_id == 6
            for lote in data:
                grouped_items = {}
                invoice_line = []
                last_key = None
                
                for line in doc.invoice_line_ids:
                    if line.display_type == 'line_note':
                        if last_key and last_key in grouped_items:
                            obs = grouped_items[last_key]['observacion']
                            grouped_items[last_key]['observacion'] = obs + " " + line.name if obs else line.name
                    else:
                        prod_name = line.product_id.product_tmpl_id.name
                        if is_diplomatic:
                            prod_name = f'{prod_name} - Ley 110/92'
                        
                        item = {
                            "codigo": line.product_id.product_tmpl_id.barcode or line.product_id.product_tmpl_id.default_code or "",
                            "descripcion": prod_name,
                            "observacion": "",
                            "ncm": line.product_id.ncm if line.product_id.ncm else "",
                            "unidadMedida": int(line.product_uom_id.code),
                            "cantidad": line.quantity,
                            "precioUnitario": line.price_unit,
                            "cambio": 0.0,
                            "descuento": round((line.discount/100) * line.price_unit, 8),
                            "ivaTipo": 1 if line.tax_ids else 3,
                            "ivaBase": 100 if line.tax_ids else 0,
                            "iva": int(sum(tax.amount for tax in line.tax_ids)) if line.tax_ids else 0,
                            "lote": "",
                            "vencimiento": "",
                            "numeroSerie": "",
                            "numeroPedido": "",
                            "numeroSeguimiento": "",
                        }
                        
                        key = (line.product_id.product_tmpl_id.id, line.price_unit, line.discount, tuple(line.tax_ids.ids), line.product_uom_id.id)
                        if key in grouped_items:
                            grouped_items[key]['cantidad'] += line.quantity
                        else:
                            grouped_items[key] = item
                        last_key = key
                        
                invoice_line.extend(grouped_items.values())
                lote['items'] = invoice_line
                
    return data

# Aplicar el monkey patch
jsongenerator.create_json_data = custom_create_json_data
cross_account_move.create_json_data = custom_create_json_data

class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    def get_pdf_to_print(self):
        # 1. Ejecutamos la lógica original (Descarga el PDF y lo guarda como [Numero].pdf)
        super().get_pdf_to_print()

        # 2. Preparamos las variables para el nuevo nombre
        invoice_num = self.invoice_number or self.name or 'SIN_NUMERO'
        partner_name = self.partner_id.name or 'Consumidor_Final'
        partner_name_safe = re.sub(r'[^a-zA-Z0-9]', '_', partner_name)
        
        # Formateamos la fecha (DD_MM_AAAA), o usamos un valor por defecto si no hay fecha
        date_str = self.invoice_date.strftime('%d_%m_%Y') if self.invoice_date else '00_00_0000'

        # Construimos el nombre final: [Nro]_[Cliente]_[Fecha].pdf
        new_filename = f"{invoice_num}_{partner_name_safe}_{date_str}.pdf"

        # 3. Buscamos el adjunto que acaba de crear el método original
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
        ], order='create_date desc', limit=1)

        # 4. Actualizamos el nombre
        if attachment:
            attachment.write({
                'name': new_filename,
                'description': new_filename,
            })

    def send_json_to_set_again(self):
        # Inyectamos una variable de contexto para indicar que es una regeneración (reenvío)
        return super(AccountMoveInherit, self.with_context(is_regenerating_ed=True)).send_json_to_set_again()

    def send_json_to_set(self):
        for record in self:
            # Si estamos regenerando la factura desde send_json_to_set_again, evitamos validar la fecha
            if self.env.context.get('is_regenerating_ed'):
                continue

            # 1. Validación de existencia de fecha
            if not record.invoice_date:
                raise UserError(_("La factura %s no tiene una fecha asignada.") % record.name)

            # 2. Obtener la fecha de hoy según la zona horaria del usuario
            today = fields.Date.context_today(record)

            # 3. Lógica corregida: 
            if record.invoice_date != today and not record.is_ed:
                raise UserError(_(
                    "Operación no permitida: La fecha de la factura (%s) debe coincidir con la fecha de hoy (%s) "
                    "para el primer envío del documento electrónico."
                ) % (record.invoice_date, today))

        # 4. Llamamos al super solo si todas las validaciones pasaron
        return super().send_json_to_set()

    def unlink(self):
        has_delete_group = self.env.user.has_group('utex_account_cross.group_allow_delete_invoice_any_state')
        for record in self:
            if record.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund') and not has_delete_group:
                raise UserError(_("No tiene los permisos necesarios para eliminar facturas (incluso en estado borrador)."))

        if has_delete_group:
            self = self.with_context(force_delete=True)
            for record in self:
                if record.state != 'draft':
                    try:
                        record.button_draft()
                    except Exception:
                        pass
                    record.write({'state': 'draft'})
        return super().unlink()
