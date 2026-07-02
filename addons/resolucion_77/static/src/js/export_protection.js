/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

/**
 * Sistema de protección global para exportaciones del módulo Resolución 77
 */
class Resolucion77ExportProtection {
    constructor() {
        this.activeExports = new Map();
        this.exportTimeouts = new Map();
    }

    /**
     * Registrar una exportación activa
     */
    registerExport(exportId, component) {
        this.activeExports.set(exportId, {
            component: component,
            startTime: Date.now(),
            status: 'active'
        });

        // Auto-cleanup después de 5 minutos
        const timeoutId = setTimeout(() => {
            this.cleanupExport(exportId);
        }, 5 * 60 * 1000);

        this.exportTimeouts.set(exportId, timeoutId);
    }

    /**
     * Limpiar exportación
     */
    cleanupExport(exportId) {
        if (this.exportTimeouts.has(exportId)) {
            clearTimeout(this.exportTimeouts.get(exportId));
            this.exportTimeouts.delete(exportId);
        }
        
        if (this.activeExports.has(exportId)) {
            const exportData = this.activeExports.get(exportId);
            exportData.status = 'completed';
            this.activeExports.delete(exportId);
        }
    }

    /**
     * Verificar si una exportación está activa
     */
    isExportActive(exportId) {
        return this.activeExports.has(exportId) && 
               this.activeExports.get(exportId).status === 'active';
    }

    /**
     * Verificar si un componente es seguro para operaciones RPC
     */
    isComponentSafe(component) {
        if (!component) return false;
        
        // Verificaciones estándar
        if (component.__owl__ && component.__owl__.isDestroyed) return false;
        if (component._isDestroying) return false;
        if (!component._isMounted) return false;
        
        return true;
    }

    /**
     * Wrapper seguro para llamadas RPC
     */
    async safeRpcCall(component, rpcMethod, ...args) {
        const exportId = `${component.constructor.name}_${Date.now()}`;
        
        try {
            if (!this.isComponentSafe(component)) {
                console.warn(`Resolucion77: RPC cancelado - Componente no seguro (${exportId})`);
                return null;
            }

            this.registerExport(exportId, component);
            
            const result = await rpcMethod.apply(component, args);
            
            if (!this.isComponentSafe(component)) {
                console.warn(`Resolucion77: Resultado RPC descartado - Componente destruido (${exportId})`);
                return null;
            }

            this.cleanupExport(exportId);
            return result;

        } catch (error) {
            this.cleanupExport(exportId);
            
            if (error.message && error.message.includes("destroyed")) {
                console.warn(`Resolucion77: Error de componente destruido capturado (${exportId}):`, error.message);
                return null;
            }
            
            throw error;
        }
    }
}

// Crear instancia global
const exportProtection = new Resolucion77ExportProtection();

/**
 * Patch para la clase base Component para agregar protecciones automáticas
 */
registry.category("services").add("resolucion77_export_protection", {
    start() {
        return exportProtection;
    }
});

/**
 * Patch específico para botones de exportación
 */
patch(document, {
    addEventListener(type, listener, options) {
        if (type === 'click') {
            const originalListener = listener;
            const protectedListener = function(event) {
                // Verificar si es un botón de exportación del módulo
                const target = event.target;
                if (target && (
                    target.classList.contains('o_export_btn') ||
                    target.closest('.o_export_btn') ||
                    (target.textContent && target.textContent.includes('Exportar'))
                )) {
                    
                    // Prevenir clics múltiples
                    if (target.disabled || target.classList.contains('o_processing')) {
                        event.preventDefault();
                        event.stopPropagation();
                        return;
                    }
                    
                    // Marcar como procesando
                    target.classList.add('o_processing');
                    target.disabled = true;
                    
                    // Restaurar después de un tiempo razonable
                    setTimeout(() => {
                        target.classList.remove('o_processing');
                        target.disabled = false;
                    }, 10000); // 10 segundos
                }
                
                return originalListener.call(this, event);
            };
            
            return super.addEventListener(type, protectedListener, options);
        }
        
        return super.addEventListener(type, listener, options);
    }
});

/**
 * Función utilitaria para crear callbacks seguros
 */
export function createSafeCallback(callback, component) {
    return function(...args) {
        if (!exportProtection.isComponentSafe(component)) {
            console.warn("Resolucion77: Callback cancelado - Componente no seguro");
            return;
        }
        
        try {
            return callback.apply(this, args);
        } catch (error) {
            if (error.message && error.message.includes("destroyed")) {
                console.warn("Resolucion77: Error en callback por componente destruido:", error.message);
                return;
            }
            throw error;
        }
    };
}

/**
 * Función para crear promesas con timeout y cleanup automático
 */
export function createSafePromise(promiseFactory, component, timeout = 30000) {
    return new Promise((resolve, reject) => {
        if (!exportProtection.isComponentSafe(component)) {
            reject(new Error("Component is not safe for operation"));
            return;
        }

        const timeoutId = setTimeout(() => {
            reject(new Error("Operation timeout"));
        }, timeout);

        promiseFactory()
            .then(result => {
                clearTimeout(timeoutId);
                if (exportProtection.isComponentSafe(component)) {
                    resolve(result);
                } else {
                    console.warn("Resolucion77: Promise resultado descartado - Componente destruido");
                    resolve(null);
                }
            })
            .catch(error => {
                clearTimeout(timeoutId);
                if (error.message && error.message.includes("destroyed")) {
                    console.warn("Resolucion77: Promise error por componente destruido:", error.message);
                    resolve(null);
                } else {
                    reject(error);
                }
            });
    });
}

// Exportar la instancia de protección para uso en otros módulos
export { exportProtection };

console.log("Resolucion77: Sistema de protección de exportaciones inicializado"); 