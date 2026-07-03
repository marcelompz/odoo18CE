# -*- coding: utf-8 -*-
"""
Created on 2025-01-18 02:05:51

@author: drojo
"""
# python 
import requests
import logging
import psycopg2
from psycopg2 import sql, OperationalError

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PosOrderInherit(models.Model):
    _inherit = 'pos.order'

    def _generate_pos_order_invoice(self):
        """
        Generates an electronic invoice for a POS order.

        This method creates an invoice for the current POS order, assigns it to the 
        order, and attempts to generate and send the electronic invoice.

        :return: Action dictionary to open the invoice view.
        :rtype: dict
        :raises UserError: If a customer is not assigned to the order.
        """
        moves = self.env['account.move']

        for order in self:
            if order.account_move:
                moves += order.account_move
                continue

            if not order.partner_id:
                raise UserError(_('Por favor proporcione un cliente para la venta.'))

            move_vals = order._prepare_invoice_vals()

            # Validacion de metodo de pago
            if not move_vals.get('invoice_payment_term_id'):
                cash_payment_term = self.env['account.payment.term'].search([('is_cash_payment', '=', True)], limit=1)
                if cash_payment_term:
                    move_vals['invoice_payment_term_id'] = cash_payment_term.id
            
            new_move = order._create_invoice(move_vals)

            order.write({'account_move': new_move.id})
            new_move.sudo().with_company(order.company_id).with_context(skip_invoice_sync=True)._post()

            try:
                if new_move.move_type == 'out_invoice':
                    if not new_move.authorization_id:
                        stamped = self.env['account.authorization'].search(
                            [('latam_doc_type_id.code', '=', 1)],
                            order='id desc', limit=1
                        )
                        new_move.write({'authorization_id': stamped.id if stamped else False})
                    
                    # Genera la FE
                    res = new_move.send_json_to_set()

                    if isinstance(res, dict):  
                        # Si dio error mostramos al usuario
                        title_value = res.get("params", {}).get("title", "")
                        raise ValidationError(title_value)

                    else:  
                        # Si se generó correctamente
                        _logger.info("Electronic invoice generated")

            except Exception as e:
                _logger.error("Error executing send_json_to_set for invoice %s: %s", new_move.id, str(e))
                raise ValidationError(str(e))

            moves += new_move
            order._apply_invoice_payments()

            if not new_move.pdf_show:
                res = new_move.get_pdf_to_print()

                if isinstance(res, dict):  
                    # Si dio error mostramos al usuario
                    title_value = res.get("params", {}).get("title", "")
                    _logger.info(f'ERROR: {title_value}')
                    raise ValidationError(title_value)

        if not moves:
            _logger.warning("No invoices were generated for the orders.")
            return {}

        return {
            'name': _('Customer Invoice'),
            'view_mode': 'form',
            'view_id': self.env.ref('account.view_move_form').id,
            'res_model': 'account.move',
            'context': "{'move_type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': moves.ids[0],
        }

    def search_customer_by_ruc(self, ruc):
        """
        Searches for a customer by their RUC from the POS.

        If the RUC does not exist, attempts to fetch customer data from an external API.

        :param ruc: RUC (tax ID) of the customer.
        :type ruc: str
        :return: Dictionary with customer data or an error message.
        :rtype: dict
        :raises UserError: If the RUC is invalid or already registered.
        """
        if not ruc:
            raise UserError(_('Debes ingresar el R.U.C. del cliente'))

        ruc = ruc.translate(str.maketrans('', '', '., /[]*(){}'))
        parts = ruc.split('-')
        ruc_dv = '#'

        if len(parts) == 1:
            ruc_dv = f"{ruc}-{self._get_verification_digit(ruc)}"
        elif len(parts) > 2:
            _logger.warning("Malformed RUC: %s", ruc)
            return {'error': _('Mal formato del número de documento.')}

        partners = self.env['res.partner'].search([
            '|', ('vat', '=', ruc), ('vat', '=', ruc_dv)
        ])

        if partners:
            partner_names = ', '.join(partners.mapped('name'))
            return {'error': _('Número de documento ya registrado con el cliente %s' % partner_names)}

        if ruc_dv != '#': ruc = ruc_dv

        params = self.env.company._get_postgre_configurator()

        try:
            # Establecer conexión con PostgreSQL
            with psycopg2.connect(
                dbname=params['postgre_dbname'], 
                user=params['postgre_user'], 
                password=params['postgre_password'], 
                host=params['postgre_host'], 
                port=params['postgre_port']
            ) as conn:
                with conn.cursor() as cur:
                    # Usar consulta parametrizada para evitar inyección SQL
                    query = sql.SQL("SELECT id, name, vat, status FROM public.res_partner WHERE vat = %s")
                    cur.execute(query, (ruc,))
                    columnas = [desc[0] for desc in cur.description]  # Obtener nombres de columnas
                    filas = cur.fetchall()


                    # Transformar filas en lista de diccionarios
                    resultados = [dict(zip(columnas, fila)) for fila in filas]
                    return resultados[0]

        # Retorno del error
        except OperationalError as e:
            return {'error': _('Problema de conexión a la base de datos %s' % e)}

        except psycopg2.Error as e:
            return {'error': _('Error al ejecutar la consulta SQL - %s' % e)}

        except Exception as e:
            return {'error': e}

    def _get_verification_digit(self, ruc):
        """
        Calculates the verification digit for a given RUC.

        :param ruc: RUC to verify.
        :type ruc: str
        :return: Verification digit.
        :rtype: int
        """
        total = sum(int(digit) * (base if (base := 2 + i % 9) else 2) for i, digit in enumerate(reversed(ruc)))
        return 0 if total % 11 in (0, 1) else 11 - total % 11
