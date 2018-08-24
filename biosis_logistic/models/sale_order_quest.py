# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp


class SaleQuest(models.Model):
    _name = 'sale.quest'

    template_html = fields.Html(u'Template para mostrar')
    name = fields.Char(u'Nombre')
    default = fields.Float(u'Costo por defecto', digits=dp.get_precision('Account'))


class SaleOrderQuest(models.Model):
    _name = 'sale.order.quest'

    quest_id = fields.Many2one('sale.quest', required=True)
    order_id = fields.Many2one('sale.order', required=True)
    costo = fields.Float(u'Costo', digits=dp.get_precision('Account'))

    @api.onchange('quest_id')
    def onchange_quest_id(self):
        self.costo = self.quest_id.default or 0.0
