# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp


class SaleQuest(models.Model):
    _name = 'sale.quest'

    sequence = fields.Integer('Orden')
    template_html = fields.Html(u'Template para mostrar')
    name = fields.Char(u'Nombre')
    default = fields.Float(u'Costo por defecto', digits=dp.get_precision('Account'))
    active = fields.Boolean(u'Archivado', default=True)
    tiene_variable = fields.Boolean(u'Tiene variable', default=True)
    tiene_condicion = fields.Boolean(u'Condición')
    condicion = fields.Char(u'Código python')
    importacion = fields.Boolean(u'Aplica para importación', default=False)
    exportacion = fields.Boolean(u'Aplica para exportación', default=False)

    @api.multi
    def aplica(self, order_id):
        quest_id = self
        if quest_id.tiene_condicion:
            condicion = eval(quest_id.condicion)
        else:
            condicion = True
        return condicion


class SaleOrderQuest(models.Model):
    _name = 'sale.order.quest'

    quest_id = fields.Many2one('sale.quest', u'Pregunta',required=True)
    order_id = fields.Many2one('sale.order', u'Pedido de venta')
    quest_tiene_variable = fields.Boolean(related='quest_id.tiene_variable')
    costo = fields.Float(u'Costo', digits=dp.get_precision('Account'))
    ejemplo = fields.Html(u'Ejemplo', compute='_compute_ejemplo')

    @api.onchange('quest_id')
    def onchange_quest_id(self):
        self.costo = self.quest_id.default or 0.0

    @api.depends('costo')
    def _compute_ejemplo(self):
        self.ejemplo = self.render()

    @api.multi
    def render(self):
        if self.quest_id.template_html and self.quest_id.tiene_variable:
            template_html = self.quest_id.template_html.format('%.2f' % (self.costo or 0.0))
            return template_html
        return self.quest_id.template_html
