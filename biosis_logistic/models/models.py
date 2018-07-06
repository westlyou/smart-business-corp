# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleLinea(models.Model):
    _name = "sale.linea"
    _description = u"Linea naviera"

    name = fields.Char(string=u'Linea', required=True)
    representante_ids = fields.Many2many('res.partner', string='Representante(s)', required=True)
    vacio_ids = fields.Many2many('product.template', string=u'Vacíos', domain=[('tipo_servicio', '=', 'vacio')])
    agente_portuario_ids = fields.Many2many('product.template', string=u'Agentes portuarios',
                                            domain=[('tipo_servicio', '=', 'agente_portuario')])


class TipoContenedor(models.Model):
    _name = 'sale.contenedor.tipo'
    _description = 'Tipo de contenedor'

    name = fields.Char('Nombre')
