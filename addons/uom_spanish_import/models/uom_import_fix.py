# -*- coding: utf-8 -*-
"""
UoM Spanish Import Fix - Main Model

This module fixes UoM import when Odoo UI is in Spanish.
The issue: Odoo's frontend validates Many2one fields using English names internally,
but Spanish users have CSV files with Spanish UoM names (Unidades, g, ml).

Solution: Convert Spanish UoM names to IDs during _convert_import_data,
before frontend validation occurs.
"""

import csv
from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


# Spanish UoM name to ID mapping
SPANISH_UOM_TO_ID = {
    # Units
    'unidades': 1,
    'unidad': 1,
    'uds': 1,
    'ud': 1,
    'units': 1,  # Also support English
    # Grams
    'g': 15,
    'gramo': 15,
    'gramos': 15,
    # Milliliters
    'ml': 12,
    'mililitro': 12,
    'mililitros': 12,
    # Kilograms
    'kg': 16,
    'kilogramo': 16,
    'kilogramos': 16,
    # Liters
    'l': 13,
    'litro': 13,
    'litros': 13,
    # Dozens
    'docena': 3,
    'docenas': 3,
    # Hours
    'hora': 4,
    'horas': 4,
    'h': 4,
    # Days
    'dia': 5,
    'día': 5,
    'dias': 5,
    'días': 5,
    'd': 5,
}

# Spanish product type mapping (selection field values)
# Supports both Odoo 18 (product, consu, service) and Odoo 19 (goods, service, combo)
SPANISH_PRODUCT_TYPE = {
    # Odoo 19: Storable Product
    'almacenable': 'goods',
    'producto almacenable': 'goods',
    'producto': 'goods',
    'goods': 'goods',  # English Odoo 19
    # Odoo 18: Storable Product (legacy)
    'product': 'goods',  # Convert old 'product' to 'goods'
    
    # Odoo 19/18: Consumable
    'consumible': 'consu',
    'consumo': 'consu',
    'consu': 'consu',
    
    # Odoo 19/18: Service
    'servicio': 'service',
    'servicios': 'service',
    'service': 'service',
    
    # Odoo 19: Combo (new)
    'combo': 'combo',
    'combinado': 'combo',
}


class BaseImport(models.TransientModel):
    _inherit = 'base_import.import'

    def _convert_import_data(self, fields, options):
        """Override to convert Spanish names to technical values.

        This runs BEFORE frontend validation, so JavaScript receives IDs
        instead of names that it can't match.

        Converts:
        - UoM names (Unidades, g, ml) to IDs
        - Product type names (Almacenable, Consumible, Servicio) to technical values

        Args:
            fields: List of field names (with False placeholders)
            options: Import options including file data

        Returns:
            tuple: (data, import_fields) with values converted
        """
        # Call original method to get base data
        data, import_fields = super()._convert_import_data(fields, options)

        # Find field indices
        uom_id_index = None
        uom_po_id_index = None
        type_index = None

        for i, field in enumerate(import_fields):
            if field == 'uom_id':
                uom_id_index = i
            elif field == 'uom_po_id':
                uom_po_id_index = i
            elif field == 'type':
                type_index = i

        # If no fields to convert, return as-is
        if uom_id_index is None and uom_po_id_index is None and type_index is None:
            return data, import_fields

        _logger.info(f"_convert_import_data: {len(data)} rows, uom_id={uom_id_index}, type={type_index}")

        # Convert values
        uom_converted = 0
        type_converted = 0
        converted_data = []

        for row_idx, row in enumerate(data):
            converted_row = list(row)

            # Convert uom_id
            if uom_id_index is not None and uom_id_index < len(converted_row):
                uom_value = converted_row[uom_id_index]
                converted_id = self._get_uom_id(uom_value)
                if converted_id and converted_id != uom_value:
                    converted_row[uom_id_index] = converted_id
                    uom_converted += 1
                    if uom_converted <= 5:
                        _logger.info(f"Row {row_idx}: UoM '{uom_value}' -> ID {converted_id}")

            # Convert uom_po_id
            if uom_po_id_index is not None and uom_po_id_index < len(converted_row):
                uom_value = converted_row[uom_po_id_index]
                converted_id = self._get_uom_id(uom_value)
                if converted_id and converted_id != uom_value:
                    converted_row[uom_po_id_index] = converted_id

            # Convert product type
            if type_index is not None and type_index < len(converted_row):
                type_value = converted_row[type_index]
                converted_type = self._get_product_type(type_value)
                if converted_type and converted_type != type_value:
                    converted_row[type_index] = converted_type
                    type_converted += 1
                    if type_converted <= 5:
                        _logger.info(f"Row {row_idx}: Type '{type_value}' -> '{converted_type}'")

            converted_data.append(converted_row)

        if uom_converted > 5:
            _logger.info(f"... and {uom_converted - 5} more UoM conversions")
        if uom_converted > 0:
            _logger.info(f"Total UoM conversions: {uom_converted}")
        if type_converted > 0:
            _logger.info(f"Total product type conversions: {type_converted}")

        return converted_data, import_fields

    def _get_uom_id(self, uom_value):
        """Get UoM ID from value (name or ID).

        Args:
            uom_value: String or int UoM value

        Returns:
            int: UoM ID, or None if not found
        """
        # Handle integer IDs directly
        if isinstance(uom_value, int):
            return uom_value

        # Handle None/empty
        if not uom_value:
            return None

        uom_str = str(uom_value).strip().lower()
        if not uom_str or uom_str in ('', 'nan', 'none'):
            return None

        # Check if it's a numeric string (already an ID)
        if uom_str.isdigit():
            return int(uom_str)

        # Try Spanish mapping first
        if uom_str in SPANISH_UOM_TO_ID:
            return SPANISH_UOM_TO_ID[uom_str]

        # Try to find by name in database (both languages)
        self.env.cr.execute("""
            SELECT id FROM uom_uom
            WHERE name->>'es_419' ILIKE %s
               OR name->>'en_US' ILIKE %s
            LIMIT 1
        """, (uom_str, uom_str))

        result = self.env.cr.fetchone()
        if result:
            return result[0]

        # Not found
        _logger.warning(f"UoM '{uom_value}' not found in mapping or database")
        return None

    def _get_product_type(self, type_value):
        """Get product type technical value from Spanish name.
        
        Supports Odoo 19 (goods, service, combo) and Odoo 18 (product, consu, service).

        Args:
            type_value: String product type name

        Returns:
            str: Technical value (goods, consu, service, combo), or None if not found
        """
        if not type_value:
            return None

        type_str = str(type_value).strip().lower()
        if not type_str or type_str in ('', 'nan', 'none'):
            return None

        # Try Spanish mapping
        if type_str in SPANISH_PRODUCT_TYPE:
            return SPANISH_PRODUCT_TYPE[type_str]

        # Already a technical value (Odoo 19)
        if type_str in ('goods', 'service', 'combo', 'consu'):
            return type_str

        # Not found
        _logger.warning(f"Product type '{type_value}' not found in mapping")
        return None
