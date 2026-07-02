# -*- coding: utf-8 -*-
"""Tile configurable que se muestra en el portal Talento Humano."""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TalentPortalTile(models.Model):
    _name = 'talent.portal.tile'
    _description = 'Tile del Portal Talento Humano'
    _order = 'category_id, sequence, id'

    name = fields.Char(string='Nombre', required=True, translate=True)
    description = fields.Char(string='Descripcion corta', translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    category_id = fields.Many2one(
        'talent.portal.category', string='Categoria',
        ondelete='set null', index=True,
    )

    icon_class = fields.Char(
        string='Icono Font Awesome', default='fa-cubes',
    )
    color = fields.Selection([
        ('1', 'Rojo'), ('2', 'Naranja'), ('3', 'Amarillo'),
        ('4', 'Verde claro'), ('5', 'Verde'), ('6', 'Cian'),
        ('7', 'Azul claro'), ('8', 'Azul'), ('9', 'Violeta'),
        ('10', 'Magenta'), ('11', 'Rosa'),
    ], default='8', string='Color')

    action_id = fields.Many2one('ir.actions.actions', string='Accion destino')
    action_xml_id = fields.Char(string='ID externo de la accion')
    method_call = fields.Char(string='Metodo Python')
    groups_ids = fields.Many2many('res.groups', string='Visible solo para')
    notes = fields.Text(string='Notas internas')

    show_count = fields.Boolean(string='Mostrar contador')
    count_model = fields.Char(string='Modelo a contar')
    count_domain = fields.Char(string='Dominio a contar')

    def action_open_target(self):
        self.ensure_one()
        if self.method_call:
            try:
                model_name, method = self.method_call.split(':')
            except ValueError:
                raise UserError(_('Metodo Python con formato invalido. Use modelo:metodo.'))
            Model = self.env.get(model_name)
            if Model is None:
                raise UserError(_('Modelo "%s" no existe.') % model_name)
            if not hasattr(Model, method):
                raise UserError(_('El metodo "%s" no existe en el modelo "%s".') % (method, model_name))
            return getattr(Model, method)()

        action = None
        if self.action_id:
            action = self.action_id
        elif self.action_xml_id:
            try:
                action = self.env.ref(self.action_xml_id, raise_if_not_found=True)
            except Exception:
                raise UserError(_(
                    'No se encontro la accion con XML ID "%s". '
                    'Verifique que el modulo destino este instalado.'
                ) % self.action_xml_id)
        if not action:
            raise UserError(_('Este tile no tiene una accion destino configurada.'))
        return action.read()[0] if hasattr(action, 'read') else action
