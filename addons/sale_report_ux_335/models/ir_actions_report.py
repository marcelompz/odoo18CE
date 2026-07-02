# -*- coding: utf-8 -*-

from odoo import models
import base64
import os
import tempfile
import logging
from contextlib import closing
from PyPDF2 import PdfFileReader, PdfFileWriter

_logger = logging.getLogger(__name__)

# URL que wkhtmltopdf debe usar dentro del contenedor (Odoo escucha en 8069)
REPORT_INTERNAL_URL = 'http://127.0.0.1:8069/'


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """Fuerza report.url a la URL interna durante la generación del PDF (evita ConnectionRefusedError en Docker)."""
        icp = self.env['ir.config_parameter'].sudo()
        old_url = icp.get_param('report.url')
        try:
            icp.set_param('report.url', REPORT_INTERNAL_URL)
            return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        finally:
            icp.set_param('report.url', old_url or '')

    def _run_wkhtmltopdf(
        self,
        bodies,
        report_ref=False,
        header=None,
        footer=None,
        landscape=False,
        specific_paperformat_args=None,
        set_viewport_size=False,
    ):
        """
        Interceptamos la salida cruda de wkhtmltopdf para incrustar el fondo de forma exacta 
        usando PyPDF2, asegurando dimensiones 100% correctas en hoja A4.
        """
        report = self._get_report(report_ref)
        pdf_content = super()._run_wkhtmltopdf(
            bodies,
            report_ref=report_ref,
            header=header,
            footer=footer,
            landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )

        # Solo aplicar nuestro fondo especial si es nuestro reporte UX 335
        if report.report_name != 'sale_report_ux_335.report_sale_order_ux_335':
            return pdf_content

        # Conseguir la imagen de fondo configurada en la compañía
        company = self.env.company
        bg_image_data = company.report_background_image
        if not bg_image_data:
            return pdf_content

        # Intentar mezclar la imagen como fondo (Watermark)
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            import io
            from PIL import Image

            # 1. Crear un PDF de 1 página que sea solamente la imagen a tamaño completo
            bg_packet = io.BytesIO()
            bg_canvas = canvas.Canvas(bg_packet, pagesize=A4)
            width, height = A4

            # Convertir la imagen base64 a formato que reportlab pueda leer
            img_data = base64.b64decode(bg_image_data)
            from reportlab.lib.utils import ImageReader
            bg_image_reader = ImageReader(io.BytesIO(img_data))

            # Dibujar imagen en el canvas ocupando toda la hoja (210x297mm)
            bg_canvas.drawImage(
                bg_image_reader, 
                x=0, y=0, width=width, height=height, 
                preserveAspectRatio=False, anchor='c'
            )
            bg_canvas.save()

            bg_packet.seek(0)
            bg_pdf = PdfFileReader(bg_packet)
            
            # 2. Leer el PDF que nos generó wkhtmltopdf
            report_packet = io.BytesIO(pdf_content)
            report_pdf = PdfFileReader(report_packet)

            # 3. Fusionar página por página
            output = PdfFileWriter()
            for i in range(report_pdf.getNumPages()):
                report_page = report_pdf.getPage(i)
                # Crear una página nueva que sea una COPIA del fondo para no contaminar el original
                import copy
                bg_page = copy.copy(bg_pdf.getPage(0))
                # Pegar el contenido de la página actual del reporte encima de la copia del fondo
                bg_page.mergePage(report_page)
                output.addPage(bg_page)

            # Escribir el resultado final
            final_packet = io.BytesIO()
            output.write(final_packet)
            pdf_content = final_packet.getvalue()

        except Exception as e:
            _logger.error(f"Error al aplicar el fondo dinámico UX335 en PyPDF2: {e}")
            
        return pdf_content
