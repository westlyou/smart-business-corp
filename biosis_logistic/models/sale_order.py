# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import UserError, ValidationError
import bs4, urllib2, urllib
from datetime import datetime, date, timedelta
import calendar

# Permite filtrar resultados acorde a lo que se seleccione
_logger = logging.getLogger(__name__)

ORDER_LINE_TIPO = (
    (u'deposito', u'Depósito'),
    (u'vacio', u'Vacío'),
    (u'agente_aduana', u'Agente aduana'),
    (u'agente_portuario', u'Agente portuario'),
    (u'transporte', u'Transporte'),
    (u'resguardo', u'Resguardo'),
    (u'cuadrilla', u'Cuadrilla'),
    (u'agente_carga', u'Agente de carga'),
    (u'aforo', u'Aforo/Inspección'),
    (u'otros', u'Otros'),
)

TIPO_SERVICIO_DICT = {
    u'deposito': u'Depósito',
    u'vacio': u'Vacío',
    u'agente_aduana': u'Agente aduana',
    u'agente_portuario': u'Agente portuario',
    u'transporte': u'Transporte',
    u'resguardo': u'Resguardo',
    u'cuadrilla': u'Cuadrilla',
    u'otros': u'Otros',
    u'aforo': u'Aforo/Inspección',
    u'agente_carga': u'Agente de carga',
}


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                # FORWARDPORT UP TO 10.0
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id, partner=order.partner_shipping_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
            order.update({
                'total_sin_ganancia': amount_untaxed,
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax
            })

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

    referencia_sbc = fields.Char('Referencia SBC')
    linea_id = fields.Many2one('sale.linea', string=u'Linea')
    deposito_id = fields.Many2one('product.product', string=u'Depósito')
    vacio_id = fields.Many2one('product.product', string=u'Vacio')
    tipo_vacio_id = fields.Many2one('sale.tipo.vacio', string=u'Tipo Vacio')
    agente_aduana_id = fields.Many2one('product.product', string=u'Agente de Aduana')
    agente_portuario_id = fields.Many2one('product.product', string=u'Agente Portuario')
    agente_carga_id = fields.Many2one('product.product', string=u'Agente de carga')
    valor_tipo_cambio = fields.Float(string=u'Valor tipo de cambio', store=True, digits=(4, 3))
    tipo_contenedor_id = fields.Many2one('sale.contenedor.tipo', string=u'Tipo de contenedor')
    tipo_contenedor_name = fields.Char(related='tipo_contenedor_id.name')
    modalidad_pago_id = fields.Many2one('sale.pago.modalidad', string='Modalidad de pago')
    transporte_id = fields.Many2one('product.product', string='Transporte')
    resguardo_id = fields.Many2one('product.product', string='Resguardo')
    cuadrilla_id = fields.Many2one('product.product', string='Cuadrilla')
    zona_id = fields.Many2one('sale.zona', string='Zona')
    total_sin_ganancia = fields.Float('Precio inicial')
    ganancia = fields.Float('Ganancia')
    total_con_ganancia = fields.Float('Precio final')

    @api.multi
    def action_confirm(self):
        ret = super(SaleOrder, self).action_confirm()
        secuencia = self.env['ir.sequence'].search(
            [('code', '=', 'sbc.referencia.%s' % self.actividad == 'E' and 'exportacion' or 'importacion')], limit=1)
        if secuencia.exists():
            self.write({u'referencia_sbc': secuencia.next_by_id()})
        return ret

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

    @api.depends('linea_id')
    @api.onchange('deposito_id')
    def onchange_deposito_id(self):
        res = dict()
        res['value'] = dict()
        if self.deposito_id:
            return self._cambiar_order_line(u'deposito', self.deposito_id)

    @api.onchange('agente_portuario_id')
    def onchange_agente_portuario_id(self):
        res = dict()
        res['value'] = dict()
        if self.agente_portuario_id:
            return self._cambiar_order_line(u'agente_portuario', self.agente_portuario_id)

    @api.onchange('vacio_id')
    def onchange_vacio_id(self):
        res = dict()
        res['value'] = dict()
        if self.vacio_id:
            return self._cambiar_order_line(u'vacio', self.vacio_id)

    @api.onchange('transporte_id')
    def onchange_transporte_id(self):
        res = dict()
        res['value'] = dict()
        if self.transporte_id:
            return self._cambiar_order_line(u'transporte', self.transporte_id)

    @api.onchange('resguardo_id')
    def onchange_resguardo_id(self):
        res = dict()
        res['value'] = dict()
        if self.resguardo_id:
            return self._cambiar_order_line(u'resguardo', self.resguardo_id)

    @api.onchange('cuadrilla_id')
    def onchange_cuadrilla_id(self):
        res = dict()
        res['value'] = dict()
        if self.cuadrilla_id:
            return self._cambiar_order_line(u'cuadrilla', self.cuadrilla_id)

    @api.onchange('agente_aduana_id')
    def onchange_agente_aduana_id(self):
        res = dict()
        res['value'] = dict()
        if self.agente_aduana_id:
            return self._cambiar_order_line(u'agente_aduana', self.agente_aduana_id)

    @api.onchange('agente_carga_id')
    def onchange_agente_carga_id(self):
        res = dict()
        res['value'] = dict()
        if self.agente_carga_id:
            return self._cambiar_order_line(u'agente_carga', self.agente_carga_id)

    @api.onchange('via', 'modalidad', 'tipo_contenedor_id', 'linea_id')
    def onchange_modalidad(self):
        res = dict(domain=dict())

        # if self.modalidad:
        # aplica para tipo aereo
        if self.via == 'M':
            if self.modalidad == 'FCL':
                if self.tipo_contenedor_id is not False:
                    if self.linea_id is not False:
                        res['domain']['agente_portuario_id'] = ['&', '&', '&', '&',
                                                                ('tipo_servicio', '=', 'agente_portuario'),
                                                                ('maritimo', '=', True),
                                                                ('fcl', '=', True),
                                                                ('tipo_contenedor_ids', 'in',
                                                                 self.tipo_contenedor_id.ids),
                                                                ('linea_naviera_ids', 'in', self.linea_id.ids)]
                        res['domain']['vacio_id'] = ['&', '&', '&', '&',
                                                     ('tipo_servicio', '=', 'vacio'),
                                                     ('maritimo', '=', True),
                                                     ('fcl', '=', True),
                                                     ('tipo_contenedor_ids', 'in', self.tipo_contenedor_id.ids),
                                                     ('linea_naviera_ids', 'in', self.linea_id.ids)]
                    res['domain']['deposito_id'] = ['&', '&', '&',
                                                    ('tipo_servicio', '=', 'deposito'),
                                                    ('maritimo', '=', True),
                                                    ('fcl', '=', True),
                                                    ('tipo_contenedor_ids', 'in', self.tipo_contenedor_id.ids)]
                res['domain']['agente_aduana_id'] = ['&', '&',
                                                     ('tipo_servicio', '=', 'agente_aduana'),
                                                     ('maritimo', '=', True),
                                                     ('fcl', '=', True)]

            if self.modalidad == 'LCL':
                res['domain']['agente_portuario_id'] = [('tipo_servicio', '=', 'agente_portuario'),
                                                        ('lcl', '=', True)]
                res['domain']['deposito_id'] = [('tipo_servicio', '=', 'deposito'),
                                                ('lcl', '=', True)]
        if self.via == 'A':
            res['domain']['agente_aduana_id'] = [('tipo_servicio', '=', 'agente_aduana'),
                                                 ('aereo', '=', True)]
            res['domain']['deposito_id'] = [('tipo_servicio', '=', 'deposito'),
                                            ('aereo', '=', True)]
        if res['domain']:
            _logger.info('Resultado: %s' % res)
            return res

    @api.onchange('total_sin_ganancia')
    def onchange_amount_total(self):
        res = dict(value=dict(total_con_ganancia=(self.total_sin_ganancia + self.ganancia)))
        return res

    @api.onchange('total_con_ganancia')
    def onchange_total_con_ganancia(self):
        res = dict(value=dict(ganancia=(self.total_con_ganancia - self.total_sin_ganancia)))
        return res

    @api.onchange('ganancia')
    def onchange_ganancia(self):
        if self.ganancia < 350:
            raise ValidationError(u'Recuerde que el profit mínimo a considerar debe ser mayor o igual a 350')
        res = dict(value=dict(total_con_ganancia=(self.total_sin_ganancia + self.ganancia)))
        return res

    def _cambiar_order_line(self, tipo, product_id_nuevo):
        res = {'value': {}}
        order_lines = []
        encontrado = False
        desc = TIPO_SERVICIO_DICT[product_id_nuevo.tipo_servicio]
        if self.order_line:
            i = 0
            for line in self.order_line:
                bandera = line.tipo == tipo
                if bandera:
                    encontrado = True

                order_lines.append((0, False, {
                    u'procurement_ids': [],
                    u'tipo': bandera and tipo or line.tipo,
                    u'route_id': False,
                    u'qty_delivered': 0,
                    u'product_id': bandera and product_id_nuevo.id or line.product_id.id,
                    u'product_uom': 1,
                    u'sequence': line.sequence,
                    u'customer_lead': 0,
                    u'price_unit': bandera and product_id_nuevo.lst_price or line.price_unit,
                    u'product_uom_qty': 1,
                    u'discount': 0,
                    u'state': u'draft',
                    u'qty_delivered_updateable': True,
                    u'analytic_tag_ids': [],
                    u'invoice_status': u'no',
                    u'tax_id': [[6, False, [1]]],
                    u'layout_category_id': False,
                    u'name': bandera and '%s - %s' % (desc, product_id_nuevo.name) or line.name
                }))
        if not encontrado:
            order_lines.append((0, False, {
                u'procurement_ids': [],
                u'tipo': tipo,
                u'route_id': False,
                u'qty_delivered': 0,
                u'product_id': product_id_nuevo.id,
                u'product_uom': 1,
                u'sequence': self.order_line and len(self.order_line) * 10 or 0,
                u'customer_lead': 0,
                u'price_unit': product_id_nuevo.lst_price,
                u'product_uom_qty': 1,
                u'discount': 0,
                u'state': u'draft',
                u'qty_delivered_updateable': True,
                u'analytic_tag_ids': [],
                u'invoice_status': u'no',
                u'tax_id': [[6, False, [1]]],
                u'layout_category_id': False,
                u'name': '%s - %s' % (desc, product_id_nuevo.name)
            }))

        res['value']['order_line'] = order_lines
        self._amount_all()
        return res

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


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    tipo = fields.Selection(ORDER_LINE_TIPO, default='otros')
