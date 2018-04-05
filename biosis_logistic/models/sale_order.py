# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import UserError, ValidationError
import bs4, urllib2, urllib
from datetime import datetime, date, timedelta
import calendar


class SaleOrder(models.Model):
    _inherit = "sale.order"

    via = fields.Selection([
        ('A', u'Aéreo'),
        ('M', u'Marítimo')
    ], string=u'Vía', required=True, default="A")
    actividad = fields.Selection([
        ('E', u'Exportación'),
        ('I', u'Importación')
    ], string=u'Actividad', required=True, default="E")
    modalidad = fields.Selection([
        ('FCL', u'Full Container Load'),
        ('LCL', u'Less Container Load')
    ], string=u'Tipo', required=True, default="FCL")

    linea_id = fields.Many2one('sale.linea', string=u'Linea')
    deposito_id = fields.Many2one('sale.deposito', string=u'Depósito')
    vacio_id = fields.Many2one('sale.vacio', string=u'Vacio')
    tipo_vacio_id = fields.Many2one('sale.tipo.vacio', string=u'Tipo Vacio')
    agente_aduana_id = fields.Many2one('sale.agente.aduana', string=u'Agente de Aduana')
    agente_portuario_id = fields.Many2one('sale.agente.portuario', string=u'Agente Portuario')
    valor_tipo_cambio = fields.Float(string=u'Valor tipo de cambio', store=True, digits=(4, 3))
    tipo_contenedor_id = fields.Many2one('sale.contenedor.tipo', string='Tipo de contenedor')
    modalidad_pago_id = fields.Many2one('sale.pago.modalidad', string='Modalidad de pago')
    transporte_id = fields.Many2one('sale.transporte', string='Transporte')
    resguardo_id = fields.Many2one('sale.resguardo', string='Resguardo')
    zona_id = fields.Many2one('sale.zona', string='Zona')

    def mapear_tc(self, mes, anio):
        web = urllib2.urlopen(
            "http://www.sunat.gob.pe/cl-at-ittipcam/tcS01Alias?mes=" + mes + "&anho=" + anio + "")
        soup = bs4.BeautifulSoup(web, 'lxml')
        # soup.prettify()
        listado = []
        tabla = soup.find_all('table')[1]

        tds = tabla.find_all('td')

        if len(tds) == 13:
            return False

        for i in xrange(12, len(tds), 3):
            dia = tds[i].text.strip()
            fecha_inicio = '-'.join((anio, mes, dia))
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            compra = float(tds[i + 1].text.strip())
            venta = float(tds[i + 2].text.strip())

            if len(listado) >= 1:
                listado[len(listado) - 1]['fecha_fin'] = fecha_inicio

            listado.append({
                'fecha_inicio': fecha_inicio,
                'fecha_fin': None,
                'compra': compra,
                'venta': venta
            })
        return listado

    def tipo_cambio(self, fecha):
        anio, mes, dia = fecha.split('-')

        fecha_date = datetime.strptime(fecha, '%Y-%m-%d').date()

        if date.today() < fecha_date:
            return False

        tcs = self.mapear_tc(mes, anio)

        if tcs:
            for tc in tcs:
                if tc['fecha_inicio'] <= fecha_date and (tc['fecha_fin'] is None or fecha_date < tc['fecha_fin']):
                    return {'compra': tc['compra'], 'venta': tc['venta']}
        else:
            fecha_anterior = fecha_date - timedelta(days=1)
            return self.tipo_cambio(fecha_anterior.strftime('%Y-%m-%d'))

    @api.multi
    @api.onchange('date_order')
    def onchange_date_order(self):
        value_tipo_cambio = 'V'
        if value_tipo_cambio == 'V' or value_tipo_cambio == 'C':
            self.invoice_line_ids = {}
            fecha = self.date_order
            if fecha != False:
                dia = fecha[8:10]
                mes = fecha[5:7]
                anho = fecha[0:4]

                tipo_cambio = self.tipo_cambio('-'.join((anho, mes, dia)))

                if tipo_cambio:
                    self.valor_tipo_cambio = value_tipo_cambio == 'V' and tipo_cambio['venta'] or tipo_cambio['compra']
                else:
                    self.valor_tipo_cambio = 0.0

        else:
            self.valor_tipo_cambio = 0.0

            # def get_tc_web(self, mes, anho, dia):

    @api.multi
    def generar_order_lines(self):
        order_lines = []
        line_vals = {
            'product_id': False,
            'name': False,
            'product_uom_qty': 1,
            'price_unit': 1.0,
            'tax_id': False,
            'product_uom': False
        }

        order_id = self.id
        product_obj = self.env['product.product']
        line_obj = self.env['sale.order.line']

        portuario = product_obj.search([('default_code', '=', 'AGNTPORTUARIO')])
        vacio = product_obj.search([('default_code', '=', 'ALMVAC')])
        ingreso = product_obj.search([('default_code', '=', 'ALMING')])

        unidad = self.env['product.uom'].browse([1])

        line_portuario = line_obj.create({
            'product_id': portuario.id,
            'name': self.agente_portuario_id.name,
            'product_uom_qty': 1,
            'product_uom': unidad.id,
            'tax_id': False,
            'price_unit': 1.0,
            'order_id': order_id
        })

        line_vacio = line_obj.create({
            'product_id': vacio.id,
            'name': self.vacio_id.name,
            'product_uom_qty': 1,
            'product_uom': unidad.id,
            'tax_id': False,
            'price_unit': 1.0,
            'order_id': order_id
        })

        order_lines.append(line_portuario.id)
        order_lines.append(line_vacio.id)

        self.order_line = [(6, 0, order_lines)]
