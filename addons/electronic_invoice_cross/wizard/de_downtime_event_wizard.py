# -*- coding: utf-8 -*-
"""
Created on 2025-02-21 23:43:04

@author: drojo
"""
# python
import requests  # api
import json  # json format

# odoo
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class DeDowntimeEventWizard(models.TransientModel):
    _name = 'de.downtime.event.wizard'
    _description = 'Registro de evento de inutilización'

    authorization_id = fields.Many2one(
        'account.authorization', string='Timbrado')
    latam_doc_type_id = fields.Many2one(
        related='authorization_id.latam_doc_type_id')
    establishment_code = fields.Char(
        related='authorization_id.establishment_code')
    generation_point = fields.Char(
        related='authorization_id.generation_point')
    number_from = fields.Integer(
        string='Número desde')
    number_to = fields.Integer(
        string='Número hasta')
    reason = fields.Text(
        string='Motivo')

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        
        context = self.env.context
        copy_data = {
            'authorization_id': context.get('active_id'),
        }
        res.update(copy_data)
    
        return res

    def action_acept(self):
        if self.number_from <= 0 or self.number_to <= 0 or self.number_from > self.number_to:
            raise UserError(_('Por favor verifique los números desde/hasta'))

        if not (5 <= len(self.reason) <= 500):
            raise ValidationError(_('El motivo del evento debe tener un mínimo de 5 letras y un máximo de 500.'))

        params = self._get_connection_configurator()

        if not params["url_api"] or not params["api_key"]:
            raise ValidationError(_('La configuración de la API está incompleta. Verifique la configuración.'))

        url = params["url_api"] + "/evento/inutilizacion"
        headers = {
            "Authorization": f'Bearer api_key_{params["api_key"]}',
            "Content-Type": "application/json; charset=utf-8",
        }
        data = {
            "tipoDocumento": int(self.latam_doc_type_id.code),
            "establecimiento": self.establishment_code,
            "punto": self.generation_point,
            "desde": self.number_from,
            "hasta": self.number_to,
            "motivo": self.reason,
        }

        try:
            result = requests.post(url=url, verify=False, headers=headers, data=json.dumps(data))
            result.raise_for_status()
            res_json = result.json()

            if res_json.get('success'):
                json_state = res_json["result"]['ns2:rRetEnviEventoDe']['ns2:gResProcEVe']['ns2:dEstRes']
                json_msg = res_json["result"]['ns2:rRetEnviEventoDe']['ns2:gResProcEVe']['ns2:gResProc']['ns2:dMsgRes']

                self.env['account.authorization.downtime.history'].create({
                    'authorization_id': self.authorization_id.id,
                    'latam_doc_type_id': self.latam_doc_type_id.id,
                    'establishment_code': self.establishment_code,
                    'generation_point': self.generation_point,
                    'number_from': self.number_from,
                    'number_to': self.number_to,
                    'reason': self.reason,
                    'json_sent': data,
                    'state': 'approved' if json_state == 'Aprobado' else 'refused',
                    'json_result': res_json["result"],
                    'json_message': json_msg,
                })

                if json_state == 'Aprobado':
                    self.authorization_id.message_post(body=_("Se registro un evento de inutilización: Numeración desde %s al %s" % (self.number_from, self.number_to)))
                    return self.env.user.cross_user_notify(message='¡Evento de inutilización exitoso!', reload=True)

                else:
                    return self.env.user.cross_user_notify(state='warning', message='¡Error en el Evento de inutilización!', reload=False)

            else:
                raise UserError(_('No se pudo procesar el evento. Verifique la respuesta de la API.'))

        except requests.exceptions.RequestException as e:
            self.env['account.authorization.downtime.history'].create({
                'authorization_id': self.authorization_id.id,
                'latam_doc_type_id': self.latam_doc_type_id.id,
                'establishment_code': self.establishment_code,
                'generation_point': self.generation_point,
                'number_from': self.number_from,
                'number_to': self.number_to,
                'reason': self.reason,
                'json_sent': data,
                'state': 'refused',
                'json_result': str(e),
            })
            
            return self.env.user.cross_user_notify(state='warning', message=str(e), reload=False, sticky=True)

    def _get_connection_configurator(self):
        url_api = self.env.company.url_api_cross
        api_key = self.env.company.api_key_cross
        sync_communication = self.env.company.sync_communication_cross

        return {
            "url_api": url_api,
            "api_key": api_key,
            "sync_communication": sync_communication,
        }
