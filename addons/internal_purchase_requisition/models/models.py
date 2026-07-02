from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseRequisition(models.Model):
    _name = 'purchase.requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Purchase Requisition'

    name = fields.Char(string='Requisition Reference', required=True, copy=False, readonly=True, index=True,
                       default=lambda self: _('New'), tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True, tracking=True)
    department_manager_id = fields.Many2one('hr.employee', related='department_id.manager_id')
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user,
                                   tracking=True, required=True)
    date = fields.Date(string='Requisition Date', default=fields.Date.context_today, tracking=True, required=True)
    deadline_date = fields.Date(string='Requisition Deadline', tracking=True)
    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'In-Review'),
        ('procurement_officer_approved', 'Procurement Officer Approved'),
        ('approved', 'Fully Approved'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled'),
        ('done','Done')
    ], string='Approval Status', default='draft', tracking=True)
    requisition_line_ids = fields.One2many('purchase.requisition.line', 'requisition_id', string='Requisition Lines',
                                           tracking=True, required=True)
    purchase_order_count = fields.Integer(string='Purchase Order Count', compute='_compute_purchase_order_count')
    subject = fields.Char(string='Subject', tracking=True, required=True)  # New Subject field
    cc_users = fields.Many2many('res.users', string='CC', tracking=True)
    purchase_order_status = fields.Char(string='Purchase Order Status', compute='_compute_purchase_order_status')
    active = fields.Boolean(default=True)  # Add this field to support archiving
    approval_stage = fields.Char(string='Approval Stage', compute='_compute_approval_status', tracking=True)
    is_manager = fields.Boolean(compute='_compute_is_manager')

    @api.depends('department_id')
    def _compute_is_manager(self):
        for record in self:
            record.is_manager = record.department_id.manager_id.user_id.id == self.env.user.id

    @api.depends('approval_status')  # Assuming you have a state field or similar
    def _compute_approval_status(self):
        for record in self:
            if record.approval_status == 'submitted':
                record.approval_stage = 'Approve Pending Procurement Officer'
            elif record.approval_status == 'procurement_officer_approved':
                record.approval_stage = 'Approve Pending Head of Deparment'
            elif record.approval_status == 'approved':
                record.approval_stage = 'Head of Department Approved'
            else:
                record.approval_stage = 'None'


    def action_archive(self):
        self.write({'active': False})

    def action_unarchive(self):
        self.write({'active': True})

    def _compute_purchase_order_status(self):
        # Get the state selection values from the purchase.order model
        purchase_order_model = self.env['purchase.order']
        state_selection = dict(purchase_order_model.fields_get(allfields=['state'])['state']['selection'])

        for requisition in self:
            # Determine if it's a single requisition or needs to check for multiple
            purchase_orders = purchase_order_model.search(
                [('requisition_ids', 'in', requisition.id)])  # Use 'in' for single or multiple requisition IDs

            if purchase_orders:
                # Map the internal states to their labels
                mapped_statuses = [
                    state_selection.get(po.state, po.state) for po in purchase_orders
                ]
                # Join the unique labels into a string
                requisition.purchase_order_status = ', '.join(set(mapped_statuses))
            else:
                requisition.purchase_order_status = 'None'

    def action_approve_by_procurement_officer(self):
        # Check if the user is in the Procurement Officer group
        procurement_officer_group = self.env.ref('internal_purchase_requisition.group_procurement_officer')
        if procurement_officer_group not in self.env.user.groups_id:
            raise models.ValidationError(
                _("Only members of the Procurement Officer group can approve this requisition."))
        self.write({'approval_status': 'procurement_officer_approved'})

    def action_approve_by_manager(self):
        if self.env.user != self.department_id.manager_id.user_id:
            raise models.ValidationError(
                _("Only the department head for %s can approve this requisition.") % self.department_id.name)
        self.write({'approval_status': 'approved'})
        # self.write({'approval_status': 'done'})

    @api.depends('approval_status')
    def _compute_statusbar_states(self):
        for record in self:
            if record.approval_status == 'closed':
                record.statusbar_states = 'closed'
            else:
                record.statusbar_states = record.approval_status

    @api.model
    def create(self, vals):
        """Function to generate purchase requisition sequence"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'purchase.requisition') or 'New'
        result = super(PurchaseRequisition, self).create(vals)
        return result

    def _compute_purchase_order_count(self):
        for requisition in self:
            requisition.purchase_order_count = self.env['purchase.order'].search_count([
                ('requisition_ids', '=', requisition.id)
            ])

    def action_submit(self):
        # Check if there are no requisition lines
        if not self.requisition_line_ids:
            raise models.ValidationError(_("You must add at least one requisition line before submitting."))
        self.write({'approval_status': 'submitted'})

    def action_cancel(self):
        self.write({'approval_status': 'cancel'})

    def action_reject(self):
        self.write({'approval_status': 'rejected'})

    def reset_draft(self):
        self.write({'approval_status': 'draft'})

    def action_create_purchase_order(self):
        """Redirect to the purchase order form view with the requisition lines."""
        if not self.requisition_line_ids:
            raise UserError(_('Please add requisition lines before creating a purchase order.'))

        # Prepare the values for the order lines to pass through the context
        order_lines = [(0, 0, {
            'product_id': line.product_id.id,
            'product_qty': line.quantity,
            'price_unit': line.price,
            'name': line.description or line.product_id.name,
            'product_uom': line.product_uom.id,
            'date_planned': fields.Datetime.now(),
        }) for line in self.requisition_line_ids]


        # Return an action to open the purchase order form in "create" mode with the pre-filled lines
        return {
            'name': _('Create Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'view_id': self.env.ref('purchase.purchase_order_form').id,
            'target': 'current',
            'context': {
                'default_requisition_ids': self.ids,
                'default_order_line': order_lines,
            },
        }

    def action_view_purchase_orders(self):
        """Return an action to open related purchase orders."""
        self.ensure_one()
        return {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('requisition_ids', '=', self.id)],
            'context': {'default_requisition_id': self.id,
                        'create': False}
        }

    def create_purchase_order_from_requisition(self):
        """Open a purchase order form with requisition details pre-filled, but do not create the PO automatically."""
        order_lines = []
        requisition_ids = []

        for requisition in self:
            # Ensure the requisition is approved
            if requisition.purchase_order_status not in ['None','Cancelled']:
                raise UserError(
                    _("An RFQ or purchase order has already been created for requisition '%s'." % requisition.name))
            if requisition.approval_status != 'approved':
                raise UserError(
                    _("The requisition '%s' is not approved. Please approve the requisition first." % requisition.name))

            # Prepare the order lines from requisition lines
            for line in requisition.requisition_line_ids:
                order_line = {
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.price,
                    'name': line.description or line.product_id.name,
                }
                order_lines.append((0, 0, order_line))

            requisition_ids.append(requisition.id)  # Collect requisition IDs

        if not order_lines:
            raise UserError(_("No requisition lines are available for purchase order creation."))

        self._compute_purchase_order_status()


        # Return the action to open the purchase order form with pre-filled data
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': {
                'default_requisition_ids': [(4, req_id) for req_id in requisition_ids],  # Link all requisitions
                'default_order_line': order_lines  # Pass all order lines
            }
        }


class PurchaseRequisitionLine(models.Model):
    _name = 'purchase.requisition.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Purchase Requisition Line'

    product_id = fields.Many2one('product.product', string='Product', required=True, tracking=True)
    quantity = fields.Float(string='Quantity', required=True, tracking=True)
    product_uom = fields.Many2one(comodel_name='uom.uom', string="Unit", tracking=True, related='product_id.uom_id')
    price = fields.Float(string='Price', tracking=True)
    description = fields.Text(string='Description', tracking=True)
    requisition_id = fields.Many2one('purchase.requisition', string='Requisition Reference', required=True)
    sequence = fields.Integer(string='Sequence')

    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line', readonly=True,
                                             copy=False)

    @api.model
    def create(self, vals):
        """Function to automatically set sequence for each requisition line."""
        if 'requisition_id' in vals:
            requisition = self.env['purchase.requisition'].browse(vals['requisition_id'])
            line_count = len(requisition.requisition_line_ids) + 1  # Next sequence
            vals['sequence'] = line_count
        return super(PurchaseRequisitionLine, self).create(vals)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    requisition_id = fields.Many2one('purchase.requisition', string='Requisition Reference')
    requisition_ids = fields.Many2many('purchase.requisition', string='Requisition References')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    commercial_registration = fields.Binary("Commercial Registration",help="Upload a copy of the Commercial Registration")
    municipal_license = fields.Binary("Municipal License", help="Upload a copy of the Municipal License")
    computer_card = fields.Binary("Computer Card (Establishment Card)", help="Upload a copy of the Computer Card")
    classification_certificate = fields.Binary("Classification Certificate",help="Upload a copy of the Classification Certificate")
    tax_card = fields.Binary("Tax Card", help="Upload a copy of the Tax Card")
    authorized_signatories_qid = fields.Binary("Authorized Signatories QID",help="Upload a copy of the Authorized Signatories QID")
    company_profile = fields.Binary("Company Profile", help="Upload a copy of the Company Profile")
    pre_qualification_form = fields.Binary("Pre-qualification Form", help="Upload a signed and stamped Pre-qualification Form")
    moi_approved_documents = fields.Binary("MOI Approved Documents",help="Upload MOI approved documents, if applicable")
    kahramaa_certificate = fields.Binary("Kahramaa Certificate", help="Upload Kahramaa certificate, if applicable")
    qcd_certificate = fields.Binary("QCD Certificate", help="Upload QCD certificate, if applicable")

    verified_partner = fields.Boolean("Verified Partner", help="Check if the vendor is verified")
