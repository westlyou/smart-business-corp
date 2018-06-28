# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleLinea(models.Model):
    _name = "sale.linea"
    _description = u"Linea naviera"

    name = fields.Char(string=u'Linea', required=True)
    representante_ids = fields.Many2many('res.partner', string='Representante(s)', required=True)
    vacio_ids = fields.Many2many('product.product', string=u'Vacíos')
    agente_portuario_ids = fields.Many2many('product.product', string=u'Agentes portuarios')


class TipoContenedor(models.Model):
    _name = 'sale.contenedor.tipo'
    _description = 'Tipo de contenedor'

    name = fields.Char('Nombre')


# class Zona(models.Model):
#     _name = 'sale.zona'
#
#     name = fields.Char('Zona')
#     resguardo_ids = fields.Many2many('sale.resguardo', string='Empresas de resguardo')
#     transporte_ids = fields.Many2many('sale.transporte', string='Empresas de transporte')
