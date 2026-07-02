/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import { _t } from '@web/core/l10n/translation';

// Extend a new widget named DeliveryMethods for loading delivery methods in payment page
publicWidget.registry.DeliveryMethods = publicWidget.Widget.extend({
    selector: '.o_website_sale_checkout',
    events: {
        'click [name="o_delivery_radio"]': '_selectDeliveryMethod',
    },
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },
    /**
     * @override
     */
    async start() {
        this.mainButton = document.querySelector('a[name="o_payment_submit_button"]');
        await this._prepareDeliveryMethods();
    },
    /**
     * Copied from checkout.js for loading delivery method template in payment template
     */
    async _selectDeliveryMethod(ev) {
        const checkedRadio = ev.currentTarget;
        if (checkedRadio.disabled) {  // The delivery rate request failed.
            return; // Failing delivery methods cannot be selected.
        }

        // Disable the main button while fetching delivery rates.
        this._disableMainButton();

        // Fetch delivery rates and update the cart summary and the price badge accordingly.
        await this._updateDeliveryMethod(checkedRadio);

        // Re-enable the main button after delivery rates have been fetched.
        this._enableMainButton();

        // Show a button to open the location selector if required for the selected delivery method.
        await this._showPickupLocation(checkedRadio);
    },

     async _prepareDeliveryMethods() {
        // Load the radios from the DOM here to update them if the template is re-rendered.
        this.dmRadios = Array.from(document.querySelectorAll('input[name="o_delivery_radio"]'));
        if (this.dmRadios.length > 0) {
            const checkedRadio = document.querySelector('input[name="o_delivery_radio"]:checked');
            this._disableMainButton();
            if (checkedRadio) {
                await this._updateDeliveryMethod(checkedRadio);
                this._enableMainButton();
            }
        }
        // Asynchronously fetch delivery rates to mitigate delays from third-party APIs
        await Promise.all(this.dmRadios.filter(radio => !radio.checked).map(async radio => {
            this._showLoadingBadge((radio));
            const rateData = await this._getDeliveryRate(radio);
            this._updateAmountBadge(radio, rateData);
        }));
    },

    async _updateDeliveryMethod(radio) {
        this._showLoadingBadge(radio);
        const result = await this._setDeliveryMethod(radio.dataset.dmId);
        this._updateAmountBadge(radio, result);
        this._updateCartSummary(result);
    },

    async _showPickupLocation(radio) {
        if (!radio.dataset.isPickupLocationRequired || radio.disabled) {
            return;  // Fetching the delivery rate failed.
        }
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        const pickupLocation = deliveryMethodContainer.querySelector('[name="o_pickup_location"]');

        const editPickupLocationButton = pickupLocation.querySelector(
            'span[name="o_pickup_location_selector"]'
        );
        if (editPickupLocationButton.dataset.pickupLocationData) {
            await this._setPickupLocation(editPickupLocationButton.dataset.pickupLocationData);
        }

        pickupLocation.classList.remove('d-none'); // Show the whole div.
    },

    async _setPickupLocation(pickupLocationData) {
        await rpc('/website_sale/set_pickup_location', {pickup_location_data: pickupLocationData});
    },
    _updateAmountBadge(radio, rateData) {
        const deliveryPriceBadge = this._getDeliveryPriceBadge(radio);
        if (rateData.success) {
             // If it's a free delivery (`free_over` field), show 'Free', not '$ 0'.
             if (rateData.is_free_delivery) {
                 deliveryPriceBadge.textContent = _t("Free");
             } else {
                 deliveryPriceBadge.innerHTML = rateData.amount_delivery;
             }
             this._toggleDeliveryMethodRadio(radio);
        } else {
            deliveryPriceBadge.textContent = rateData.error_message;
            this._toggleDeliveryMethodRadio(radio, true);
        }
    },

    _toggleDeliveryMethodRadio(radio, disable=false) {
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        radio.disabled = disable;
        if (disable) {
            deliveryMethodContainer.classList.add('text-muted');
        }
        else {
            deliveryMethodContainer.classList.remove('text-muted');
        }
    },

    _updateCartSummary(result) {
        const amountDelivery = document.querySelector('#order_delivery .monetary_field');
        const amountUntaxed = document.querySelector('#order_total_untaxed .monetary_field');
        const amountTax = document.querySelector('#order_total_taxes .monetary_field');
        const amountTotal = document.querySelectorAll(
            '#order_total .monetary_field, #amount_total_summary.monetary_field'
        );
        amountDelivery.innerHTML = result.amount_delivery;
        amountUntaxed.innerHTML = result.amount_untaxed;
        amountTax.innerHTML = result.amount_tax;
        amountTotal.forEach(total => total.innerHTML = result.amount_total);
    },

    async _setDeliveryMethod(dmId) {
        return await rpc('/shop/set_delivery_method', {'dm_id': dmId});
    },

    async _getDeliveryRate(radio) {
        return await rpc('/shop/get_delivery_rate', {'dm_id': radio.dataset.dmId});
    },

    _disableMainButton() {
        this.mainButton?.classList.add('disabled');
    },

    _enableMainButton() {
        if (this._isDeliveryMethodReady()) {
            this.mainButton?.classList.remove('disabled');
        }
    },

    _showLoadingBadge(radio) {
        const deliveryPriceBadge = this._getDeliveryPriceBadge(radio);
        this._clearElement(deliveryPriceBadge);
        deliveryPriceBadge.appendChild(this._createLoadingElement());
    },

    _clearElement(el) {
        while (el.firstChild) {
            el.removeChild(el.lastChild);
        }
    },

    _createLoadingElement() {
        const loadingElement = document.createElement('i');
        loadingElement.classList.add('fa', 'fa-circle-o-notch', 'fa-spin', 'center');
        return loadingElement;
    },

    _isDeliveryMethodReady() {
        if (this.dmRadios.length === 0) { // No delivery method is available.
            return true; // Ignore the check.
        }
        const checkedRadio = document.querySelector('input[name="o_delivery_radio"]:checked');
        return checkedRadio
            && !checkedRadio.disabled
            && !this._isPickupLocationMissing(checkedRadio);
    },

    _getDeliveryPriceBadge(radio) {
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        return deliveryMethodContainer.querySelector('.o_wsale_delivery_price_badge');
    },

    _isPickupLocationMissing(radio) {
        const deliveryMethodContainer = this._getDeliveryMethodContainer(radio);
        if (!this._isPickupLocationRequired(radio)) return false;
        return !deliveryMethodContainer.querySelector(
            'span[name="o_pickup_location_selector"]'
        ).dataset.locationId;
    },

    _getDeliveryMethodContainer(el) {
        return el.closest('[name="o_delivery_method"]');
    },

    _isPickupLocationRequired(radio) {
        return Boolean(radio.dataset.isPickupLocationRequired);
    },
});
