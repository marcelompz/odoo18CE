# -*- coding: utf-8 -*-
"""
Created on 2025-03-04 15:58:37

@author: drojo
"""
# python
import logging
import json

# odoo
from odoo import _, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def create_json_data(doc, origin='invoice'):
    """Crea el JSON principal para la factura electrónica."""
    if not doc.invoice_number:
        doc.assign_number()

    # lote list
    lote = []

    if origin == 'invoice':
        money_change = doc.currency_id
    
        if doc.move_type == 'out_invoice':
            tipoDocumento = 1
        elif doc.move_type == 'out_refund':
            tipoDocumento = 5

    else:
        money_change = doc.env.company.currency_id
        tipoDocumento = 7
    
    # main
    main_json = {
        "tipoDocumento": tipoDocumento,
        "establecimiento": int(doc.authorization_id.establishment_code),
        "punto": int(doc.authorization_id.generation_point),
        "numero": int(doc.invoice_number[8:]),
        "descripcion": doc.env.company.description,
        "observacion": doc.env.company.general_remarks,
        "fecha": doc._get_current_datetime().strftime("%Y-%m-%dT%H:%M:%S"),
        "tipoEmision": int(doc.company_id.emitter_type),
        "tipoTransaccion": doc.company_id.company_transactiontype_id.transaction_id,
        "tipoImpuesto": doc.company_id.company_taxtype_id.taxtype_id,
        "moneda": money_change.name,
        "cambio": int(money_change.inverse_rate) if money_change.name != 'PYG' else 1,
    }

    # customer
    main_json["cliente"] = {
        "contribuyente": True if doc.partner_id.l10n_latam_identification_type_id.document_id == 0 else False,
        "ruc": doc.partner_id.vat,
        "razonSocial": doc.partner_id.name,
        "nombreFantasia": doc.partner_id.partner_fantasy_name,
        "tipoOperacion": doc._get_type_of_operations(),
        "direccion": f'{doc.partner_id.street} {doc.partner_id.street2 if doc.partner_id.street2 else ""}',
        "numeroCasa": doc.partner_id.house_number or "0",
        "departamento": doc.partner_id.state_id.code,
        "departamentoDescripcion": doc.partner_id.state_id.name,
        "distrito": doc.partner_id.district_id.code,
        "distritoDescripcion": doc.partner_id.district_id.name,
        "ciudad": doc.partner_id.city_id.code,
        "ciudadDescripcion": doc.partner_id.city_id.name,
        "pais": doc.partner_id.country_id.code_alfa_3,
        "paisDescripcion": doc.partner_id.country_id.name,
        "tipoContribuyente": 1 if doc.partner_id.company_type == "person" else 2,
        "documentoTipo": doc.partner_id.l10n_latam_identification_type_id.document_id,
        "documentoNumero": doc.partner_id.vat,
        "telefono": doc.partner_id.phone.replace(' ','') if doc.partner_id.phone else "",
        "celular": doc.partner_id.mobile.replace(' ','') if doc.partner_id.mobile else "",
        "email": doc.partner_id.email,
        "codigo": doc.partner_id.partner_code,
    }

    # users
    user_id = doc.env.user
    main_json["usuario"] = {
        "documentoTipo": user_id.l10n_latam_identification_type_id.document_id,
        "documentoNumero": user_id.vat,
        "nombre": user_id.name,
        "cargo": user_id.function,
    }

    if origin == 'invoice':
        # presence indicator
        if doc.move_type == 'out_invoice':
            main_json["factura"] = {"presencia": doc.company_id.presence_id.presence_id}

        # nota credito debito
        if doc.move_type == 'out_refund':
            main_json["notaCreditoDebito"] = {"motivo": doc.creditdebit_note_id.code}

        # payment conditions
        if doc.move_type == 'out_invoice':
            main_json["condicion"] = {
                "tipo": 1 if doc.invoice_payment_term_id.is_cash_payment else 2,
            }

            if doc.invoice_payment_term_id.is_cash_payment:
                # contado
                main_json["condicion"].update({
                    "entregas": [
                        {
                            "tipo": 1,
                            "monto": doc.amount_total_in_currency_signed,
                            "moneda": doc.currency_id.name,
                            "cambio" : int(money_change.inverse_rate) if doc.currency_id.name != 'PYG' else 1,
                        },
                    ],
                })

            else:
                # credito a cuota
                if doc.invoice_payment_term_id.line_ids[0].value == 'installment':
                    main_json["condicion"].update({
                        "credito": {
                                "tipo": 2,
                                "cuotas": doc.invoice_payment_term_id.line_ids[0].period_count or 1,
                            },
                        })

                else:
                    # credito a plazo
                    plazo_credito = ''
                    if doc.invoice_payment_term_id and doc.invoice_payment_term_id.line_ids:
                        # total_months = sum(line.months for line in doc.invoice_payment_term_id.line_ids)
                        total_days = sum(line.nb_days for line in doc.invoice_payment_term_id.line_ids)
                        
                        # if total_months > 0:
                        #     plazo_credito = f'{total_months} Mes/es'
                        
                        if total_days > 0:
                            if plazo_credito:
                                plazo_credito += f', {total_days} Días'
                            else:
                                plazo_credito = f'{total_days} Días'
                    else:
                        total_days_diff = (doc.invoice_date_due - doc.invoice_date).days
                        plazo_credito = f'{total_days_diff} Días'

                    main_json["condicion"].update({
                        "credito": {
                            "tipo": 1,
                            "plazo": plazo_credito,
                        },
                    })

    else:
        # remision
        main_json["remision"] = {
            "motivo" : doc.delivery_note_id.code,
            "tipoResponsable" : doc.responsible_note_id.code,
            "kms" : doc.kms_traveled,
            "fechaFactura" : f'{fields.Date().to_date(doc.scheduled_date)}'
        }


    # invoice items
    invoice_line = []

    if origin == 'invoice':
        for line in doc.invoice_line_ids:
            if line.display_type == 'line_note':
                if len(invoice_line) > 0:
                    invoice_line[-1]['observacion'] = line.name
                
                else:
                    continue

            else:
                item = {
                    "codigo": line.product_id.barcode or line.product_id.default_code or "",
                    "descripcion": line.name,
                    "observacion": "",
                    "ncm": line.product_id.ncm if line.product_id.ncm else "",
                    "unidadMedida": int(line.product_uom_id.code),
                    "cantidad": line.quantity,
                    "precioUnitario": line.price_unit,
                    "cambio": 0.0,
                    "descuento": round((line.discount/100) * line.price_unit, 8),
                    "ivaTipo": 1 if line.tax_ids else 3,
                    "ivaBase": 100  if line.tax_ids else 0,
                    "iva": int(sum(tax.amount for tax in line.tax_ids)) if line.tax_ids else 0,
                    "lote": "",
                    "vencimiento": "",
                    "numeroSerie": "",
                    "numeroPedido": "",
                    "numeroSeguimiento": "",
                }
                invoice_line.append(item)

        if doc.move_type == 'out_refund':
            main_json["documentoAsociado"] = {
                "formato": doc.doc_format_id.code,
                "cdc": doc.associated_document,
                "tipoDocumentoImpreso": doc.doc_format_type_id.code if not doc.comes_from_invoice else "",
                "timbrado": doc.doc_stamped if not doc.comes_from_invoice else "",
                "establecimiento": doc.doc_establishment if not doc.comes_from_invoice else "",
                "punto": doc.doc_point if not doc.comes_from_invoice else "",
                "numero": doc.doc_number if not doc.comes_from_invoice else "",
                "fecha": doc.doc_date.strftime("%Y-%m-%d") if not doc.comes_from_invoice else "",
            }

    else:
        for line in doc.move_ids_without_package:
            item = {
                "codigo": line.product_id.default_code,
                "descripcion": line.product_id.name,
                "observacion": "",
                "ncm": line.product_id.ncm if line.product_id.ncm else "",
                "unidadMedida": int(line.product_uom.code),
                "cantidad": line.quantity,
                "precioUnitario": line.price_unit,
                "cambio": 0.0,
                "ivaTipo": 1 if line.product_id.taxes_id else 3,
                "ivaBase": 100,
                "iva": int(sum(tax.amount for tax in line.product_id.taxes_id)) if line.product_id.taxes_id else 0,
                "lote": "",
                "vencimiento": "",
            }
            invoice_line.append(item)

        if doc.picking_type_code == 'outgoing':
            destination = doc.partner_id

        if doc.picking_type_code == 'internal':
            destination = doc.location_dest_id.warehouse_id.partner_id
        
        main_json["transporte"] = {
            "tipo" : int(doc.transporte_type),
            "modalidad" : int(doc.fleet_modality),
            "tipoResponsable" : int(doc.freight_cost),
            "condicionNegociacion" : doc.negotiation_condition_id.code,
            "inicioEstimadoTranslado" : f'{fields.Date().to_date(doc.scheduled_date)}',
            "finEstimadoTranslado" : f'{fields.Date().to_date(doc.end_transfer_date)}',
            "salida" : {
                "direccion" : f'{doc.company_id.partner_id.street} {doc.company_id.partner_id.street2 if doc.company_id.partner_id.street2 else ""}',
                "numeroCasa" : doc.company_id.partner_id.house_number or "0",
                "complementoDireccion1" : doc.company_id.partner_id.street or "", 
                "complementoDireccion2" : doc.company_id.partner_id.street2 or "",
                "departamento" : doc.company_id.partner_id.state_id.code,
                "departamentoDescripcion" : doc.company_id.partner_id.state_id.name,
                "distrito" : doc.company_id.partner_id.district_id.code,
                "distritoDescripcion" : doc.company_id.partner_id.district_id.name,
                "ciudad" : doc.company_id.partner_id.city_id.code,
                "ciudadDescripcion" : doc.company_id.partner_id.city_id.name,
                "pais" : doc.company_id.partner_id.country_id.code_alfa_3,
                "paisDescripcion" : doc.company_id.partner_id.country_id.name,
                "telefonoContacto" : doc.company_id.partner_id.mobile or ""
            },
            "entrega" : {
                "direccion" : f'{destination.street} {destination.street2 if destination.street2 else ""}',
                "numeroCasa" : destination.house_number or "0",
                "complementoDireccion1" : destination.street or "",
                "complementoDireccion2" : destination.street2 or "",
                "departamento" : destination.state_id.code,
                "departamentoDescripcion" : destination.state_id.name,
                "distrito" : destination.district_id.code,
                "distritoDescripcion" : destination.district_id.name,
                "ciudad" : destination.city_id.code,
                "ciudadDescripcion" : destination.city_id.name,
                "pais" : destination.country_id.code_alfa_3,
                "paisDescripcion" : destination.country_id.name,
                "telefonoContacto" : destination.mobile or ""
            },
            "vehiculo" : {
                "tipo" : doc.fleet_id.type_of_transport_id.name,
                "marca" : doc.fleet_id.model_id.brand_id.name,
                "documentoTipo" : doc.fleet_id.type_id_vehicle, 
                "documentoNumero" : doc.fleet_id.license_plate if doc.fleet_id.type_id_vehicle == '1' else "",
                "obs" : "",
                "numeroMatricula" : doc.fleet_id.license_plate if doc.fleet_id.type_id_vehicle == '2' else "",
                "numeroVuelo" : ""
            },
            "transportista" : {
                "contribuyente" : True if doc.cross_carrier_id.l10n_latam_identification_type_id.document_id == 0 else False,
                "nombre" : doc.cross_carrier_id.name,
                "ruc" : doc.cross_carrier_id.vat, 
                "documentoTipo" : doc.cross_carrier_id.l10n_latam_identification_type_id.document_id if doc.cross_carrier_id.l10n_latam_identification_type_id.document_id != 0 else "",
                "documentoNumero" : doc.cross_carrier_id.vat if doc.cross_carrier_id.l10n_latam_identification_type_id.document_id != 0 else "",
                "direccion" : f'{doc.cross_carrier_id.street} {doc.cross_carrier_id.street2 if doc.cross_carrier_id.street2 else ""}',
                "obs" : "",
                "pais" : doc.cross_carrier_id.country_id.code_alfa_3,
                "paisDescripcion" : doc.cross_carrier_id.country_id.name,
                "chofer" : {
                    "documentoNumero" : doc.driver_id.vat,
                    "nombre" : doc.driver_id.name,
                    "direccion" : f'{doc.driver_id.street} {doc.driver_id.street2 if doc.driver_id.street2 else ""}'
                },
                "agente" : {
                    "nombre" : "",
                    "ruc" : "",
                    "direccion" : ""
                }
            }
        }

        document = doc._get_associated_document()

        if len(document) > 0:
            main_json["documentoAsociado"] = document

    main_json["items"] = invoice_line

    lote.append(main_json)

    return lote
