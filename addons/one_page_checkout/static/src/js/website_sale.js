/** @odoo-module **/

import wSaleUtils from "@website_sale/js/website_sale_utils";
import VariantMixin from "@website_sale/js/sale_variant_mixin";
import publicWidget from '@web/legacy/js/public/public_widget';
import { cartHandlerMixin } from '@website_sale/js/website_sale_utils';
import { WebsiteSale } from '@website_sale/js/website_sale';
import { _t } from "@web/core/l10n/translation";
// Eliminar import de @website_sale/js/website_sale_delivery si no existe en Odoo 18
// import '@website_sale/js/website_sale_delivery';
// Importar el archivo propio usando ruta relativa
import './website_sale_delivery.js';
// Importar el archivo propio usando ruta relativa
import './payment_demo.js';
import { rpc } from "@web/core/network/rpc_service";

publicWidget.registry.OnePageCheckoutWebsiteSale = publicWidget.Widget.extend(
VariantMixin, cartHandlerMixin, {
        selector: '.single_pg_checkout_layout',
        events: Object.assign({}, VariantMixin.events || {}, {
            'click .a-submit': '_onClickSubmit',
            'click .show_coupon': '_onClickShowCoupon',
            'change select[name="country_id"]': '_onChangeCountry',
            'click span[title="Details"]': '_onCartDetailClick',
        }),
        /**
         * Inicializa el widget.
         * Establece la propiedad `isWebsite` en `true`.
         */
        init: function () {
            this._super.apply(this, arguments);
            this.isWebsite = true;
        },

        /**
         * Inicia el widget.
         * Llama al método super y retorna la promesa resultante.
         * @returns {Promise} Una promesa que representa el inicio del widget.
         */
        start() {
            const def = this._super(...arguments);
            return def;
        },
        /**
         * Destruye el widget.
         * Llama al método super y realiza cualquier limpieza necesaria.
         */
        destroy() {
            this._super.apply(this, arguments);
            this._cleanupZoom();
        },
        /**
         * Cambia el país y actualiza los campos correspondientes
            basados en el país seleccionado.
         */
        _changeCountry: function () {
        var self = this
        if (!this.$el.find("#country_id").val()) {
            return;
        }
        return rpc("/shop/country_infos/" + $("#country_id").val(), {
            mode: this.$el.find("#country_id").attr('mode'),
        }).then(function (data) {
            // placeholder phone_code
            self.$el.find("input[name='phone']").attr('placeholder', data.phone_code !== 0 ? '+'+ data.phone_code : '');

            // populate states and display
            var selectStates = self.$el.find("select[name='state_id']");
            // dont reload state at first loading (done in qweb)
            if (selectStates.data('init')===0 || selectStates.find('option').length===1) {
                if (data.states.length || data.state_required) {
                    selectStates.html('');
                    data.states.forEach((x) => {
                        var opt = self.$el.find('<option>').text(x[1])
                            .attr('value', x[0])
                            .attr('data-code', x[2]);
                        selectStates.append(opt);
                    });
                    selectStates.parent('div').show();
                } else {
                    selectStates.val('').parent('div').hide();
                }
                selectStates.data('init', 0);
            } else {
                selectStates.data('init', 0);
            }

            // manage fields order / visibility
            if (data.fields) {
                if (data.fields.indexOf("zip") > data.fields.indexOf("city")){
                    self.$el.find(".div_zip").before(self.$el.find(".div_city"));
                } else {
                    self.$el.find(".div_zip").after(self.$el.find(".div_city"));
                }
                var all_fields = ["street", "zip", "city", "country_name"]; // "state_code"];
                all_fields.forEach((field) => {
                    self.$el.find(".checkout_autoformat .div_" + field.split('_')[0]).toggle(data.fields.indexOf(field)>=0);
                });
            }

            if (self.$el.find("label[for='zip']").length) {
                self.$el.find("label[for='zip']").toggleClass('label-optional', !data.zip_required);
                self.$el.find("label[for='zip']").get(0).toggleAttribute('required', !!data.zip_required);
            }
            if (self.$el.find("label[for='zip']").length) {
                self.$el.find("label[for='state_id']").toggleClass('label-optional', !data.state_required);
                self.$el.find("label[for='state_id']").get(0).toggleAttribute('required', !!data.state_required);
            }
        });
    },
        /**
         * Maneja el evento de clic en los botones de envío y realiza las acciones necesarias.
         * @param {Event} ev - El evento de clic.
         * @param {boolean} forceSubmit - Determina si se debe forzar la envío
            incluso si ciertas condiciones no se cumplen.
         */
        _onClickSubmit: function (ev, forceSubmit) {
            if (this.$(ev.currentTarget).is('#products_grid .a-submit') && !forceSubmit) {
                return;
            }
            var $aSubmit = this.$(ev.currentTarget);
            if (!ev.isDefaultPrevented() && !$aSubmit.is(".disabled")) {
                ev.preventDefault();
                $aSubmit.closest('form').submit();
            }
            if ($aSubmit.hasClass('a-submit-loading')) {
                var loading = '<span class="fa fa-cog fa-spin"/>';
                var fa_span = $aSubmit.find('span[class*="fa"]');
                if (fa_span.length) {
                    fa_span.replaceWith(loading);
                } else {
                    $aSubmit.append(loading);
                }
            }
        },
        /**
         * Maneja el evento de clic para mostrar el formulario de cupón ocultando el
            botón "mostrar cupón" y mostrando el formulario de cupón.
         * @param {Event} ev - El evento de clic.
         */
        _onClickShowCoupon: function (ev) {
            this.$el.find(".show_coupon").hide();
            this.$el.find('.coupon_form').removeClass('d-none');
        },
        /**
         * Maneja el evento de cambio en el campo de país y activa la funcionalidad de cambio de país.
         * Si el elemento checkout_autoformat no está presente, la función no hace nada.
         * Esta función llama internamente a la función _changeCountry.
         * @param {Event} ev - El evento de cambio.
         */
        _onChangeCountry: function (ev) {
            if (!this.$('.checkout_autoformat').length) {
                return;
            }
            this._changeCountry();
        },
        /**
         * Maneja el evento de clic en el elemento de detalle del carrito.
         * Alterna el icono de chevron y muestra/oculta el div de resumen según corresponda.
         * @param {Event} ev - El evento de clic.
         */
        _onCartDetailClick: function(ev) {
            var $elem = this.$(ev.currentTarget);
            if ($elem.hasClass('fa-chevron-down')) {
                $elem.removeClass('fa-chevron-down');
                $elem.addClass('fa-chevron-up');
            } else {
                $elem.removeClass('fa-chevron-up');
                $elem.addClass('fa-chevron-down');
            }
            var $summary_div = this.$el.find('.toggle_summary_div');
            $summary_div.toggleClass('d-none');
        }
});
/**
 * Este widget se utiliza para la funcionalidad del carrito de la página de pago único.
 * Añade eventos para cambiar el envío y editar la dirección.
 */
publicWidget.registry.OnePageCheckoutWebsiteSaleCart = publicWidget.Widget.extend({
    selector: '.single_pg_checkout_layout .oe_cart',
    events: {
        'click .js_change_shipping': '_onClickChangeShipping',
        'click .js_edit_address': '_onClickEditAddress',
    },
    /**
     * Maneja el evento de clic en el elemento "Cambiar Envío".
     * Actualiza las opciones de envío cambiando la visibilidad y aplicando clases CSS.
     * Realiza una solicitud POST para actualizar la opción de envío seleccionada mediante AJAX.
     * @param {Event} ev - El evento de clic.
     */
    _onClickChangeShipping: function (ev) {
        var $old = this.$el.find('.all_shipping').find('.card.border.border-primary');
        $old.find('.btn-ship').toggle();
        $old.addClass('js_change_shipping');
        $old.removeClass('border border-primary');

        var $new = this.$(ev.currentTarget).parent('div.one_kanban').find('.card');
        $new.find('.btn-ship').toggle();
        $new.removeClass('js_change_shipping');
        $new.addClass('border border-primary');

        var $form = this.$(ev.currentTarget).parent('div.one_kanban').find('form.d-none');
        this.$.post($form.attr('action'), $form.serialize()+'&xhr=1');
    },
    /**
     * Maneja el evento de clic en el elemento "Editar Dirección".
     * Previene la acción por defecto del evento de clic.
     * Actualiza el atributo de acción del formulario correspondiente y lo envía.
     * @param {Event} ev - El evento de clic.
     */
    _onClickEditAddress: function (ev) {
        ev.preventDefault();
        this.$(ev.currentTarget).closest('div.one_kanban').find('form.d-none').attr('action', '/shop/address').submit();
    }
});
return {
    OnePageCheckoutWebsiteSale: publicWidget.registry.OnePageCheckoutWebsiteSale,
    OnePageCheckoutWebsiteSaleCart: publicWidget.registry.OnePageCheckoutWebsiteSaleCart,
};
