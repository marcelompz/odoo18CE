/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

/**
 * @props partner
 */
patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        console.log("ActionpadWidget");
        this.isSubmitClicked = false;
    },

    async submitOrder() {
        var self = this;
        if (!this.isSubmitClicked) {
            this.isSubmitClicked = true;
            try {
                const currentOrder = this.pos.get_order();
                await self.orm.call("pos.order", "check_order_status", ["", currentOrder.pos_reference]).then(function(result){
                    if (result == false){
                        self.kitchen_order_status = false;
                        self.env.services.dialog.add(AlertDialog, {
                            title: _t("Order is Completed"),
                            body: _t("This Order is Completed. Please create a new Order"),
                        });
                    }
                    else{
                         self.kitchen_order_status = true;
                    }
                });
                if (self.kitchen_order_status){
                    if (this.pos.sendOrderInPreparationUpdateLastChange) {
                        await this.pos.sendOrderInPreparationUpdateLastChange(currentOrder);
                    }
                    await this.processOrderForKitchen();
                    if (this.env.bus) {
                        this.env.bus.trigger('pos-kitchen-screen-update');
                    }
                }
            } finally {
                this.isSubmitClicked = false;
            }
        }
    },

    async processOrderForKitchen() {
        var self = this;
        const currentOrder = this.pos.get_order();
        const orderData = {
            'pos_reference': currentOrder.pos_reference,
            'config_id': currentOrder.config_id?.id,
            'table_id': currentOrder.table_id?.id || false,
            'session_id': currentOrder.session_id?.id || currentOrder.session_id
        };
        if (this.pos.syncAllOrders) {
            this.pos.syncAllOrders();
        }
        await self.orm.call("pos.order", "process_order_for_kitchen", [orderData]);
    }
});

