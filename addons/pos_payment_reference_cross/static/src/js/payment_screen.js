/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

// Parche a la pantalla principal (Componente OWL)
patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        for (const line of this.currentOrder.payment_ids) {
            if (line.payment_method_id.require_reference && !line.transaction_reference) {
                this.dialog.add(AlertDialog, {
                    title: _t("Falta Referencia de Pago"),
                    body: _t(`El método de pago '${line.payment_method_id.name}' requiere un número de referencia.`),
                });
                return;
            }
        }
        await super.validateOrder(isForceValidate);
    }
});

// Parche al componente de las líneas de pago (Componente OWL)
patch(PaymentScreenPaymentLines.prototype, {
    onReferenceChange(line, value) {
        line.set_transaction_reference(value);
    }
});
