# coding=utf-8
from odoo import fields, models
from odoo.addons import decimal_precision as dp

TIPO_CONCEPTO = [
    (u'contenedor', u'Gastos por contenedor'),
    (u'administrativo', u'Gastos administrativos')
]


class ProductConcepto(models.Model):
    _name = 'product.concepto'

    tipo = fields.Selection(TIPO_CONCEPTO, u'Tipo de concepto', required=True)
    name = fields.Char(u'Concepto', required=True)
    precio = fields.Float(u'Costo', required=True, digits=dp.get_precision('Product Price'))
    descripcion = fields.Char(u'Descripción')
    product_id = fields.Many2one('product.template', u'Producto')
