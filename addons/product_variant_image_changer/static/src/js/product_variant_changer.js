/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";

document.addEventListener('DOMContentLoaded', function() {
    
    // Verificar si estamos en una página de producto
    const productDetails = document.getElementById('product_details');
    if (!productDetails) return;

    const productId = productDetails.dataset.productId;
    const currentVariantId = productDetails.dataset.currentVariantId;

    // Elementos del DOM
    const variantThumbnails = document.querySelectorAll('.variant_image_thumbnail');
    const mainProductImage = document.querySelector('.product_detail_img img');
    const priceContainer = document.getElementById('product_price_container');
    const selectedVariantInfo = document.getElementById('selected_variant_info');
    const selectedVariantName = document.getElementById('selected_variant_name');

    // Estado actual
    let currentSelectedVariant = currentVariantId;

    /**
     * Actualiza la imagen principal del producto
     */
    function updateMainImage(imageUrl, variantName) {
        if (mainProductImage && imageUrl) {
            mainProductImage.src = imageUrl;
            mainProductImage.alt = variantName || 'Imagen del producto';
            
            // Agregar efecto de transición
            mainProductImage.style.opacity = '0.5';
            setTimeout(() => {
                mainProductImage.style.opacity = '1';
            }, 150);
        }
    }

    /**
     * Actualiza el precio del producto
     */
    function updatePrice(formattedPrice) {
        if (priceContainer && formattedPrice) {
            const priceElement = priceContainer.querySelector('.oe_price, .product_price');
            if (priceElement) {
                priceElement.textContent = formattedPrice;
            }
        }
    }

    /**
     * Actualiza la información de la variante seleccionada
     */
    function updateSelectedVariantInfo(variantName) {
        if (selectedVariantInfo && selectedVariantName && variantName) {
            selectedVariantName.textContent = variantName;
            selectedVariantInfo.style.display = 'block';
        }
    }

    /**
     * Actualiza el estado visual de las miniaturas
     */
    function updateThumbnailsState(selectedVariantId) {
        variantThumbnails.forEach(thumbnail => {
            const variantId = thumbnail.dataset.variantId;
            const img = thumbnail.querySelector('img');
            
            if (variantId === selectedVariantId) {
                thumbnail.classList.add('selected');
                img.classList.add('border-primary');
                img.classList.remove('border');
            } else {
                thumbnail.classList.remove('selected');
                img.classList.remove('border-primary');
                img.classList.add('border');
            }
        });
    }

    /**
     * Maneja el clic en una miniatura de variante
     */
    async function handleVariantClick(variantId, imageUrl) {
        if (variantId === currentSelectedVariant) return;

        try {
            // Mostrar indicador de carga
            const loadingIndicator = document.createElement('div');
            loadingIndicator.className = 'loading-overlay';
            loadingIndicator.innerHTML = '<i class="fa fa-spinner fa-spin"></i>';
            document.body.appendChild(loadingIndicator);

            // Llamada AJAX para obtener información de la variante
            const response = await jsonrpc('/shop/product/get_variant_info', {
                variant_id: parseInt(variantId)
            });

            // Remover indicador de carga
            document.body.removeChild(loadingIndicator);

            if (response.success) {
                // Actualizar imagen principal
                updateMainImage(response.main_image_url, response.name);
                
                // Actualizar precio
                updatePrice(response.formatted_price);
                
                // Actualizar información de variante
                updateSelectedVariantInfo(response.name);
                
                // Actualizar estado de miniaturas
                updateThumbnailsState(variantId);
                
                // Actualizar estado actual
                currentSelectedVariant = variantId;

                // Disparar evento personalizado para otros módulos
                const event = new CustomEvent('variantChanged', {
                    detail: {
                        variantId: variantId,
                        variantData: response
                    }
                });
                document.dispatchEvent(event);

                // Actualizar URL si es posible (opcional)
                if (history.pushState) {
                    const newUrl = window.location.pathname + '?variant=' + variantId;
                    history.pushState({variantId: variantId}, '', newUrl);
                }

            } else {
                console.error('Error al obtener información de la variante:', response.error);
                showErrorMessage('Error al cargar la variante. Por favor, intenta de nuevo.');
            }

        } catch (error) {
            console.error('Error en la llamada AJAX:', error);
            showErrorMessage('Error de conexión. Por favor, verifica tu conexión a internet.');
        }
    }

    /**
     * Muestra un mensaje de error al usuario
     */
    function showErrorMessage(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(errorDiv, container.firstChild);

        // Auto-remover después de 5 segundos
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 5000);
    }

    /**
     * Inicializa los event listeners
     */
    function initializeEventListeners() {
        variantThumbnails.forEach(thumbnail => {
            thumbnail.addEventListener('click', function(e) {
                e.preventDefault();
                const variantId = this.dataset.variantId;
                const imageUrl = this.dataset.imageUrl;
                
                if (variantId) {
                    handleVariantClick(variantId, imageUrl);
                }
            });

            // Agregar efecto hover
            thumbnail.addEventListener('mouseenter', function() {
                this.querySelector('img').style.transform = 'scale(1.05)';
            });

            thumbnail.addEventListener('mouseleave', function() {
                this.querySelector('img').style.transform = 'scale(1)';
            });
        });
    }

    /**
     * Inicializa el estado inicial
     */
    function initializeState() {
        if (currentSelectedVariant) {
            updateThumbnailsState(currentSelectedVariant);
        }

        // Verificar si hay un parámetro de variante en la URL
        const urlParams = new URLSearchParams(window.location.search);
        const variantParam = urlParams.get('variant');
        
        if (variantParam && variantParam !== currentSelectedVariant) {
            const thumbnail = document.querySelector(`[data-variant-id="${variantParam}"]`);
            if (thumbnail) {
                handleVariantClick(variantParam, thumbnail.dataset.imageUrl);
            }
        }
    }

    // Inicializar el módulo
    if (variantThumbnails.length > 0) {
        initializeEventListeners();
        initializeState();
        
        console.log('Product Variant Image Changer initialized successfully');
    }

    // Manejar navegación del historial
    window.addEventListener('popstate', function(event) {
        if (event.state && event.state.variantId) {
            const thumbnail = document.querySelector(`[data-variant-id="${event.state.variantId}"]`);
            if (thumbnail) {
                handleVariantClick(event.state.variantId, thumbnail.dataset.imageUrl);
            }
        }
    });

});

