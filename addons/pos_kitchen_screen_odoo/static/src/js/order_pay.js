/** @odoo-module **/
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
const { Component, useState } = owl;
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { deduceUrl, random5Chars, uuidv4, getOnNotified } from "@point_of_sale/utils";
import {
    makeAwaitable,
    ask,
    makeActionAwaitable,
} from "@point_of_sale/app/utils/make_awaitable_dialog";


/*
 * Patching the Order class to add custom functionality.
 */
patch(PosStore.prototype, {
    async setup(env) {
        await super.setup(...arguments);
        console.log("PosStore",PosStore)

        this.kitchen = true;

    },
    async initServerData() {
        const result = await super.initServerData(...arguments);
        if (this.bus) {
            this.onNotified = getOnNotified(this.bus, this.config.access_token);
        }
        return result;
    },
    async pay() {
        let order_name = this.getOrder().pos_reference;
        let self = this;
        const result = await rpc("/web/dataset/call_kw/pos.order/check_order",{
            model: 'pos.order', method: 'check_order',
            args: [order_name],
            kwargs: {},
        });
        if (result.category) {
            let title = "No category found for your current order in the kitchen.(" + result.category + ')';
            self.kitchen = false;
            await this.env.services.dialog.add(AlertDialog, {
                title: _t(title),
                body: _t("No food items found for the specified category for this kitchen. Kindly remove the selected food and update the order by clicking the 'Order' button. Following that, proceed with the payment."),
            });
            return false
        } else if (result == true) {
            self.kitchen = false;
            await this.env.services.dialog.add(AlertDialog, {
                title: _t("Food is not ready"),
                body: _t("Please Complete all the food first."),
            });
            return false
        } else {
            self.kitchen = true;
        }

        return super.pay(...arguments);
    }


});