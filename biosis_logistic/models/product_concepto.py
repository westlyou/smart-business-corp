# coding=utf-8
from odoo import fields, models

TIPO_CONCEPTO = [
    (u'contenedor', u'Gastos por contenedor'),
    (u'administrativo', u'Gastos administrativos')
]


class ProductConcepto(models.Model):
    _name = 'product.concepto'

    tipo = fields.Selection(TIPO_CONCEPTO, u'Tipo de concepto', required=True)
    name = fields.Char(u'Nombre deconcepto', required=True)
    precio = fields.Float(u'Costo', required=True)
    descripcion = fields.Char(u'Descripción')
