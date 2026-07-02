// Script para deshabilitar el widget AddressForm problemático
// Se ejecuta inmediatamente para prevenir errores

(function() {
    'use strict';
    
    // Variable para evitar múltiples ejecuciones
    var isDisabled = false;
    
    function disableAddressForm() {
        if (isDisabled) {
            return;
        }
        
        // Verificar si odoo está disponible
        if (typeof window.odoo !== 'undefined' && window.odoo.define) {
            // Guardar la función original
            var originalDefine = window.odoo.define;
            
            // Reemplazar odoo.define
            window.odoo.define = function(name, dependencies, factory) {
                // Si es el widget de dirección problemático, deshabilitarlo
                if (name === 'website_sale.AddressForm' || 
                    name.includes('AddressForm') || 
                    name.includes('address')) {
                    
                    // Retornar un widget vacío que no hace nada
                    return originalDefine.call(this, name, [], function() {
                        'use strict';
                        
                        return {
                            selector: 'form.js_address_submit',
                            init: function () {
                                return;
                            },
                            start: function() {
                                return;
                            }
                        };
                    });
                }
                
                // Para otros widgets, usar el comportamiento original
                return originalDefine.apply(this, arguments);
            };
            
            isDisabled = true;
        } else {
            setTimeout(disableAddressForm, 100);
        }
    }
    
    // Ejecutar inmediatamente
    disableAddressForm();
    
    // También ejecutar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', disableAddressForm);
    }
    
    // También ejecutar cuando la ventana se cargue
    window.addEventListener('load', disableAddressForm);
    
})(); 