/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class PagoparConnectionTest extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
    }

    async testConnection(providerId) {
        try {
            const result = await this.rpc("/web/dataset/call_kw", {
                model: "payment.provider",
                method: "action_test_pagopar_connection",
                args: [providerId],
                kwargs: {},
            });

            if (result && result.params) {
                if (result.params.type === 'success') {
                    this.notification.add(result.params.message, {
                        title: result.params.title,
                        type: "success",
                    });
                } else {
                    this.notification.add(result.params.message, {
                        title: result.params.title,
                        type: "danger",
                    });
                }
            }
        } catch (error) {
            this.notification.add(_t("Error al probar la conexión"), {
                type: "danger",
            });
        }
    }
}

export class PagoparTransactionChecker extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
    }

    async checkTransactionStatus(transactionIds) {
        try {
            const result = await this.rpc("/web/dataset/call_kw", {
                model: "payment.transaction",
                method: "action_check_pagopar_status",
                args: [transactionIds],
                kwargs: {},
            });

            if (result && result.params) {
                this.notification.add(result.params.message, {
                    title: result.params.title,
                    type: result.params.type === 'success' ? "success" : "warning",
                });
            }
        } catch (error) {
            this.notification.add(_t("Error al verificar el estado"), {
                type: "danger",
            });
        }
    }
}

registry.category("components").add("PagoparConnectionTest", PagoparConnectionTest);
registry.category("components").add("PagoparTransactionChecker", PagoparTransactionChecker);
