/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";
import VariantMixin from "@website_sale/js/sale_variant_mixin";
import wSaleUtils from "@website_sale/js/website_sale_utils";
const cartHandlerMixin = wSaleUtils.cartHandlerMixin;

publicWidget.registry.LookBook = publicWidget.Widget.extend(VariantMixin, cartHandlerMixin, {
    selector: '.shop_the_look_product',
    events: Object.assign({}, VariantMixin.events || {}, {

        'click a.js_add_cart_json': '_onClickAddCartJSON',
        'change .variant_select': '_onChangeVariantSelect',
        'change .items_to_add': '_onChangeitemsToAdd',
        'click .recent-add': '_onAddToCartBtn',
        'change .js_add_cart_json': 'onChangeAddQuantity',
        'change #modal_qty': '_onChangeModalQty',
        'click #add_all': '_onAddAllBtn',
        'click #add_to_cart': 'add_look_cart',
        'mouseover .img_hotspot_carousel': 'get_tooltip',
        'mouseover .tooltip_carousel': 'in_tooltip',
        'mouseout .img_hotspot_carousel': 'out_tooltip',
        'mouseout .tooltip_carousel': 'vanish_tooltip',


    }),


    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAddCartJSON: function (ev) {
        this.onClickAddCartJSON(ev);
    },
    get_tooltip: function (ev) {
        var width = $('.o_carousel_product_outer').width()
        // var height = $('.o_carousel_product_outer').hight()
        var child_top = $(ev.currentTarget).parents('.hot-spot').css('top')
        var par_top = $(ev.currentTarget).parents('.hot-spot').parent().height()
        var top = (parseFloat(child_top.replace('px', '')) / parseInt(par_top)) * 100

        var child_left = $(ev.currentTarget).parents('.hot-spot').css('left')
        var par_left = $(ev.currentTarget).parents('.hot-spot').parent().width()
        var left = (parseFloat(child_left.replace('px', '')) / parseInt(par_left)) * 100

        if (top > 55.73747) {
            $(ev.currentTarget).siblings('.tooltip').css('margin-top', '-228px')
        }
        if (left > 78) {
            $(ev.currentTarget).siblings('.tooltip').css({
                'margin-left': '-173px',
            })
        }
        if (left < 15) {
            $(ev.currentTarget).siblings('.tooltip').css({
                'margin-left': '4px',
            })
        }


        $(ev.currentTarget).siblings('.tooltip').css('display', 'block')
    },
    out_tooltip: function (ev) {
        $(ev.currentTarget).siblings('.tooltip').css('display', 'none')
    },
    in_tooltip: function (ev) {
        $(ev.currentTarget).css('display', 'block')
    },
    vanish_tooltip: function (ev) {
        $(ev.currentTarget).css('display', 'none')
    },


    add_look_cart: function (ev) {
        var self = this;
        var qty = $('#prod_qty').val()
        if (qty < 1) {
            $("#add_to_cart").attr('disabled', 'disabled');
            ev.preventDefault();
            ev.stopPropagation();
        } else {
            $("#add_to_cart").prop("disabled", false);
        }
        this._onChangeModalQty(ev)
    },

    _onChangeModalQty: function (ev) {
        var self = this;
        // var products = $(ev.currentTarget).closest('.modal').find('.modal_carousel_product :selected')
        var products = $('.shop_look_modal').find('.modal_carousel_product :selected')
        var qty = parseInt($("#modal_qty").val());

        if (modal_qty <= 0) {
            $("#add_all").attr('disabled', 'disabled');
        }
        else {
            $("#add_all").prop("disabled", false);
        }
        products.each(function (index, value) {
            var product_id = parseInt(value.value);
            var combination = value.dataset.combination ? JSON.parse(value.dataset.combination) : [];
            var product_template_id = parseInt(value.getAttribute('tmpl_id'));
            var pricelist_id = parseInt($('.current_pricelist').val())
            return rpc('/website_sale/get_combination_info', {
                'product_template_id': product_template_id,
                'product_id': product_id,
                'combination': combination,
                'add_qty': qty,
                'pricelist_id': pricelist_id || false,
            }).then((combinationData, ev) => {
                self.onChangeAddQuantity(ev, combinationData);
            });
        });

    },


    onChangeAddQuantity: function (ev, combinationData) {

        var price = this._priceToStr(combinationData.price)
        var option = $(`.modal_product_options_details[data-id='${combinationData.product_template_id}']`);
        $(option).find('.oe_currency_value').text(price)
    },


    _onChangeVariantSelect: function (ev) {
        var self = this;
        var $selected_option_price = $(ev.target).find(":selected").attr("price");
        var price = this._priceToStr(parseInt($selected_option_price))
        $(ev.target).parent().find('.oe_currency_value').text(price)
        self.handleCustomValues($(ev.target));
    },

    _onChangeitemsToAdd: function (ev) {
        var self = this;
        var $selected_option = $(ev.target).find(":selected")
        var $selected_variant = $(ev.target).find(":selected").attr("value");
        var $selected_template = $(ev.target).find(":selected").attr("tmpl_id");
        var $selected_combination = $selected_option.attr("data-combination") ? JSON.parse($selected_option.attr("data-combination")) : [];
        var qty = parseInt($("#modal_qty").val());

        return rpc('/website_sale/get_combination_info', {
            'product_template_id': $selected_template,
            'product_id': $selected_variant,
            'combination': $selected_combination,
            'add_qty': qty,
            'pricelist_id': this.pricelistId || false,
        }).then((combinationData, ev) => {
            self.onChangeAddQuantity(ev, combinationData);
        });
        // $(ev.target).parent().find('.oe_currency_value').text($selected_option)
    },

    _onAddToCartBtn: async function (ev) {
        try {
            const id = parseInt($(ev.currentTarget).parent().find('.variant_select').val());

            if (id > 0) {
                const customAttributeValues = this.getCustomVariantValues($(ev.currentTarget).parent());
                const response = await rpc("/shop/cart/update_json",{
                        product_id: id,
                        add_qty: 1,
                        product_custom_attribute_values: JSON.stringify(customAttributeValues)
                    },
                );

                const cartQuantity = parseInt($(".my_cart_quantity").text());
                if (response.cart_quantity && response.cart_quantity !== cartQuantity) {
                    const imageWidth = $('div[data-image_width]').data('image_width');
                    if (imageWidth !== 'none') {
                        await wSaleUtils.animateClone($('header .o_wsale_my_cart').first(), $(ev.target).closest('.product_options_content'), 25, 40);
                    }
                    updateCartNavBar(response);
                }
            }
        } catch (error) {
            console.error("An error occurred:", error);
        }
    },


    _onAddAllBtn: function () {
        const ids = [];
        var qty = parseInt($("#modal_qty").val());
        $(".items_to_add").each(function () {
            var id = $(this).find(":selected").val();
            ids.push(parseInt(id))
        });
        const uniq = [...new Set(ids)];
        try {
            if (ids && (qty > 0)) {
                $(this).prop("disabled", false);
                rpc("/shop/look/cart/update", { "product_id": uniq, "add_qty": qty })
                    .then(function (res) {
                        window.location.reload();
                    })
            }
            else {
                $(this).attr('disabled', 'disabled');
            }

        }
        catch (e) { }


    },

    getCustomVariantValues: function ($container) {
        var variantCustomValues = [];
        $container.find('.variant_custom_value').each(function () {
            var $variantCustomValueInput = $(this);
            if ($variantCustomValueInput.length !== 0) {
                variantCustomValues.push({
                    'custom_product_template_attribute_value_id': $variantCustomValueInput.data('custom_product_template_attribute_value_id'),
                    'attribute_value_name': $variantCustomValueInput.data('attribute_value_name'),
                    'custom_value': $variantCustomValueInput.val(),
                });
            }
        });

        return variantCustomValues;
    },

    handleCustomValues: function ($target) {
        var $variantContainer;
        var $customInput = false;
        if ($target.is('select')) {
            $variantContainer = $target.closest('select');
            $customInput = $target
                .find('option[value="' + $target.val() + '"]');
        }
        $('.variant_custom_value').remove()

        if ($variantContainer) {
            if ($customInput && $customInput.data('is_custom') === 'True') {
                var attributeValueId = $customInput.data('value_id');
                var attributeValueName = $customInput.data('value_name');


                if ($variantContainer.find('.variant_custom_value').length === 0
                    || $variantContainer
                        .find('.variant_custom_value')
                        .data('custom_product_template_attribute_value_id') !== parseInt(attributeValueId)) {
                    $variantContainer.find('.variant_custom_value').remove();
                    $('.variant_custom_value').remove()

                    const previousCustomValue = $customInput.attr("previous_custom_value");
                    var $input = $('<input>', {
                        type: 'text',
                        'data-custom_product_template_attribute_value_id': attributeValueId,
                        'data-attribute_value_name': attributeValueName,
                        class: 'variant_custom_value form-control'
                    });

                    $input.attr('placeholder', attributeValueName);
                    $input.addClass('custom_value_radio');
                    $variantContainer.after($input);
                    if (previousCustomValue) {
                        $input.val(previousCustomValue);
                    }
                    $input[0].focus();
                }
            } else {
                $variantContainer.find('.variant_custom_value').remove();
            }
        }
    },

});


/**
 * Updates both navbar cart
 * @param {Object} data
 */
function updateCartNavBar(data) {
    $(".my_cart_quantity")
        .parents('li.o_wsale_my_cart').removeClass('d-none').end()
        .addClass('o_mycart_zoom_animation').delay(300)
        .queue(function () {
            $(this)
                .toggleClass('fa fa-warning', !data.cart_quantity)
                .attr('title', data.warning)
                .text(data.cart_quantity || '')
                .removeClass('o_mycart_zoom_animation')
                .dequeue();
        });

    $(".js_cart_lines").first().before(data['website_sale.cart_lines']).end().remove();
    $(".js_cart_summary").replaceWith(data['website_sale.short_cart_summary']);
}
