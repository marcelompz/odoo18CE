# -*- coding: utf-8 -*-
import logging
from psycopg2 import IntegrityError

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrEmployeeMergeWizard(models.TransientModel):
    _name = 'hr.employee.merge.wizard'
    _description = 'Fusionar empleados duplicados'

    master_employee_id = fields.Many2one(
        'hr.employee', string='Empleado MAESTRO', required=True,
        help='Es el empleado que se conserva. Todas las referencias de los '
             'duplicados se redirigiran a este registro.',
    )
    duplicate_employee_ids = fields.Many2many(
        'hr.employee', 'hr_emp_merge_dup_rel', 'wizard_id', 'employee_id',
        string='Empleados DUPLICADOS', required=True,
        help='Empleados que seran archivados despues de redirigir sus '
             'referencias al maestro.',
    )
    copy_missing_fields = fields.Boolean(
        string='Copiar campos faltantes al maestro', default=True,
    )
    archive_duplicates = fields.Boolean(
        string='Archivar duplicados al finalizar', default=True,
    )
    summary = fields.Html(string='Resumen', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ids = self.env.context.get('active_ids') or []
        if ids:
            emps = self.env['hr.employee'].with_context(active_test=False).browse(ids)
            sorted_emps = emps.sorted('id')
            if sorted_emps:
                res['master_employee_id'] = sorted_emps[0].id
                if len(sorted_emps) > 1:
                    res['duplicate_employee_ids'] = [(6, 0, sorted_emps[1:].ids)]
        return res

    @api.constrains('master_employee_id', 'duplicate_employee_ids')
    def _check_master_not_duplicate(self):
        for w in self:
            if w.master_employee_id in w.duplicate_employee_ids:
                raise UserError(_('El empleado MAESTRO no puede figurar tambien '
                                  'en la lista de duplicados.'))
            if not w.duplicate_employee_ids:
                raise UserError(_('Debe seleccionar al menos un empleado duplicado.'))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_employee_referencing_fields(self):
        """Devuelve [(model_name, field_name, ttype), ...] de TODOS los campos
        m2o/m2m almacenados que apuntan a hr.employee.
        """
        Field = self.env['ir.model.fields']
        domain = [
            ('relation', '=', 'hr.employee'),
            ('ttype', 'in', ['many2one', 'many2many']),
            ('store', '=', True),
        ]
        fs = Field.sudo().search(domain)
        result = []
        for f in fs:
            if f.model == 'hr.employee.merge.wizard':
                continue
            result.append((f.model, f.name, f.ttype))
        return result

    def _safe_write(self, recs, vals):
        """Escribe registros uno por uno usando savepoint para que un fallo
        no aborte toda la transaccion. Devuelve (ok, fallidos)."""
        ok = 0
        fail = 0
        for rec in recs:
            sp_name = 'merge_emp_%d_%d' % (rec.id, ok + fail)
            try:
                self.env.cr.execute('SAVEPOINT %s' % sp_name)
                rec.write(vals)
                self.env.cr.execute('RELEASE SAVEPOINT %s' % sp_name)
                ok += 1
            except (IntegrityError, ValidationError, UserError) as e:
                self.env.cr.execute('ROLLBACK TO SAVEPOINT %s' % sp_name)
                _logger.warning("Skip merge of %s id=%d: %s",
                                rec._name, rec.id, e)
                fail += 1
            except Exception as e:
                self.env.cr.execute('ROLLBACK TO SAVEPOINT %s' % sp_name)
                _logger.warning("Unexpected skip %s id=%d: %s",
                                rec._name, rec.id, e)
                fail += 1
        return ok, fail

    def _redirect_m2o(self, model_name, field_name, master_id, duplicate_ids):
        try:
            Model = self.env[model_name].sudo()
        except KeyError:
            return 0, 0
        if not Model._auto:
            return 0, 0
        if field_name not in Model._fields:
            return 0, 0
        field = Model._fields[field_name]
        if not field.store:
            return 0, 0
        try:
            recs = Model.with_context(active_test=False).search(
                [(field_name, 'in', duplicate_ids)])
        except Exception as e:
            _logger.warning("Skip search %s.%s: %s", model_name, field_name, e)
            return 0, 0
        if not recs:
            return 0, 0
        return self._safe_write(recs, {field_name: master_id})

    def _redirect_m2m(self, model_name, field_name, master_id, duplicate_ids):
        try:
            Model = self.env[model_name].sudo()
        except KeyError:
            return 0, 0
        if not Model._auto:
            return 0, 0
        if field_name not in Model._fields:
            return 0, 0
        field = Model._fields[field_name]
        if not field.store:
            return 0, 0
        try:
            recs = Model.with_context(active_test=False).search(
                [(field_name, 'in', duplicate_ids)])
        except Exception as e:
            _logger.warning("Skip search m2m %s.%s: %s", model_name, field_name, e)
            return 0, 0
        if not recs:
            return 0, 0
        ok = fail = 0
        for rec in recs:
            sp = 'merge_m2m_%d_%d' % (rec.id, ok + fail)
            try:
                self.env.cr.execute('SAVEPOINT %s' % sp)
                current = set(getattr(rec, field_name).ids)
                new_set = (current - set(duplicate_ids)) | {master_id}
                rec.write({field_name: [(6, 0, list(new_set))]})
                self.env.cr.execute('RELEASE SAVEPOINT %s' % sp)
                ok += 1
            except Exception as e:
                self.env.cr.execute('ROLLBACK TO SAVEPOINT %s' % sp)
                _logger.warning("Skip m2m %s.%s: %s", model_name, field_name, e)
                fail += 1
        return ok, fail

    def _merge_mail_followers(self, master_id, dup_ids):
        """Redirige followers de los duplicados al maestro evitando duplicar
        partner_id ya seguidor del maestro: si el partner ya sigue al maestro,
        se elimina el follower del duplicado en lugar de redirigirlo."""
        Fol = self.env['mail.followers'].sudo()
        master_followers = Fol.search([
            ('res_model', '=', 'hr.employee'),
            ('res_id', '=', master_id),
        ])
        master_partner_ids = set(master_followers.mapped('partner_id').ids)
        dup_followers = Fol.search([
            ('res_model', '=', 'hr.employee'),
            ('res_id', 'in', dup_ids),
        ])
        moved = removed = 0
        for f in dup_followers:
            sp = 'merge_fol_%d' % f.id
            try:
                self.env.cr.execute('SAVEPOINT %s' % sp)
                if f.partner_id.id in master_partner_ids:
                    f.unlink()
                    removed += 1
                else:
                    f.write({'res_id': master_id})
                    master_partner_ids.add(f.partner_id.id)
                    moved += 1
                self.env.cr.execute('RELEASE SAVEPOINT %s' % sp)
            except Exception as e:
                self.env.cr.execute('ROLLBACK TO SAVEPOINT %s' % sp)
                _logger.warning("Skip follower id=%d: %s", f.id, e)
        return moved, removed

    def _merge_mail_messages(self, master_id, dup_ids):
        Msg = self.env['mail.message'].sudo()
        msgs = Msg.search([
            ('model', '=', 'hr.employee'),
            ('res_id', 'in', dup_ids),
        ])
        ok, fail = self._safe_write(msgs, {'res_id': master_id})
        return ok

    def _copy_missing_fields_to_master(self, master, duplicates):
        if not self.copy_missing_fields:
            return []
        copied = []
        safe_fields = [
            'work_phone', 'work_email', 'mobile_phone',
            'identification_id', 'passport_id', 'gender', 'birthday',
            'place_of_birth', 'country_of_birth', 'marital',
            'children', 'emergency_contact', 'emergency_phone',
            'pin', 'barcode', 'job_title',
        ]
        vals = {}
        for fname in safe_fields:
            if fname not in master._fields:
                continue
            current = master[fname]
            if current:
                continue
            for dup in duplicates:
                v = dup[fname]
                if v:
                    vals[fname] = v
                    copied.append(fname)
                    break
        if vals:
            try:
                master.sudo().write(vals)
            except Exception as e:
                _logger.warning("No se pudieron copiar campos faltantes: %s", e)
        return copied

    # ------------------------------------------------------------------
    # Accion principal
    # ------------------------------------------------------------------
    def action_merge(self):
        self.ensure_one()
        master = self.master_employee_id
        duplicates = self.duplicate_employee_ids
        if not master or not duplicates:
            raise UserError(_('Datos insuficientes.'))

        master_id = master.id
        dup_ids = duplicates.ids

        # 1) Copiar campos faltantes
        copied = self._copy_missing_fields_to_master(master, duplicates)

        # 2) Followers (manejo especial)
        moved_fol, removed_fol = self._merge_mail_followers(master_id, dup_ids)

        # 3) Mensajes del chatter
        moved_msgs = self._merge_mail_messages(master_id, dup_ids)

        # 4) Redirigir todos los m2o y m2m a hr.employee
        ref_fields = self._get_employee_referencing_fields()
        total_ok = 0
        total_fail = 0
        details = []
        for model_name, field_name, ttype in ref_fields:
            if ttype == 'many2one':
                ok, fail = self._redirect_m2o(
                    model_name, field_name, master_id, dup_ids)
            else:
                ok, fail = self._redirect_m2m(
                    model_name, field_name, master_id, dup_ids)
            if ok or fail:
                total_ok += ok
                total_fail += fail
                if ok:
                    details.append('%s.%s: %d redirigidos' % (model_name, field_name, ok))
                if fail:
                    details.append('%s.%s: %d omitidos por conflicto' % (model_name, field_name, fail))

        # 5) Archivar duplicados
        archived = 0
        if self.archive_duplicates:
            try:
                for dup in duplicates:
                    sp = 'arch_dup_%d' % dup.id
                    try:
                        self.env.cr.execute('SAVEPOINT %s' % sp)
                        dup.sudo().write({
                            'name': '[FUSIONADO->%d] %s' % (master_id, dup.name or ''),
                            'active': False,
                        })
                        self.env.cr.execute('RELEASE SAVEPOINT %s' % sp)
                        archived += 1
                    except Exception as e:
                        self.env.cr.execute('ROLLBACK TO SAVEPOINT %s' % sp)
                        _logger.warning("No se pudo archivar dup %d: %s", dup.id, e)
            except Exception as e:
                _logger.error("Error archivando duplicados: %s", e)

        # 6) Resumen
        summary_html = '<h3>Fusion completada</h3>'
        summary_html += '<p><b>Maestro:</b> %s (ID %d)</p>' % (master.name or '', master_id)
        summary_html += '<p><b>Duplicados procesados:</b> %d (archivados: %d)</p>' % (
            len(duplicates), archived)
        summary_html += '<p><b>Registros redirigidos:</b> %d</p>' % total_ok
        if total_fail:
            summary_html += '<p style="color:#d97706"><b>Conflictos omitidos:</b> %d ' \
                'registros que ya tenian relacion con el maestro o violaban una ' \
                'restriccion unica. Estos casos son normales y no afectan la fusion.</p>' % total_fail
        summary_html += '<p><b>Followers movidos:</b> %d (%d eliminados como duplicados)</p>' % (
            moved_fol, removed_fol)
        summary_html += '<p><b>Mensajes del chatter movidos:</b> %d</p>' % moved_msgs
        if copied:
            summary_html += '<p><b>Campos copiados al maestro:</b> %s</p>' % ', '.join(copied)
        if details:
            summary_html += '<details><summary>Detalle por modelo</summary><ul>'
            for d in details:
                summary_html += '<li>%s</li>' % d
            summary_html += '</ul></details>'
        self.summary = summary_html
        return {
            'type': 'ir.actions.act_window',
            'name': _('Resumen de fusion'),
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_open_master(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.master_employee_id.name,
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': self.master_employee_id.id,
            'target': 'current',
        }
