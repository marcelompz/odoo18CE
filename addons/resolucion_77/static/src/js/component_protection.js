/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ExportDataDialog } from "@web/views/view_dialogs/export_data_dialog";

/**
 * Patch para ExportDataDialog para prevenir errores "Component is destroyed"
 * específico para el módulo resolucion_77
 */
patch(ExportDataDialog.prototype, {
    
    /**
     * Override setup para agregar protecciones contra component destruction
     */
    setup() {
        super.setup();
        
        // Flag para verificar si el componente está montado
        this._isMounted = false;
        this._isDestroying = false;
        
        // Agregar listener para detectar cuando el componente se monta
        this.onMounted(() => {
            this._isMounted = true;
            this._isDestroying = false;
        });
        
        // Agregar listener para cleanup antes de destruir
        this.onWillUnmount(() => {
            this._isDestroying = true;
            this._isMounted = false;
            
            // Cancelar cualquier operación pendiente
            this._cancelPendingOperations();
        });
    },

    /**
     * Override del método searchRead para agregar verificaciones de estado
     */
    async _searchRead(...args) {
        // Verificar si el componente está en proceso de destrucción
        if (this._isDestroying || !this._isMounted) {
            console.warn("Resolucion77: Operación searchRead cancelada - Componente destruido");
            return [];
        }

        try {
            // Llamar al método original con protección
            const result = await super._searchRead?.(...args);
            
            // Verificar nuevamente después de la operación asíncrona
            if (this._isDestroying || !this._isMounted) {
                console.warn("Resolucion77: Resultado searchRead descartado - Componente destruido durante operación");
                return [];
            }
            
            return result;
        } catch (error) {
            // Log específico para errores relacionados con component destruction
            if (error.message && error.message.includes("destroyed")) {
                console.warn("Resolucion77: Error de componente destruido capturado:", error.message);
                return [];
            }
            throw error;
        }
    },

    /**
     * Override del método _updateExportFields para mayor protección
     */
    async _updateExportFields() {
        if (this._isDestroying || !this._isMounted) {
            console.warn("Resolucion77: _updateExportFields cancelado - Componente destruido");
            return;
        }

        try {
            return await super._updateExportFields?.();
        } catch (error) {
            if (error.message && error.message.includes("destroyed")) {
                console.warn("Resolucion77: Error en _updateExportFields capturado:", error.message);
                return;
            }
            throw error;
        }
    },

    /**
     * Cancelar operaciones pendientes cuando el componente se destruye
     */
    _cancelPendingOperations() {
        // Si hay operaciones RPC pendientes, intentar cancelarlas
        if (this.rpc && typeof this.rpc.abort === 'function') {
            try {
                this.rpc.abort();
            } catch (e) {
                // Ignorar errores de abort
            }
        }
        
        // Limpiar cualquier timeout o interval
        if (this._timeouts) {
            this._timeouts.forEach(clearTimeout);
            this._timeouts = [];
        }
        
        if (this._intervals) {
            this._intervals.forEach(clearInterval);
            this._intervals = [];
        }
    },

    /**
     * Helper para agregar timeouts con cleanup automático
     */
    _safeSetTimeout(callback, delay) {
        if (!this._timeouts) {
            this._timeouts = [];
        }
        
        const timeoutId = setTimeout(() => {
            if (!this._isDestroying && this._isMounted) {
                callback();
            }
            // Remover del array de timeouts
            const index = this._timeouts.indexOf(timeoutId);
            if (index > -1) {
                this._timeouts.splice(index, 1);
            }
        }, delay);
        
        this._timeouts.push(timeoutId);
        return timeoutId;
    },

    /**
     * Helper para verificar si es seguro ejecutar operaciones
     */
    _isSafeToExecute() {
        return this._isMounted && !this._isDestroying && !this.__owl__.isDestroyed;
    }
});

/**
 * Utilidad para crear wrappers seguros para métodos que usan RPC
 */
export function createSafeRpcWrapper(originalMethod, context) {
    return async function(...args) {
        // Verificar si el contexto (componente) está disponible y seguro
        if (!context || 
            (context._isDestroying) || 
            (context.__owl__ && context.__owl__.isDestroyed)) {
            console.warn("Resolucion77: Operación RPC cancelada - Contexto no seguro");
            return null;
        }

        try {
            const result = await originalMethod.apply(this, args);
            
            // Verificar nuevamente después de la operación
            if (context._isDestroying || 
                (context.__owl__ && context.__owl__.isDestroyed)) {
                console.warn("Resolucion77: Resultado RPC descartado - Contexto destruido durante operación");
                return null;
            }
            
            return result;
        } catch (error) {
            if (error.message && error.message.includes("destroyed")) {
                console.warn("Resolucion77: Error RPC por componente destruido:", error.message);
                return null;
            }
            throw error;
        }
    };
}

console.log("Resolucion77: Protecciones contra 'Component is destroyed' cargadas"); 