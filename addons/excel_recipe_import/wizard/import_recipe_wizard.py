# -*- coding: utf-8 -*-
import base64
import io
import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

try:
    import pandas as pd
except ImportError:
    pd = None

class ExcelRecipeImportWizard(models.TransientModel):
    _name = 'excel.recipe.import.wizard'
    _description = 'Excel Recipe Import Wizard'

    import_file = fields.Binary('Archivo Excel', required=False)
    import_filename = fields.Char('Nombre del Archivo')
    import_type = fields.Selection([
        ('both', 'Recetas MRP y POS BoM'),
        ('mrp', 'Solo Recetas MRP (Fabricación)'),
        ('pos', 'Solo Recetas POS BoM (Comidas)'),
    ], string='Tipo de Importación', default='both', required=True)

    def action_download_template(self):
        """Descargar la plantilla de importación"""
        template_path = 'excel_recipe_import/data/plantilla_importacion.xlsx'
        try:
            with odoo.tools.file_open(template_path, 'rb') as file:
                file_content = file.read()
        except FileNotFoundError:
            # Provide alternative absolute path in case file_open fails
            try:
                import os
                path = os.path.join(os.path.dirname(__file__), '../data/plantilla_importacion.xlsx')
                with open(path, 'rb') as f:
                    file_content = f.read()
            except Exception as e:
                raise UserError(_("No se pudo encontrar el archivo de plantilla."))

        attachment_id = self.env['ir.attachment'].create({
            'name': 'plantilla_importacion.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'public': True
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment_id.id,
            'target': 'new',
        }

    def action_export_missing_pos_bom(self):
        """Exporta productos POS BoM que no tienen lista de materiales configurada"""
        if not pd:
            raise UserError(_("La librería 'pandas' no está instalada."))

        # Buscar productos que deberían tener receta POS BoM
        products = self.env['product.product'].search([('product_tmpl_id.is_pos_bom', '=', True)])
        
        # Buscar cuáles de esos productos ya tienen receta
        boms = self.env['pos.product.bom'].search([('product_id', 'in', products.ids)])
        products_with_bom = boms.mapped('product_id')
        
        # Filtrar los que faltan
        missing_products = products - products_with_bom

        if not missing_products:
            raise UserError(_("¡Genial! Todos los productos marcados como 'POS BoM' ya tienen su receta configurada."))

        data = []
        for p in missing_products:
            data.append({
                'Recipe': p.name,
                'Component': '',
                'Quantity': ''
            })

        df = pd.DataFrame(data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='POS BoM (Comidas)', index=False)
            
        file_content = output.getvalue()
        
        attachment_id = self.env['ir.attachment'].create({
            'name': 'recetas_faltantes_pos_bom.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'public': True
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment_id.id,
            'target': 'new',
        }

    def _get_or_create_uom(self, uom_name):
        """Get or create a unit of measure. Handles Spanish and English names.
        
        The uom.uom name field is translated (stored as JSON like {'en_US': 'Units', 'es_419': 'Unidades'}),
        so we need to search using both English and Spanish terms.
        """
        uom_name = str(uom_name).strip()
        if not uom_name or uom_name.lower() in ['nan', 'none', '']:
            uom_name = 'Unidades'

        # Normalize: lowercase and strip
        uom_name_lower = uom_name.lower()

        # Spanish/English mappings - map all variations to canonical forms that exist in DB
        # DB has: 'g', 'kg', 'ml', 'L', 'Unidades' (es_419) / 'Units' (en_US)
        mapping = {
            'mililitro': 'ml',
            'mililitros': 'ml',
            'ml': 'ml',
            'gramo': 'g',
            'gramos': 'g',
            'gr': 'g',
            'unidades': 'Unidades',
            'unidad': 'Unidades',
            'units': 'Unidades',
            'u': 'Unidades',
            'kilo': 'kg',
            'kilos': 'kg',
            'kg': 'kg',
            'litro': 'L',
            'litros': 'L',
            'l': 'L',
        }
        search_name = mapping.get(uom_name_lower, uom_name)

        # Strategy: Try multiple search approaches
        # 1. Try the mapped name first
        uom = self.env['uom.uom'].search([('name', '=ilike', search_name)], limit=1)
        
        # 2. If not found, try original name
        if not uom and uom_name_lower != search_name.lower():
            uom = self.env['uom.uom'].search([('name', '=ilike', uom_name)], limit=1)
        
        # 3. Try English equivalent for common Spanish terms
        if not uom:
            english_fallbacks = {
                'unidades': 'Units',
                'unidad': 'Units',
            }
            if uom_name_lower in english_fallbacks:
                uom = self.env['uom.uom'].search([('name', '=ilike', english_fallbacks[uom_name_lower])], limit=1)
        
        # 4. Try searching by JSON text content (PostgreSQL casts JSON to text)
        if not uom:
            self.env.cr.execute(
                "SELECT id FROM uom_uom WHERE name::text ILIKE %s LIMIT 1",
                (f'%{search_name}%',)
            )
            result = self.env.cr.fetchone()
            if result:
                uom = self.env['uom.uom'].browse(result[0])
        
        # 5. Fallback to default unit reference (ID 1 in most Odoo installations)
        if not uom:
            uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        
        # 6. Last resort: get any unit (usually ID 1 = Units/Unidades)
        if not uom:
            uom = self.env['uom.uom'].search([], limit=1, order='id')
        
        return uom

    def _get_or_create_product(self, name, category_name=None, available_in_pos=False, cost=0.0, uom_name='Unidades'):
        if not name or str(name).lower() == 'nan':
            return False

        name = str(name).strip()
        product = self.env['product.product'].search([('name', '=', name)], limit=1)

        if not product:
            uom = self._get_or_create_uom(uom_name)
            # Create product.template first
            template_vals = {
                'name': name,
                'standard_price': cost,
                'uom_id': uom.id if uom else False,
                'available_in_pos': available_in_pos,
            }
            if category_name:
                category = self.env['product.category'].search([('name', '=', category_name)], limit=1)
                if not category:
                    category = self.env['product.category'].create({'name': category_name})
                template_vals['categ_id'] = category.id

            template = self.env['product.template'].create(template_vals)
            
            # Get the created product variant
            product = template.product_variant_id

            if available_in_pos:
                template.is_pos_bom = True

        return product

    def _get_or_create_product_from_materia_prima(self, row):
        """Create product from MATERIA PRIMA sheet row.
        
        Columns: Referencia interna, Nombre, Unidades, Costo, Categoria del producto,
                 Rastrear inventario, Precio de venta, Disponible en PdV, Fecha de caducidad
        """
        default_code = str(row.get('Referencia interna', '')).strip() if pd.notna(row.get('Referencia interna')) else False
        name = str(row.get('Nombre', '')).strip() if pd.notna(row.get('Nombre')) else False
        uom_name = str(row.get('Unidades', 'Unidades')).strip() if pd.notna(row.get('Unidades')) else 'Unidades'
        cost = float(row.get('Costo', 0.0)) if pd.notna(row.get('Costo')) else 0.0
        category_name = str(row.get('Categoria del producto', '')).strip() if pd.notna(row.get('Categoria del producto')) else 'Materia Prima'
        tracking_val = int(row.get('Rastrear inventario', 0)) if pd.notna(row.get('Rastrear inventario')) else 0
        list_price = float(row.get('Precio de venta', 0.0)) if pd.notna(row.get('Precio de venta')) else 0.0
        available_in_pos = bool(row.get('Disponible en PdV', False)) if pd.notna(row.get('Disponible en PdV')) else False
        
        if not name:
            return False
        
        # Search by reference code first, then by name
        product = False
        if default_code:
            product = self.env['product.product'].search([('default_code', '=', default_code)], limit=1)
        if not product:
            product = self.env['product.product'].search([('name', '=', name)], limit=1)
        
        if not product:
            uom = self._get_or_create_uom(uom_name)
            # Map tracking value to tracking type
            tracking_map = {0: 'none', 1: 'lot', 2: 'serial'}
            tracking = tracking_map.get(tracking_val, 'none')
            
            vals = {
                'name': name,
                'default_code': default_code or False,
                'standard_price': cost,
                'list_price': list_price,
                'uom_id': uom.id if uom else False,
                'available_in_pos': available_in_pos,
                'tracking': tracking,
            }
            
            if category_name:
                category = self.env['product.category'].search([('name', '=', category_name)], limit=1)
                if not category:
                    category = self.env['product.category'].create({'name': category_name})
                vals['categ_id'] = category.id
            
            product = self.env['product.product'].create(vals)
            _logger.info(f"Created product from MATERIA PRIMA: {name} ({default_code}) with UoM {uom.name if uom else 'Unknown'}")
        
        return product

    def _check_dependencies(self):
        """Verifica las dependencias necesarias y sus versiones.
        
        Returns:
            tuple: (is_valid, error_messages, warning_messages)
        """
        errors = []
        warnings = []
        
        # Check pandas
        if pd is None:
            errors.append(_("❌ La librería 'pandas' no está instalada"))
        else:
            try:
                import pandas
                pandas_version = pandas.__version__
                # pandas should be available, no specific version requirement
                _logger.info(f"✓ pandas version: {pandas_version}")
            except Exception as e:
                errors.append(f"❌ Error al verificar pandas: {str(e)}")
        
        # Check openpyxl
        try:
            import openpyxl
            openpyxl_version = openpyxl.__version__
            # Check if version >= 3.1.5
            from packaging import version
            if version.parse(openpyxl_version) < version.parse("3.1.5"):
                errors.append(
                    _("❌ openpyxl versión %s instalada. Se requiere versión 3.1.5 o superior.") % openpyxl_version
                )
            else:
                _logger.info(f"✓ openpyxl version: {openpyxl_version}")
        except ImportError:
            errors.append(_("❌ La librería 'openpyxl' no está instalada"))
        except Exception as e:
            errors.append(f"❌ Error al verificar openpyxl: {str(e)}")
        
        # Check et_xmlfile (required by openpyxl)
        try:
            import et_xmlfile
            _logger.info(f"✓ et_xmlfile available")
        except ImportError:
            warnings.append(_("⚠ La librería 'et_xmlfile' no está instalada (requerida por openpyxl)"))
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    def action_validate(self):
        """Valida el archivo y las dependencias antes de importar."""
        # Check dependencies first
        is_valid, errors, warnings = self._check_dependencies()
        
        result_message = []
        
        if errors:
            result_message.append(_("**Errores críticos:**"))
            for error in errors:
                result_message.append(f"  • {error}")
            result_message.append("")
            result_message.append(_("Por favor, instale las dependencias faltantes antes de importar."))
        
        if warnings:
            result_message.append(_("**Advertencias:**"))
            for warning in warnings:
                result_message.append(f"  • {warning}")
            result_message.append("")
        
        # If file is uploaded, validate it
        if self.import_file:
            if not pd:
                errors.append(_("No se puede validar el archivo sin pandas"))
            else:
                try:
                    file_content = base64.b64decode(self.import_file)
                    xl = pd.ExcelFile(io.BytesIO(file_content))
                    
                    result_message.append(_("**Archivo válido:** %s") % self.import_filename)
                    result_message.append(f"  • Sheets encontrados: {', '.join(xl.sheet_names)}")
                    
                    # Check for required sheets
                    required_sheets = ['POS BoM (Comidas)']
                    missing_sheets = [s for s in required_sheets if s not in xl.sheet_names]
                    
                    if missing_sheets:
                        warnings.append(_("⚠ El archivo no contiene las sheets requeridas: %s") % ', '.join(missing_sheets))
                    
                    # Check column structure in each sheet
                    for sheet_name in xl.sheet_names:
                        try:
                            df = xl.parse(sheet_name, nrows=1)
                            columns = df.columns.tolist()
                            result_message.append(f"  • Sheet '{sheet_name}': {len(columns)} columnas")
                        except Exception as e:
                            warnings.append(f"⚠ Error al leer sheet '{sheet_name}': {str(e)}")
                    
                except Exception as e:
                    errors.append(_("❌ Error al leer el archivo Excel: %s") % str(e))
                    is_valid = False
        else:
            result_message.append(_("⚠ No se ha subido ningún archivo para validar"))
        
        # Build final message
        final_message = "\n".join(result_message)
        
        if is_valid and not errors:
            final_message = _("✅ **Validación exitosa!**\n\n") + final_message
            if warnings:
                final_message += _("\n\nPuede proceder con la importación.")
        else:
            final_message = _("❌ **Validación fallida**\n\n") + final_message
        
        # Return action to show popup (don't close window, let user click Import)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Resultado de Validación'),
                'message': final_message,
                'sticky': len(errors) > 0,
                'type': 'success' if is_valid else 'danger',
            }
        }

    def action_import(self):
        """Importa las recetas desde el archivo Excel después de validar."""
        # First validate dependencies
        is_valid, errors, warnings = self._check_dependencies()

        if not is_valid:
            error_msg = _("Errores críticos encontrados:\n\n")
            for error in errors:
                error_msg += f"• {error}\n"
            error_msg += _("\nPor favor, corrija estos errores antes de importar.")
            raise UserError(error_msg)

        if not self.import_file:
            raise UserError(_("Por favor, suba un archivo Excel para importar."))

        if not pd:
            raise UserError(_("La librería 'pandas' no está instalada."))

        file_content = base64.b64decode(self.import_file)
        try:
            xl = pd.ExcelFile(io.BytesIO(file_content))
        except Exception as e:
            raise UserError(_("Formato de archivo inválido. Por favor, suba un archivo Excel (.xlsx). Error: %s") % str(e))

        imported_sheets = []
        
        # Import based on selected type
        import_mrp = self.import_type in ['both', 'mrp']
        import_pos = self.import_type in ['both', 'pos']

        # 0. MATERIA PRIMA - Always import raw materials first (needed for both MRP and POS)
        if 'MATERIA PRIMA' in xl.sheet_names:
            df_materia_prima = xl.parse('MATERIA PRIMA')
            created_count = 0
            for index, row in df_materia_prima.iterrows():
                if pd.notna(row.get('Nombre')) and str(row.get('Nombre')).strip():
                    product = self._get_or_create_product_from_materia_prima(row)
                    if product:
                        created_count += 1
            _logger.info(f"Imported {created_count} products from MATERIA PRIMA sheet")
            imported_sheets.append(f"MATERIA PRIMA ({created_count} productos)")

        # 1. Productos - Always import products (needed for both)
        if 'Products' in xl.sheet_names:
            df_products = xl.parse('Products')
            product_count = 0
            for index, row in df_products.iterrows():
                name = row.get('Name')
                if not name or str(name).lower() == 'nan':
                    continue
                cat = row.get('Category')
                available = row.get('Available in POS', False)
                if str(available).lower() in ['true', '1', '1.0', 'yes']:
                    available = True
                else:
                    available = False
                cost = row.get('Cost', 0.0)
                if pd.isna(cost):
                    cost = 0.0
                uom = row.get('UoM', 'Unidades')
                self._get_or_create_product(name, cat, available, cost, uom)
                product_count += 1
            _logger.info(f"Imported {product_count} products from Products sheet")
            imported_sheets.append(f"Products ({product_count} productos)")

        # 2. MRP BoM (Subproducts) - Only if MRP import is selected
        if import_mrp and 'MRP BoM (Subproducts)' in xl.sheet_names:
            df_mrp = xl.parse('MRP BoM (Subproducts)')
            bom_count = 0
            for recipe_name, group in df_mrp.groupby('Recipe'):
                if str(recipe_name).lower() == 'nan':
                    continue
                recipe_product = self._get_or_create_product(recipe_name, category_name='Subproducto')

                if not recipe_product:
                    continue

                bom = self.env['mrp.bom'].search([('product_tmpl_id', '=', recipe_product.product_tmpl_id.id)], limit=1)
                if not bom:
                    bom = self.env['mrp.bom'].create({
                        'product_tmpl_id': recipe_product.product_tmpl_id.id,
                        'product_qty': 1.0,
                        'type': 'normal',
                    })
                    bom_count += 1
                else:
                    bom.bom_line_ids.unlink() # Limpiar existentes

                for _, row in group.iterrows():
                    comp_name = row.get('Component')
                    if str(comp_name).lower() == 'nan':
                        continue
                    comp_product = self._get_or_create_product(comp_name, category_name='Materia Prima')
                    if comp_product:
                        qty = row.get('Quantity', 1.0)
                        if pd.isna(qty):
                            qty = 1.0
                        self.env['mrp.bom.line'].create({
                            'bom_id': bom.id,
                            'product_id': comp_product.id,
                            'product_qty': float(qty)
                        })
            _logger.info(f"Imported {bom_count} MRP BoMs")
            imported_sheets.append(f"MRP BoM ({bom_count} recetas)")

        # 3. POS BoM (Comidas) - Only if POS import is selected
        if import_pos and 'POS BoM (Comidas)' in xl.sheet_names:
            df_pos = xl.parse('POS BoM (Comidas)')
            pos_bom_count = 0
            for recipe_name, group in df_pos.groupby('Recipe'):
                if str(recipe_name).lower() == 'nan':
                    continue
                recipe_product = self._get_or_create_product(recipe_name, category_name='Comidas', available_in_pos=True)

                if not recipe_product:
                    continue

                # Asegurar que esté marcado como POS BoM
                recipe_product.product_tmpl_id.is_pos_bom = True

                bom = self.env['pos.product.bom'].search([('product_id', '=', recipe_product.id)], limit=1)
                if not bom:
                    bom = self.env['pos.product.bom'].create({
                        'product_id': recipe_product.id,
                        'product_qty': 1.0,
                        'product_uom_id': recipe_product.uom_id.id,
                    })
                    pos_bom_count += 1
                else:
                    bom.product_bom_line_ids.unlink() # Limpiar existentes

                for _, row in group.iterrows():
                    comp_name = row.get('Component')
                    if str(comp_name).lower() == 'nan':
                        continue
                    comp_product = self._get_or_create_product(comp_name)
                    if comp_product:
                        qty = row.get('Quantity', 1.0)
                        if pd.isna(qty):
                            qty = 1.0
                        self.env['pos.product.bom.line'].create({
                            'pos_bom_id': bom.id,
                            'product_id': comp_product.id,
                            'product_qty': float(qty),
                            'product_uom_id': comp_product.uom_id.id,
                        })
            _logger.info(f"Imported {pos_bom_count} POS BoMs")
            imported_sheets.append(f"POS BoM ({pos_bom_count} recetas)")

        # Build success message
        message = "**Importación Exitosa**\n\n"
        message += "Se han importado las siguientes sheets:\n"
        for sheet in imported_sheets:
            message += f"  • {sheet}\n"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Importación Exitosa',
                'message': message,
                'sticky': False,
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }
