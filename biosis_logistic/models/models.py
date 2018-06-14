# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleLineaRepresentante(models.Model):
    _name = 'sale.linea.representante'

    name = fields.Char(string='Representante', required=True)
    linea_ids = fields.Many2many('sale.linea', string=u'Líneas navieras representadas')


class SaleLinea(models.Model):
    _name = "sale.linea"
    _description = u"Linea naviera"

    name = fields.Char(string=u'Linea', required=True)
    representante_ids = fields.Many2many('sale.linea.representante', string='Representante', required=True)
    vacio_ids = fields.Many2many('sale.vacio', string='Stock de vacíos')
    agente_ids = fields.Many2many('sale.agente.portuario', string='Agentes portuarios')


class SaleDeposito(models.Model):
    _name = "sale.deposito"
    _description = u"Depósito"

    name = fields.Char(string=u'Depósito', required=True)


class SaleVacio(models.Model):
    _name = "sale.vacio"
    _description = u"Vacios"

    name = fields.Char(string=u'Stock de vacío', required=True)
    linea_ids = fields.Many2many('sale.linea', string='Lineas navieras')


class SaleTipoVacio(models.Model):
    _name = "sale.tipo.vacio"
    _description = u"Tipo Vacios"

    name = fields.Char(string=u'Tipo Vacios', required=True)


class SaleAgenteAduana(models.Model):
    _name = "sale.agente.aduana"
    _description = u"Agente de Aduana"

    name = fields.Char(string=u'Agente de Aduana', required=True)


class SaleAgentePortuario(models.Model):
    _name = "sale.agente.portuario"
    _description = u"Agente Portuario"

    name = fields.Char(string=u'Agente Portuario', required=True)
    linea_ids = fields.Many2many('sale.linea', string=u'Líneas portuarias')


class TipoContenedor(models.Model):
    _name = 'sale.contenedor.tipo'
    _description = 'Tipo de contenedor'

    name = fields.Char('Nombre')


class ModalidadPago(models.Model):
    _name = 'sale.pago.modalidad'
    _description = 'Modalidad de pago'

    name = fields.Char('Modalidad')


class Transporte(models.Model):
    _name = 'sale.transporte'

    name = fields.Char('Transporte')
    zona_ids = fields.Many2many('sale.zona', string='Zonas')


class Resguardo(models.Model):
    _name = 'sale.resguardo'

    name = fields.Char('Resguardo')
    zona_ids = fields.Many2many('sale.zona', string='Zonas')


class Zona(models.Model):
    _name = 'sale.zona'

    name = fields.Char('Zona')
    resguardo_ids = fields.Many2many('sale.resguardo', string='Empresas de resguardo')
    transporte_ids = fields.Many2many('sale.transporte', string='Empresas de transporte')
