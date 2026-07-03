# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:43:40

@author: drojo
"""
# python
import requests  # api
import json  # json format

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResCancelDocumentWizard(models.TransientModel):
    _name = 'res.cancel.document.wizard'
    _description = 'Cancelación de documentos electrónicos'

    name = fields.Char(
        string='CDC', help='El CDC del Documento Electrónico que desea cancelar')
    reason = fields.Char(
        string='Motivo de la cancelación', help='El motivo por el cual desea cancelar el documento')
    confirm_cancellation = fields.Boolean(
        string='Confirme la cancelación del documento electrónico')
    origin = fields.Char(
        string='Origen')
    stock_id = fields.Many2one(
        'stock.picking', string='Inventario')
    account_id = fields.Many2one(
        'account.move', string='Facturas')
    company_id = fields.Many2one(
        'res.company', string='Empresa', default=lambda self:self.env.company)

    @api.model
    def default_get(self, default_fields):
        res = super(). default_get(default_fields)
    
        context = self._context
        copy_data = {
            'name':context.get('name'),
            'origin': context.get('origin'),
            'stock_id': context.get('stock_id'),
            'account_id': context.get('account_id'),
        }
        res.update(copy_data)
    
        return res

    def action_cancel_document(self):
        params = self._get_cross_configurator()
        
        url = params["url_api"] + "/evento/cancelacion"
        headers = {
            "Authorization": f'Bearer api_key_{params["api_key"]}',
            "Content-Type": "application/json; charset=utf-8",
        }
        data = {"cdc": self.name, "motivo": self.reason}
        result = requests.post(url=url, verify=False, headers=headers, data=json.dumps(data))
        res_json = result.json()
        origin = self.stock_id if self.origin == 'stock' else self.account_id

        if result.status_code == 200:
            if res_json['success'] == True:
                for delist in res_json["result"]["ns2:rRetEnviEventoDe"]:
                    origin.l10n_py_ids = [(0,0,{
                        "name": "Evento cancelado",
                        "ed_status": "approved",
                        "json_result": res_json
                    },)]
                origin.is_ed_cancelled = True
                origin.get_de_status()
                origin.message_post(body=_("Factura electrónica cancelada"))
                return self.env.user.cross_user_notify(message='Documento electrónico cancelado exitosamente!', reload=True)

            else:
                origin.l10n_py_ids = [(0,0,{
                    "ed_status": "refused",
                    "ed_error_code": "ERROR",
                    "json_result": res_json
                },)]

                if res_json['errores']:
                    for error_line in res_json['errores']:
                        return self.env.user.cross_user_notify(state='warning', message=error_line['error'], reload=False, sticky=True)

                else:
                    return self.env.user.cross_user_notify(state='warning', message='Error no descripto.', reload=False, sticky=True)

        else:
            origin.l10n_py_ids = [(0,0,{
                "ed_status": "refused",
                "json_result": res_json
            },)]
            return self.env.user.cross_user_notify(state='warning', message=result.status_code, reload=False, sticky=True)

    def _get_cross_configurator(self):
        url_api = self.company_id.url_api_cross
        api_key = self.company_id.api_key_cross
        sync_communication = self.company_id.sync_communication_cross

        return {
            "url_api": url_api,
            "api_key": api_key,
            "sync_communication": sync_communication,
        }
