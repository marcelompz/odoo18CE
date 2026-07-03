from odoo import models, api
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_settle_due(self):
        settle_due_product = self.env.ref('pos_customer_balance_ce.product_product_settle_due', raise_if_not_found=False)
        for product in self:
            if settle_due_product and product.id == settle_due_product.id:
                raise UserError("Seguridad: No puedes eliminar el producto 'Abono de Cuenta' porque es vital para el sistema de cobro de deudas del TPV.")

    def write(self, vals):
        settle_due_product = self.env.ref('pos_customer_balance_ce.product_product_settle_due', raise_if_not_found=False)
        if settle_due_product:
            for product in self:
                if product.id == settle_due_product.id:
                    # Prevent disabling available_in_pos
                    if 'available_in_pos' in vals and not vals['available_in_pos']:
                        raise UserError("Seguridad: No puedes deshabilitar el producto 'Abono de Cuenta' del TPV.")
                    
                    # Prevent changing the product type to stockable (must be service)
                    if 'type' in vals and vals['type'] != 'service':
                        raise UserError("Seguridad: El producto 'Abono de Cuenta' debe ser obligatoriamente un Servicio.")
        
        return super().write(vals)
