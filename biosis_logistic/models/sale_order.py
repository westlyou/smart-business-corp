# -*- coding: utf-8 -*-
import locale
import logging
import time
import urllib2
from datetime import datetime, date, timedelta

import bs4

from odoo import models, fields, api, _
# Permite filtrar resultados acorde a lo que se seleccione
from odoo.exceptions import ValidationError

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
    (u'profit', u'Profit'),
    (u'senasa', u'SENASA'),
    (u'certificado_origen', u'Certificado de orígen'),
    (u'otros', u'Otros'),
)

APPROVAL_STATE = (
    (u'no_notificado', u'Por notificar al supervisor'),
    (u'notificado', u'Notificado al supervisor'),
    (u'aprobado', u'Aprobado por el supervisor'),
    (u'no_aprobado', u'No aprobado por el supervisor'),
)

TIPO_SERVICIO_DICT = {key: value for key, value in ORDER_LINE_TIPO}


# TIPO_SERVICIO_DICT = {
#     u'deposito': u'Depósito',
#     u'vacio': u'Vacío',
#     u'agente_aduana': u'Agente aduana',
#     u'agente_portuario': u'Agente portuario',
#     u'transporte': u'Transporte',
#     u'resguardo': u'Resguardo',
#     u'cuadrilla': u'Cuadrilla',
#     u'otros': u'Otros',
#     u'aforo': u'Aforo/Inspección',
#     u'profit': u'Profit',
#     u'senasa': u'SENASA',
#     u'agente_carga': u'Agente de carga',
# }


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends('order_line.price_total', 'cantidad_contenedores')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                if order.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                    product=line.product_id, partner=order.partner_shipping_id)
                    amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    amount_tax += line.price_tax
                cantidad = line.product_uom_qty
                punitario = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                impuestos = line.tax_id.compute_all(punitario, line.order_id.currency_id, cantidad,
                                                    product=line.product_id, partner=order.partner_shipping_id)
                amount_untaxed += impuestos['total_excluded']
            order.update({
                'total_sin_ganancia': amount_untaxed - self.ganancia,
                'total_con_ganancia': amount_untaxed,
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
    partner_atencion_id = fields.Many2one('res.partner', u'Contacto de atención')
    linea_id = fields.Many2one('sale.linea', string=u'Linea')
    deposito_id = fields.Many2one('product.product', string=u'Depósito')
    vacio_id = fields.Many2one('product.product', string=u'Vacio')
    agente_aduana_id = fields.Many2one('product.product', string=u'Agente de Aduana')
    agente_portuario_id = fields.Many2one('product.product', string=u'Agente Portuario')
    agente_carga_id = fields.Many2one('product.product', string=u'Agente de carga')
    valor_tipo_cambio = fields.Float(string=u'Valor tipo de cambio', store=True, digits=(4, 3))
    tipo_contenedor_id = fields.Many2one('sale.contenedor.tipo', string=u'Tipo de contenedor')
    tipo_contenedor_name = fields.Char(related='tipo_contenedor_id.name')
    tipo_contenedor_energia = fields.Boolean(related='tipo_contenedor_id.energia')
    payment_method_id = fields.Many2one('account.payment.method', u'Método de pago')
    transporte_id = fields.Many2one('product.product', string='Transporte')
    resguardo_id = fields.Many2one('product.product', string='Resguardo')
    cuadrilla_id = fields.Many2one('product.product', string='Cuadrilla')
    total_sin_ganancia = fields.Float('Precio inicial')
    ganancia = fields.Float('Ganancia')
    total_con_ganancia = fields.Float('Precio final')
    codigo_consulta = fields.Char(u'Código para consultar')
    order_quest_ids = fields.One2many('sale.order.quest', 'order_id', u'Cuestionario')
    senasa = fields.Boolean(u'SENASA')
    dias_energia = fields.Integer(u'Días de energía')
    dias_almacenaje = fields.Integer(u'Días de almacenaje')
    certificado_origen = fields.Boolean(u'Certificado de orígen')
    termoregistro = fields.Boolean(u'Termoregistro')
    approval_state = fields.Selection(APPROVAL_STATE, u'Aprobación interna', default=u'no_notificado')
    tipo_despacho = fields.Selection([(u'sada', u'SADA'), (u'diferido', u'DIFERIDO')], u'Tipo de despacho')
    cantidad_contenedores = fields.Integer(u'Cantidad de contenedores', default=1)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Anulada'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    @api.multi
    def cargar_cuestonario(self):
        if self.actividad == 'E':
            quest_ids = self.env['sale.quest'].search([('exportacion', '=', True)], order='sequence asc')
        else:
            quest_ids = self.env['sale.quest'].search([('importacion', '=', True)], order='sequence asc')
        order_quest_ids = []
        for quest in quest_ids:
            if quest.aplica(self):
                order_quest_ids.append((0, False, {
                    'quest_id': quest.id,
                    'costo': quest.default or False
                }))
        self.order_quest_ids = [(6, False, [])]
        self.order_quest_ids = order_quest_ids

    @api.multi
    def action_confirm(self):
        if self.approval_state != u'aprobado':
            raise ValidationError(
                _('No se puede confirmar un pedido de venta que no haya sido aprobado por el responsable'))
        ret = super(SaleOrder, self).action_confirm()
        code = 'sbc.referencia.%s' % (self.actividad == 'E' and 'exportacion' or 'importacion')
        secuencia = self.env['ir.sequence'].search([('code', '=', code)], limit=1)
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

    @api.onchange('senasa')
    def onchange_senasa(self):
        if self.senasa:
            return self._agregar_servicio(u'senasa', 0.0)

    @api.onchange('certificado_origen')
    def onchange_certificado_origen(self):
        if self.certificado_origen:
            return self._agregar_servicio(u'certificado_origen', 0.0)

    @api.onchange('ganancia')
    def onchange_ganancia(self):
        if self.ganancia >= 0:
            return self._agregar_servicio(u'profit', self.ganancia)

    @api.onchange('cantidad_contenedores')
    def onchange_cantidad_contenedores(self):
        if self.cantidad_contenedores > 0:
            if self.order_line:
                for line in self.order_line:
                    if line.por_contenedor:
                        line.update({
                            u'product_uom_qty': self.cantidad_contenedores
                        })

    def _agregar_servicio(self, servicio, monto=0.0):
        # tipo = u'profit'
        product_id_nuevo = self.env['product.product'].search([('tipo_servicio', '=', servicio)], limit=1)
        return self._cambiar_order_line(servicio, product_id_nuevo, monto)

    def _json_line(self, line):
        return (0, False, {
            u'tipo': line.tipo,
            u'product_id': line.product_id.id,
            u'product_uom': 1,
            u'price_unit': line.price_unit,
            u'product_uom_qty': line.por_contenedor and self.cantidad_contenedores or 1,
            u'tax_id': line.tax_id,
            u'name': line.name,
            u'por_contenedor': line.por_contenedor
        })

    def _cambiar_order_line(self, tipo, product_id_nuevo, price_unit=0.0):
        # res = {'value': {}}
        res = dict(value=dict())
        # order_lines = []
        # encontrado = False
        desc = TIPO_SERVICIO_DICT[tipo]

        # Descartamos las lineas que pertenezcan a un determinado tipo de tal forma que podemos sobreescribir
        order_lines = [self._json_line(line) for line in self.order_line if line.tipo != tipo]

        if tipo in (u'agente_portuario', u'vacio'):
            conceptos = product_id_nuevo.conceptos_contenedor + product_id_nuevo.conceptos_administrativo
            order_lines = order_lines + [(0, False, {
                u'tipo': tipo,
                u'product_id': product_id_nuevo.id,
                u'product_uom': 1,
                u'price_unit': concepto.precio,
                u'product_uom_qty': (concepto.tipo == u'contenedor') and self.cantidad_contenedores or 1,
                u'tax_id': [(6, False, [tax.id for tax in product_id_nuevo.taxes_id])],
                u'name': u'{}: {}'.format(product_id_nuevo.name, concepto.name),
                u'por_contenedor': concepto.tipo == u'contenedor'
            }) for concepto in conceptos]
        else:
            order_lines.append((0, False, {
                u'tipo': tipo,
                u'product_id': product_id_nuevo.id,
                u'product_uom': 1,
                u'price_unit': price_unit or product_id_nuevo.list_price,
                u'product_uom_qty': 1,
                u'tax_id': [(6, False, [tax.id for tax in product_id_nuevo.taxes_id])],
                u'name': '%s - %s' % (desc, product_id_nuevo.name)
            }))

        # if self.order_line:
        #     i = 0
        #     for line in self.order_line:
        #         bandera = line.tipo == tipo
        #         if bandera:
        #             encontrado = True
        #
        #         order_lines.append((0, False, {
        #             u'tipo': bandera and tipo or line.tipo,
        #             u'product_id': bandera and product_id_nuevo.id or line.product_id.id,
        #             u'product_uom': 1,
        #             u'sequence': line.sequence,
        #             u'price_unit': bandera and (tipo == u'profit' and 0.0 or (
        #                 (price_unit or product_id_nuevo.lst_price)) or line.price_unit),
        #             u'product_uom_qty': 1,
        #             u'tax_id': bandera and [(6, False, [tax.id for tax in product_id_nuevo.taxes_id])] or line.tax_id,
        #             u'name': bandera and '%s - %s' % (desc, product_id_nuevo.name) or line.name
        #         }))
        # if not encontrado:
        #     if tipo in (u'agente_portuario', u'vacio'):
        #     # Procedemos a leer los conceptos
        #
        #     order_lines.append((0, False, {
        #         u'tipo': tipo,
        #         u'product_id': product_id_nuevo.id,
        #         u'product_uom': 1,
        #         u'sequence': self.order_line and len(self.order_line) * 10 or 0,
        #         u'price_unit': price_unit or product_id_nuevo.lst_price,
        #         u'product_uom_qty': 1,
        #         u'tax_id': [(6, False, [tax.id for tax in product_id_nuevo.taxes_id])],
        #         u'name': '%s - %s' % (desc, product_id_nuevo.name)
        #     }))

        self.order_line = order_lines
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

    def formatear_date(self, date, formato):
        try:
            locale.setlocale(locale.LC_TIME, 'es_PE.UTF-8')
        except Exception as e:
            _logger.error("ERROR AL INTENTAR FORMATEAR LA FECHA Y HORA")
            locale.setlocale(locale.LC_TIME, '')
        _logger.info('locale.getlocale(): {}'.format(locale.getlocale()))
        formato_nice = time.strftime(formato, time.strptime(date, '%Y-%m-%d %H:%M:%S'))
        return formato_nice

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        ret = super(SaleOrder, self).create(vals)
        return ret

    @api.multi
    def write(self, vals):
        resultado = super(SaleOrder, self).write(vals)
        return resultado

    @api.multi
    def enviar_contrato(self):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('biosis_logistic', 'email_template_sbc_cotizacion')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict()
        ctx.update({
            'default_model': 'sale.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "biosis_logistic.sbc_mail_template"
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.multi
    def notificar_supervisor(self):
        partner_ids = self.env.ref('sales_team.group_sale_manager').users.filtered(lambda u: u.id != 1).mapped(
            'partner_id').ids
        if partner_ids:
            ctx = {'res_model': 'sale.order', 'res_id': self.id}
            vals = {
                'res_model': 'sale.order',
                'res_id': self.id,
                'partner_ids': [(6, False, partner_ids)],
                'message': "<p>Se ha emitido la cotización <strong>{}</strong> y se le ha agregado como seguidor.</p>".format(
                    self.name),
                'send_mail': True

            }
            invite = self.env['mail.wizard.invite'].with_context(ctx).create(vals)
            invite.add_followers()
            self.write({u'approval_state': u'notificado'})

    @api.multi
    def aprobar_cotizacion(self):
        self.write({u'approval_state': u'aprobado'})

    @api.multi
    def no_aprobar_cotizacion(self):
        self.write({u'approval_state': u'no_aprobado'})

    @api.multi
    def contract_subject(self):
        template = u'COTIZACIÓN ({}) - SMART BUSINESS CORPORATION S.A.C. - {} // {} // {}'

        if self.actividad == 'E':
            actividad = u'EXPORTACIÓN'
        else:
            actividad = u'IMPORTACIÓN'
        partner = self.partner_id.name
        order = self.name
        if self.via == 'M':
            if self.modalidad == 'FCL':
                sufix = u'FCL // {} // {}'.format(self.linea_id.name, self.tipo_contenedor_id.name)
            else:
                sufix = u'LCL'
        else:
            sufix = u'AÉREO'

        render = template.format(actividad, partner, order, sufix)
        return render


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    tipo = fields.Selection(ORDER_LINE_TIPO, default='otros')
    por_contenedor = fields.Boolean(u'Cambia por contenedor', default=False)
