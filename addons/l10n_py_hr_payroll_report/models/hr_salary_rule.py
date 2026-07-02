# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    def unlink(self):
        """Permitir archivar en lugar de eliminar si hay dependencias"""
        # Intentar eliminar normalmente, pero si falla por restricciones de BD, archivar
        try:
            return super(HrSalaryRule, self).unlink()
        except (ValidationError, UserError, Exception) as e:
            # Si hay un error relacionado con dependencias, archivar en lugar de eliminar
            error_msg = str(e)
            error_lower = error_msg.lower()
            
            # Verificar si el error está relacionado con dependencias o restricciones de BD
            # Palabras clave en español e inglés
            dependency_keywords = [
                'fkey', 'foreign key', 'constraint', 'violates foreign key',
                'otro modelo necesita', 'necesita el registro', 'restricción',
                'no se pudo completar', 'limitation', 'limitación',
                'hr_salary_rule_category_id_fkey', 'category_id_fkey'
            ]
            
            if any(keyword in error_lower for keyword in dependency_keywords):
                # Archivar las reglas en lugar de eliminarlas
                try:
                    self.write({'active': False})
                    _logger.info("Se archivaron %d reglas salariales en lugar de eliminarlas debido a dependencias: %s", len(self), error_msg)
                    return True
                except Exception as write_error:
                    # Si incluso archivar falla, loguear y propagar el error original
                    _logger.error("Error al archivar reglas salariales: %s", str(write_error))
                    raise e
            else:
                # Si es otro tipo de error, propagarlo
                raise

    @api.model
    def assign_accounts_paraguay(self):
        """Asignar cuentas contables paraguayas a las reglas salariales"""
        # Verificar si hr_payroll_account está instalado
        if not self.env['ir.module.module'].search([
            ('name', '=', 'hr_payroll_account'),
            ('state', '=', 'installed')
        ]):
            _logger.warning("hr_payroll_account no está instalado. Las cuentas no se asignarán.")
            return
        
        # Mapeo de reglas salariales (XMLID) a códigos de cuenta desde el XLSX
        # Deshabilitado temporalmente por requerimiento: cuentas de débito/crédito comentadas.
        account_mapping = {}
        
        # Buscar y asignar cuentas por compañía
        AccountAccount = self.env['account.account']
        default_company = self.env.company

        assigned_count = 0
        not_found = []

        for xmlid, accounts in account_mapping.items():
            rule = self.env.ref(xmlid, raise_if_not_found=False)
            if not rule:
                continue

            company = rule.company_id or default_company

            if accounts.get('debit'):
                debit_account = AccountAccount.search([
                    ('code', '=', accounts['debit']),
                    ('company_id', '=', company.id)
                ], limit=1)
                if debit_account:
                    rule.account_debit = debit_account.id
                    assigned_count += 1
                else:
                    not_found.append(f"{xmlid} - Debito: {accounts['debit']} (Compania: {company.name})")

            if accounts.get('credit'):
                credit_account = AccountAccount.search([
                    ('code', '=', accounts['credit']),
                    ('company_id', '=', company.id)
                ], limit=1)
                if credit_account:
                    rule.account_credit = credit_account.id
                    assigned_count += 1
                else:
                    not_found.append(f"{xmlid} - Credito: {accounts['credit']} (Compania: {company.name})")
        
        if not_found:
            _logger.warning("Las siguientes cuentas no se encontraron: %s", '\n'.join(not_found))
        
        _logger.info("Se asignaron %d cuentas contables a las reglas salariales paraguayas.", assigned_count)
        
        return {
            'assigned': assigned_count,
            'not_found': not_found
        }
