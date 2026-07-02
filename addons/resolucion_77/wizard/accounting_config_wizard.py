# -*- coding: utf-8 -*-

from odoo import api, fields, models, exceptions, _


class AccountingConfigWizard(models.TransientModel):
    _name = 'resolucion.77.accounting.config.wizard'
    _description = 'Wizard de Configuración Contable Resolución 77'

    name = fields.Char(string="Nombre de Configuración", default="Configuración Contable")
    
    # Cuentas contables por defecto
    account_asset_id = fields.Many2one('account.account', string="Cuenta de Activo Fijo",
                                       domain=[('account_type', '=', 'asset_fixed')],
                                       required=True,
                                       help="Cuenta contable para registrar activos fijos")
    
    account_depreciation_id = fields.Many2one('account.account', string="Cuenta de Depreciación Acumulada",
                                             domain=[('account_type', '=', 'asset_fixed')],
                                             required=True,
                                             help="Cuenta para depreciación acumulada")
    
    account_depreciation_expense_id = fields.Many2one('account.account', string="Cuenta de Gastos de Depreciación",
                                                     domain=[('account_type', 'in', ['expense_depreciation', 'expense'])],
                                                     required=True,
                                                     help="Cuenta para gastos de depreciación")
    
    journal_id = fields.Many2one('account.journal', string="Diario de Depreciación",
                                 domain=[('type', '=', 'general')],
                                 required=True,
                                 help="Diario para registrar asientos de depreciación")
    
    company_id = fields.Many2one('res.company', string='Compañía', 
                                default=lambda self: self.env.company, required=True)
    
    # Opciones de aplicación
    apply_to_existing = fields.Boolean(string="Aplicar a Registros Existentes", default=False,
                                      help="Aplicar esta configuración a todos los registros existentes")
    
    create_assets = fields.Boolean(string="Crear Activos Fijos Automáticamente", default=False,
                                  help="Crear activos fijos para registros que no los tengan")
    
    generate_moves = fields.Boolean(string="Generar Asientos de Depreciación", default=False,
                                   help="Generar asientos contables de depreciación")

    @api.model
    def default_get(self, fields_list):
        """Obtiene valores por defecto"""
        res = super().default_get(fields_list)
        
        # Buscar configuración existente
        config = self.env['resolucion.77.config'].get_default_config()
        
        # Buscar cuentas por defecto según plan contable
        company = self.env.company
        
        # Cuenta de activo fijo (buscar por código común)
        asset_account = self.env['account.account'].search([
            ('code', 'like', '15%'),  # Código típico de activos fijos
            ('account_type', '=', 'asset_fixed')
        ], limit=1)
        
        # Cuenta de depreciación acumulada
        depreciation_account = self.env['account.account'].search([
            ('code', 'like', '15%'),  # Mismo grupo que activos
            ('account_type', '=', 'asset_fixed'),
            ('name', 'ilike', 'depreciación')
        ], limit=1)
        
        # Cuenta de gastos de depreciación
        expense_account = self.env['account.account'].search([
            ('code', 'like', '6%'),  # Código típico de gastos
            ('account_type', '=', 'expenses'),
            ('name', 'ilike', 'depreciación')
        ], limit=1)
        
        # Diario general
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', company.id)
        ], limit=1)
        
        res.update({
            'account_asset_id': asset_account.id if asset_account else False,
            'account_depreciation_id': depreciation_account.id if depreciation_account else False,
            'account_depreciation_expense_id': expense_account.id if expense_account else False,
            'journal_id': journal.id if journal else False,
        })
        
        return res

    def action_apply_configuration(self):
        """Aplica la configuración contable"""
        self.ensure_one()
        
        if not self.account_asset_id or not self.account_depreciation_id or not self.account_depreciation_expense_id:
            raise exceptions.UserError(_('Debe configurar todas las cuentas contables'))
        
        if not self.journal_id:
            raise exceptions.UserError(_('Debe configurar el diario de depreciación'))
        
        # Buscar registros de Resolución 77
        domain = [('company_id', '=', self.company_id.id)]
        
        if not self.apply_to_existing:
            # Solo registros sin configuración contable
            domain += [
                '|', '|', '|',
                ('account_asset_id', '=', False),
                ('account_depreciation_id', '=', False),
                ('account_depreciation_expense_id', '=', False),
                ('journal_id', '=', False)
            ]
        
        lines = self.env['resolucion.77.line'].search(domain)
        
        if not lines:
            raise exceptions.UserError(_('No hay registros para actualizar'))
        
        # Actualizar configuración contable
        update_vals = {
            'account_asset_id': self.account_asset_id.id,
            'account_depreciation_id': self.account_depreciation_id.id,
            'account_depreciation_expense_id': self.account_depreciation_expense_id.id,
            'journal_id': self.journal_id.id,
        }
        
        lines.write(update_vals)
        
        # Crear activos fijos si se solicita
        if self.create_assets:
            created_assets = 0
            for line in lines:
                if not line.asset_created:
                    try:
                        line.action_create_asset()
                        created_assets += 1
                    except Exception as e:
                        # Continuar con otros registros si hay error
                        continue
        
        # Generar asientos si se solicita
        if self.generate_moves:
            created_moves = 0
            for line in lines:
                if line.asset_created and line.move_count == 0:
                    try:
                        line.action_generate_depreciation_move()
                        created_moves += 1
                    except Exception as e:
                        # Continuar con otros registros si hay error
                        continue
        
        # Mensaje de confirmación
        message = _('Configuración aplicada exitosamente:\n')
        message += _('- Registros actualizados: %d\n') % len(lines)
        
        if self.create_assets:
            message += _('- Activos fijos creados: %d\n') % created_assets
        
        if self.generate_moves:
            message += _('- Asientos generados: %d') % created_moves
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Configuración Aplicada'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_test_configuration(self):
        """Prueba la configuración contable"""
        self.ensure_one()
        
        if not self.account_asset_id or not self.account_depreciation_id or not self.account_depreciation_expense_id:
            raise exceptions.UserError(_('Debe configurar todas las cuentas contables'))
        
        if not self.journal_id:
            raise exceptions.UserError(_('Debe configurar el diario de depreciación'))
        
        # Verificar que las cuentas estén activas (no deprecadas en Odoo)
        if self.account_asset_id.deprecated:
            raise exceptions.UserError(_('La cuenta de activo fijo está deprecada'))
        
        if self.account_depreciation_id.deprecated:
            raise exceptions.UserError(_('La cuenta de depreciación acumulada está deprecada'))
        
        if self.account_depreciation_expense_id.deprecated:
            raise exceptions.UserError(_('La cuenta de gastos de depreciación está deprecada'))
        
        if not self.journal_id.active:
            raise exceptions.UserError(_('El diario no está activo'))
        
        # Verificar que el diario pertenezca a la compañía correcta  
        # Nota: En Odoo 18, account.account ya no tiene company_id directo
        if self.journal_id.company_id != self.company_id:
            raise exceptions.UserError(_('El diario debe pertenecer a la compañía seleccionada'))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Configuración Válida'),
                'message': _('La configuración contable es válida y puede ser aplicada.'),
                'type': 'success',
                'sticky': False,
            }
        } 
