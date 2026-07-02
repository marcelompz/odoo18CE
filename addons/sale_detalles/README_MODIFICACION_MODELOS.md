# Funcionalidad de Modificación de Modelos en el Wizard

## Descripción

Se ha implementado una nueva funcionalidad en el wizard de agregar modelos que permite detectar automáticamente cuando se está modificando un modelo existente y **actualizar la imagen y la información** del modelo en lugar de eliminarlo completamente.

## Características Principales

### 1. Detección Automática de Modificaciones

- El wizard detecta automáticamente si ya existe un modelo del mismo tipo en la orden
- Cuando se detecta una modificación, se marca el campo `is_modification` como `True`
- Se pre-llenan los campos con la información del modelo existente

### 2. Modificación del Modelo Existente

- **NO se elimina** el modelo anterior, se **actualiza** con la nueva información
- Se reemplaza la imagen si se proporciona una nueva
- Se actualiza la cantidad y productos relacionados
- Se mantiene el historial completo del modelo

### 3. Interfaz de Usuario Mejorada

- Alerta informativa que indica cuando se detecta una modificación
- El botón cambia de "Agregar Modelo" a "Modificar Modelo"
- Se muestra información clara sobre la acción que se realizará

## Flujo de Trabajo

### Para Modelos Nuevos:

1. Usuario selecciona el tipo de modelo
2. Completa la información requerida
3. Hace clic en "Agregar Modelo"
4. Se crea el nuevo modelo en la orden

### Para Modificaciones:

1. Usuario selecciona un tipo de modelo que ya existe en la orden
2. El sistema detecta automáticamente que es una modificación
3. Se muestra una alerta informativa
4. Se pre-llenan los campos con la información existente
5. Usuario puede modificar la información según sea necesario
6. Al hacer clic en "Modificar Modelo":
   - Se **actualiza** el modelo existente con la nueva información
   - Se reemplaza la imagen si se proporciona una nueva
   - Se actualiza cantidad y productos relacionados
   - Se registra la modificación en el historial de diseño

## Campos Nuevos en el Wizard

- `is_modification`: Campo booleano que indica si es una modificación
- `existing_model_line_id`: Referencia al modelo existente que será modificado

## Historial de Diseño

Se crean registros detallados en el historial cuando se modifica un modelo:

1. **Registro de Modificación Principal**: Documenta todos los cambios realizados
2. **Registro de Cambio de Diseñador** (opcional): Si se cambia el diseñador asignado

### Información Registrada:

- Cambios en la imagen (actualizada o sin cambios)
- Cambios en la cantidad (valor anterior → valor nuevo)
- Cambios en productos relacionados
- Cambios en el diseñador asignado
- Fecha y hora de la modificación

## Ventajas de la Nueva Implementación

✅ **Preserva el historial** del modelo original  
✅ **Mantiene la trazabilidad** completa de cambios  
✅ **No pierde información** del modelo anterior  
✅ **Permite modificaciones incrementales**  
✅ **Registra todos los cambios** de manera detallada  
✅ **Mantiene la integridad** de los datos

## Consideraciones Importantes

- **Reversible**: Los cambios se pueden revertir consultando el historial
- **Historial Completo**: Se mantiene un registro detallado de todas las modificaciones
- **Validaciones**: Se mantienen todas las validaciones existentes
- **Compatibilidad**: La funcionalidad es compatible con el sistema existente

## Archivos Modificados

- `wizard/add_model_wizard.py`: Lógica principal del wizard
- `views/add_model_wizard_views.xml`: Interfaz de usuario
- `models/model_design_history.py`: Modelo de historial de diseño

## Uso Recomendado

1. **Para Cambios de Imagen**: Usar la funcionalidad de modificación
2. **Para Ajustes de Cantidad**: Usar la funcionalidad de modificación
3. **Para Cambios de Productos**: Usar la funcionalidad de modificación
4. **Para Cambios de Diseñador**: Usar la funcionalidad de modificación
5. **Para Cambios Mayores**: Considerar crear un nuevo modelo si es necesario

## Ejemplo de Uso

```python
# El wizard detecta automáticamente que es una modificación
# cuando el usuario selecciona un tipo de modelo que ya existe

# Se muestra la alerta:
"ℹ️ Modificación Detectada: Ya existe un modelo del tipo 'Modelo 1' en esta orden.
Al continuar, se actualizará la imagen y la información del modelo existente."

# El botón cambia a "Modificar Modelo"
# Al confirmar, se actualiza el modelo existente con la nueva información
# Se registra todo en el historial de diseño
```

## Casos de Uso Típicos

1. **Actualización de Imagen**: Cambiar la imagen de referencia del modelo
2. **Ajuste de Cantidad**: Modificar la cantidad requerida
3. **Cambio de Productos**: Actualizar los productos relacionados
4. **Reasignación de Diseñador**: Cambiar el diseñador responsable
5. **Correcciones Menores**: Ajustar detalles del modelo existente
