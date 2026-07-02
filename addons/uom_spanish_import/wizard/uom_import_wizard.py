# -*- coding: utf-8 -*-
"""
Wizard to import products from CSV with automatic UoM conversion.
This bypasses Odoo's standard import validation.
"""

import csv
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

# Mapping from Spanish UoM names to database IDs
UOM_NAME_TO_ID = {
    'g': 15,
    'gramo': 15,
    'gramos': 15,
    'ml': 12,
    'mililitro': 12,
    'mililitros': 12,
    'unidades': 1,
    'unidad': 1,
    'uds': 1,
    'ud': 1,
    # Also map numeric strings to themselves (as integers)
    '1': 1,
    '12': 12,
    '15': 15,
}


class UomImportWizard(models.TransientModel):
    _name = 'uom.import.wizard'
    _description = 'Product Import Wizard with UoM Conversion'

    file = fields.Binary('File', required=True)
    filename = fields.Char('Filename')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft')
    import_log = fields.Text('Import Log', readonly=True)
    products_created = fields.Integer('Products Created', readonly=True)
    products_updated = fields.Integer('Products Updated', readonly=True)

    def _get_uom_id(self, uom_value):
        """Convert UoM value to ID.
        
        Args:
            uom_value: String or int UoM value
            
        Returns:
            int: UoM ID
        """
        if not uom_value:
            return 1  # Default to Unidades
        
        # If already an integer, use it directly
        if isinstance(uom_value, int):
            return uom_value
        
        uom_str = str(uom_value).strip().lower()
        
        # Try mapping first
        if uom_str in UOM_NAME_TO_ID:
            return UOM_NAME_TO_ID[uom_str]
        
        # Try to find by name in database
        self.env.cr.execute("""
            SELECT id FROM uom_uom
            WHERE name->>'es_419' ILIKE %s
               OR name->>'en_US' ILIKE %s
            LIMIT 1
        """, (uom_str, uom_str))
        
        result = self.env.cr.fetchone()
        if result:
            return result[0]
        
        # Default to Unidades
        _logger.warning(f"UoM '{uom_value}' not found, using default (Unidades)")
        return 1

    def action_import(self):
        """Import products from CSV file."""
        self.ensure_one()
        
        if not self.file:
            raise UserError(_('Please select a file to import'))
        
        # Decode file
        file_content = base64.b64decode(self.file)
        
        # Try to read as CSV
        try:
            # Try with semicolon separator first
            import io
            csv_file = io.StringIO(file_content.decode('utf-8'))
            reader = csv.DictReader(csv_file, delimiter=';')
            
            if 'Unidades' not in (reader.fieldnames or []):
                raise UserError(_('Column "Unidades" not found in CSV file'))
            
            products_created = 0
            products_updated = 0
            errors = []
            log_lines = []
            
            for row_idx, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    # Get UoM ID
                    uom_id = self._get_uom_id(row.get('Unidades', ''))
                    
                    # Prepare product values
                    product_vals = {
                        'default_code': row.get('Referencia interna', ''),
                        'name': row.get('Nombre', ''),
                        'standard_price': float(row.get('Costo', 0) or 0),
                        'list_price': float(row.get('Precio de venta', 0) or 0),
                        'is_storable': row.get('Rastrear inventario', '').upper() == 'VERDADERO',
                        'available_in_pos': row.get('Disponible en PdV', '').upper() == 'VERDADERO',
                        'uom_id': uom_id,
                        'type': 'consu' if not row.get('Rastrear inventario', '').upper() == 'VERDADERO' else 'product',
                    }
                    
                    # Try to find existing product by default_code
                    existing = self.env['product.template'].search([
                        ('default_code', '=', product_vals['default_code'])
                    ], limit=1)
                    
                    if existing:
                        existing.write(product_vals)
                        products_updated += 1
                        log_lines.append(f"Row {row_idx}: Updated {product_vals['default_code']}")
                    else:
                        # Find or create category
                        categ_name = row.get('Categoria del producto', 'MATERIA PRIMA')
                        categ = self.env['product.category'].search([
                            ('name', '=ilike', categ_name)
                        ], limit=1)
                        if not categ:
                            categ = self.env['product.category'].create({
                                'name': categ_name,
                            })
                        
                        product_vals['categ_id'] = categ.id
                        
                        # Create product
                        self.env['product.template'].create(product_vals)
                        products_created += 1
                        log_lines.append(f"Row {row_idx}: Created {product_vals['default_code']}")
                    
                except Exception as e:
                    errors.append(f"Row {row_idx}: {str(e)}")
                    log_lines.append(f"Row {row_idx}: ERROR - {str(e)}")
            
            # Update wizard state
            self.write({
                'state': 'done',
                'products_created': products_created,
                'products_updated': products_updated,
                'import_log': '\n'.join(log_lines),
            })
            
            # Return success message
            result = {
                'type': 'ir.actions.act_window',
                'res_model': 'uom.import.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
            
            if errors:
                raise UserError(_('Import completed with errors:\n\n%s') % '\n'.join(errors[:10]))
            
            return result
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                csv_file = io.StringIO(file_content.decode('latin-1'))
                reader = csv.DictReader(csv_file, delimiter=';')
                # ... same processing as above
            except Exception as e:
                raise UserError(_('Error reading file: %s') % str(e))
        except Exception as e:
            raise UserError(_('Error importing file: %s') % str(e))
