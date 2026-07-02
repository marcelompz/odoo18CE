// Product Image Hover and Variant Selection
(function() {
    'use strict';
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    function init() {
        // Initialize hover effects for product cards
        initializeProductHover();
        initializeVariantButtons();
        
        // Initialize variant selection from URL parameters (for product detail page)
        initializeVariantSelectionFromURL();
        
        // Initialize dynamic variant selectors for carousels
        initializeDynamicVariantSelectors();
        
        // Initialize unavailable combinations (with error handling)
        try {
            initializeUnavailableCombinations();
        } catch (e) {
            console.warn('Could not initialize unavailable combinations:', e);
        }
        
        // Re-initialize when new content is loaded
        var observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) {
                        if (node.classList && (node.classList.contains('oe_product_cart') || node.classList.contains('o_carousel_product_card'))) {
                            initializeProductHover();
                            initializeDynamicVariantSelectors();
                            try {
                                initializeUnavailableCombinations();
                            } catch (e) {
                                console.warn('Could not initialize unavailable combinations for new content:', e);
                            }
                        }
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
    function initializeProductHover() {
        var productCards = document.querySelectorAll('.oe_product_cart, .o_carousel_product_card');
        
        productCards.forEach(function(productCard) {
            var hoverImage = productCard.querySelector('.oe_product_image_hover');
            
            if (hoverImage) {
                // Mouse enter
                productCard.addEventListener('mouseenter', function() {
                    if (hoverImage.dataset.src && !hoverImage.src) {
                        hoverImage.src = hoverImage.dataset.src;
                    }
                    productCard.classList.add('product-hover');
                });
                
                // Mouse leave
                productCard.addEventListener('mouseleave', function() {
                    productCard.classList.remove('product-hover');
                });
            }
        });
    }
    
    function initializeVariantButtons() {
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('size-btn') || e.target.classList.contains('color-btn')) {
                e.preventDefault();
                e.stopPropagation();
                
                var variantBtn = e.target;
                var productCard = variantBtn.closest('.oe_product_cart, .o_carousel_product_card');
                var attribute = variantBtn.getAttribute('data-attribute');
                var value = variantBtn.getAttribute('data-value');
                var valueId = variantBtn.getAttribute('data-value-id');
                var displayType = variantBtn.getAttribute('data-display-type');
                
                // Remove active class from all buttons in this attribute group
                var attributeGroup = variantBtn.closest('.attribute-group');
                if (attributeGroup) {
                    var buttons = attributeGroup.querySelectorAll('.size-btn, .color-btn');
                    buttons.forEach(function(btn) {
                        btn.classList.remove('active');
                    });
                }
                
                // Add active class to clicked button
                variantBtn.classList.add('active');
                
                // Show feedback
                showVariantSelectionFeedback(productCard, attribute, value);
                
                // Log selection (for debugging)
                console.log('Selected variant:', attribute, '=', value, 'Value ID:', valueId, 'Display Type:', displayType);
                
                // Check if all attributes are selected before redirecting
                checkAndRedirectIfAllSelected(productCard, valueId);
            }
        });
    }
    
    function checkAndRedirectIfAllSelected(productCard, selectedValueId) {
        var sizeSelector = productCard.querySelector('.size-selector');
        if (!sizeSelector) {
            // If no size selector, redirect immediately
            redirectToProductWithVariant(productCard, selectedValueId);
            return;
        }
        
        var totalAttributes = parseInt(sizeSelector.getAttribute('data-total-attributes')) || 0;
        var selectedButtons = productCard.querySelectorAll('.size-btn.active, .color-btn.active');
        
        console.log('Total attributes:', totalAttributes, 'Selected:', selectedButtons.length);
        
        // If all attributes are selected, check combination availability
        if (selectedButtons.length >= totalAttributes && totalAttributes > 0) {
            // Check if combination validation is enabled (fallback to direct redirect if not)
            var productId = sizeSelector.getAttribute('data-product-id');
            if (productId) {
                checkCombinationAvailability(productCard, selectedValueId);
            } else {
                // No product ID, redirect directly
                redirectToProductWithVariant(productCard, selectedValueId);
            }
        } else {
            // Show message indicating more selections needed
            showSelectionProgress(productCard, selectedButtons.length, totalAttributes);
        }
    }
    
    function checkCombinationAvailability(productCard, selectedValueId) {
        var sizeSelector = productCard.querySelector('.size-selector');
        var productId = sizeSelector.getAttribute('data-product-id');
        
        // Get all selected attributes
        var selectedAttributes = [];
        var selectedButtons = productCard.querySelectorAll('.size-btn.active, .color-btn.active');
        
        selectedButtons.forEach(function(btn) {
            selectedAttributes.push({
                attribute: btn.getAttribute('data-attribute'),
                value: btn.getAttribute('data-value')
            });
        });
        
        // Check combination availability via AJAX
        if (productId && selectedAttributes.length > 0) {
            // Show loading state
            showLoadingState(productCard);
            
            // Make AJAX call to check combination
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/fuap/check_variant_combination', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            
            // Set timeout for the request
            xhr.timeout = 5000; // 5 seconds
            
            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4) {
                    hideLoadingState(productCard);
                    
                    if (xhr.status === 200) {
                        try {
                            var response = JSON.parse(xhr.responseText);
                            if (response.success) {
                                if (response.available) {
                                    // Combination is available, redirect to product
                                    redirectToProductWithVariant(productCard, selectedValueId);
                                } else {
                                    // Combination is not available, show error
                                    showUnavailableCombinationError(productCard, selectedAttributes);
                                }
                            } else {
                                console.error('Error checking combination:', response.error);
                                // Fallback: redirect anyway
                                redirectToProductWithVariant(productCard, selectedValueId);
                            }
                        } catch (e) {
                            console.error('Error parsing response:', e);
                            // Fallback: redirect anyway
                            redirectToProductWithVariant(productCard, selectedValueId);
                        }
                    } else {
                        console.error('AJAX error:', xhr.status);
                        // Fallback: redirect anyway
                        redirectToProductWithVariant(productCard, selectedValueId);
                    }
                }
            };
            
            xhr.ontimeout = function() {
                hideLoadingState(productCard);
                console.error('Request timeout');
                // Fallback: redirect anyway
                redirectToProductWithVariant(productCard, selectedValueId);
            };
            
            xhr.onerror = function() {
                hideLoadingState(productCard);
                console.error('Network error');
                // Fallback: redirect anyway
                redirectToProductWithVariant(productCard, selectedValueId);
            };
            
            try {
                xhr.send(JSON.stringify({
                    product_id: productId,
                    selected_attributes: selectedAttributes
                }));
            } catch (e) {
                hideLoadingState(productCard);
                console.error('Error sending request:', e);
                // Fallback: redirect anyway
                redirectToProductWithVariant(productCard, selectedValueId);
            }
        } else {
            // No product ID or no attributes, redirect anyway
            redirectToProductWithVariant(productCard, selectedValueId);
        }
    }
    
    function showUnavailableCombinationError(productCard, selectedAttributes) {
        var errorMessage = document.createElement('div');
        errorMessage.textContent = 'Combinación no disponible';
        errorMessage.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #dc3545;
            color: #fff;
            padding: 10px 20px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s ease;
            font-family: 'Inter', sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            text-align: center;
            max-width: 200px;
            word-wrap: break-word;
        `;
        
        productCard.style.position = 'relative';
        productCard.appendChild(errorMessage);
        
        // Animate in
        setTimeout(function() {
            errorMessage.style.opacity = '1';
        }, 10);
        
        // Remove after delay
        setTimeout(function() {
            errorMessage.style.opacity = '0';
            setTimeout(function() {
                if (errorMessage.parentNode) {
                    errorMessage.parentNode.removeChild(errorMessage);
                }
            }, 300);
        }, 3000);
    }
    
    function showLoadingState(productCard) {
        var loadingMessage = document.createElement('div');
        loadingMessage.textContent = 'Verificando disponibilidad...';
        loadingMessage.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #007bff;
            color: #fff;
            padding: 10px 20px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s ease;
            font-family: 'Inter', sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            text-align: center;
            max-width: 200px;
            word-wrap: break-word;
        `;
        
        productCard.style.position = 'relative';
        productCard.appendChild(loadingMessage);
        
        // Animate in
        setTimeout(function() {
            loadingMessage.style.opacity = '1';
        }, 10);
        
        // Store reference for removal
        productCard._loadingMessage = loadingMessage;
    }
    
    function hideLoadingState(productCard) {
        if (productCard._loadingMessage) {
            productCard._loadingMessage.style.opacity = '0';
            setTimeout(function() {
                if (productCard._loadingMessage && productCard._loadingMessage.parentNode) {
                    productCard._loadingMessage.parentNode.removeChild(productCard._loadingMessage);
                }
                productCard._loadingMessage = null;
            }, 300);
        }
    }
    
    function initializeUnavailableCombinations() {
        // Get all product cards with size selectors
        var productCards = document.querySelectorAll('.oe_product_cart, .o_carousel_product_card');
        
        productCards.forEach(function(productCard) {
            var sizeSelector = productCard.querySelector('.size-selector');
            if (sizeSelector) {
                var productId = sizeSelector.getAttribute('data-product-id');
                if (productId) {
                    // Get unavailable combinations via AJAX
                    getUnavailableCombinations(productCard, productId);
                }
            }
        });
    }
    
    function getUnavailableCombinations(productCard, productId) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/fuap/get_unavailable_combinations', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        
        // Set timeout for the request
        xhr.timeout = 5000; // 5 seconds
        
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    try {
                        var response = JSON.parse(xhr.responseText);
                        if (response.success) {
                            markUnavailableButtons(productCard, response.unavailable_combinations);
                        } else {
                            console.error('Error getting unavailable combinations:', response.error);
                        }
                    } catch (e) {
                        console.error('Error parsing unavailable combinations response:', e);
                    }
                } else {
                    console.error('AJAX error getting unavailable combinations:', xhr.status);
                }
            }
        };
        
        xhr.ontimeout = function() {
            console.error('Request timeout getting unavailable combinations');
        };
        
        xhr.onerror = function() {
            console.error('Network error getting unavailable combinations');
        };
        
        try {
            xhr.send(JSON.stringify({
                product_id: productId
            }));
        } catch (e) {
            console.error('Error sending request for unavailable combinations:', e);
        }
    }
    
    function markUnavailableButtons(productCard, unavailableCombinations) {
        var sizeSelector = productCard.querySelector('.size-selector');
        if (!sizeSelector) return;
        
        // Get all buttons
        var buttons = sizeSelector.querySelectorAll('.size-btn, .color-btn');
        
        // For each unavailable combination, mark the corresponding buttons
        unavailableCombinations.forEach(function(combination) {
            var unavailableAttributes = combination.attributes;
            
            buttons.forEach(function(button) {
                var buttonAttribute = button.getAttribute('data-attribute');
                var buttonValue = button.getAttribute('data-value');
                
                // Check if this button is part of an unavailable combination
                if (unavailableAttributes[buttonAttribute] && 
                    unavailableAttributes[buttonAttribute].value_name === buttonValue) {
                    
                    // Create unavailable message
                    var unavailableMessage = 'No disponible con: ';
                    var otherAttributes = [];
                    
                    for (var attrName in unavailableAttributes) {
                        if (attrName !== buttonAttribute) {
                            otherAttributes.push(attrName + ': ' + unavailableAttributes[attrName].value_name);
                        }
                    }
                    
                    unavailableMessage += otherAttributes.join(', ');
                    
                    // Mark button as disabled
                    button.classList.add('disabled');
                    button.setAttribute('data-unavailable-message', unavailableMessage);
                    button.style.pointerEvents = 'none';
                }
            });
        });
    }
    
    function showSelectionProgress(productCard, selectedCount, totalCount) {
        var progressMessage = document.createElement('div');
        progressMessage.textContent = `Selecciona ${totalCount - selectedCount} atributo${totalCount - selectedCount > 1 ? 's' : ''} más`;
        progressMessage.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #000;
            color: #fff;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s ease;
            font-family: 'Inter', sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        `;
        
        productCard.style.position = 'relative';
        productCard.appendChild(progressMessage);
        
        // Animate in
        setTimeout(function() {
            progressMessage.style.opacity = '1';
        }, 10);
        
        // Remove after delay
        setTimeout(function() {
            progressMessage.style.opacity = '0';
            setTimeout(function() {
                if (progressMessage.parentNode) {
                    progressMessage.parentNode.removeChild(progressMessage);
                }
            }, 300);
        }, 2000);
    }
    
    function initializeDynamicVariantSelectors() {
        // Buscar todos los carruseles de productos que no tienen selectores de variantes
        var carouselCards = document.querySelectorAll('.o_carousel_product_card');
        
        carouselCards.forEach(function(card) {
            // Verificar si ya tiene selectores de variantes
            if (!card.querySelector('.size-selector')) {
                // Buscar el mejor lugar para insertar los selectores
                var insertTarget = card.querySelector('.card-body') || 
                                 card.querySelector('.product_price') || 
                                 card.querySelector('.oe_product_cart') ||
                                 card;
                
                if (insertTarget) {
                    // Crear el selector de variantes dinámicamente
                    var variantSelector = document.createElement('div');
                    variantSelector.className = 'size-selector';
                    variantSelector.setAttribute('data-total-attributes', '1');
                    variantSelector.innerHTML = `
                        <div class="attribute-group">
                            <div class="attribute-label">Variantes</div>
                            <div class="attribute-values">
                                <button class="size-btn" data-attribute="Talla" data-value="S" data-value-id="1" data-display-type="select">S</button>
                                <button class="size-btn" data-attribute="Talla" data-value="M" data-value-id="2" data-display-type="select">M</button>
                                <button class="size-btn" data-attribute="Talla" data-value="L" data-value-id="3" data-display-type="select">L</button>
                                <button class="size-btn" data-attribute="Talla" data-value="XL" data-value-id="4" data-display-type="select">XL</button>
                            </div>
                        </div>
                    `;
                    
                    insertTarget.appendChild(variantSelector);
                }
            }
        });
    }
    
    function initializeVariantSelectionFromURL() {
        // Check if we're on a product detail page
        if (window.location.pathname.includes('/shop/') && !window.location.pathname.endsWith('/shop')) {
            // Get attribute_values from URL hash
            var hash = window.location.hash;
            if (hash && hash.includes('attribute_values=')) {
                var attributeValues = hash.split('attribute_values=')[1];
                if (attributeValues) {
                    var valueIds = attributeValues.split(',');
                    console.log('Found attribute_values in URL hash:', valueIds);
                    
                    // Wait a bit for the page to load completely
                    setTimeout(function() {
                        selectVariantsFromURL(valueIds);
                    }, 1000);
                }
            }
        }
    }
    
    function selectVariantsFromURL(valueIds) {
        // Find all variant selectors on the product page
        var variantSelectors = document.querySelectorAll('input[name*="attribute"], select[name*="attribute"]');
        
        if (variantSelectors.length === 0) {
            console.log('No variant selectors found on page');
            return;
        }
        
        console.log('Found variant selectors:', variantSelectors.length);
        
        valueIds.forEach(function(valueId) {
            // Try to find the corresponding variant selector
            variantSelectors.forEach(function(selector) {
                var options = selector.querySelectorAll('option');
                options.forEach(function(option) {
                    if (option.value == valueId) {
                        console.log('Selecting variant:', option.text, 'with value:', valueId);
                        selector.value = valueId;
                        
                        // Trigger change event to update the page
                        var event = new Event('change', { bubbles: true });
                        selector.dispatchEvent(event);
                    }
                });
            });
        });
        
        // Also try to find and click radio buttons or checkboxes
        valueIds.forEach(function(valueId) {
            var radioButtons = document.querySelectorAll('input[type="radio"][value="' + valueId + '"]');
            radioButtons.forEach(function(radio) {
                console.log('Selecting radio button:', radio);
                radio.checked = true;
                radio.click();
            });
        });
    }
    
    function redirectToProductWithVariant(productCard, selectedValueId) {
        // Get product URL from the product card
        var productLink = productCard.querySelector('a[href*="/shop/"]');
        if (!productLink) {
            // Try to find any link in the product card
            productLink = productCard.querySelector('a');
        }
        
        if (productLink) {
            var productUrl = productLink.href;
            
            // Get all selected variants from this product card
            var selectedVariants = [];
            var allButtons = productCard.querySelectorAll('.size-btn.active, .color-btn.active');
            
            allButtons.forEach(function(btn) {
                var valueId = btn.getAttribute('data-value-id');
                if (valueId) {
                    selectedVariants.push(valueId);
                }
            });
            
            // If no variants are selected, just use the clicked one
            if (selectedVariants.length === 0 && selectedValueId) {
                selectedVariants.push(selectedValueId);
            }
            
            // Build the URL with variant parameters using hash (#)
            if (selectedVariants.length > 0) {
                // Remove any existing hash from the URL
                var baseUrl = productUrl.split('#')[0];
                var variantParam = 'attribute_values=' + selectedVariants.join(',');
                var finalUrl = baseUrl + '#' + variantParam;
                
                console.log('Redirecting to product with variants:', selectedVariants);
                
                // Redirect to product page with selected variants
                window.location.href = finalUrl;
            } else {
                // If no variants selected, just go to product page
                window.location.href = productUrl;
            }
        }
    }
    
    function showVariantSelectionFeedback(productCard, attribute, value) {
        var feedback = document.createElement('div');
        feedback.textContent = attribute + ': ' + value + ' seleccionado';
        feedback.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #000;
            color: #fff;
            padding: 10px 20px;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 600;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s ease;
            font-family: 'Inter', sans-serif;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            text-align: center;
            max-width: 200px;
            word-wrap: break-word;
        `;
        
        productCard.style.position = 'relative';
        productCard.appendChild(feedback);
        
        // Animate in
        setTimeout(function() {
            feedback.style.opacity = '1';
        }, 10);
        
        // Remove after delay
        setTimeout(function() {
            feedback.style.opacity = '0';
            setTimeout(function() {
                if (feedback.parentNode) {
                    feedback.parentNode.removeChild(feedback);
                }
            }, 300);
        }, 1500);
    }
})(); 