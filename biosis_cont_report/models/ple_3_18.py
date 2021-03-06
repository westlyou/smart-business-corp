# -*- coding: utf-8 -*-
import datetime
import re
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta

class Ple_3_18(models.Model):
    _name = 'account.ple.3.18'
    _description = u'LIBRO DE INVENTARIOS Y BALANCES - ESTADO DE FLUJOS DE EFECTIVO - MÉTODO DIRECTO'

    periodo_1 = fields.Char(string=u'Periodo', required=True)
    cod_catalog_2 = fields.Char(string=u'Código del catálogo', required=True)
    cod_rubro_3 = fields.Char(string=u'Código del Rubro del Estado Financiero', required=True)
    saldro_rubro_4 = fields.Char(string=u'Saldo del Rubro Contable', required=True)
    estado_5 = fields.Char(string=u'Estado', required=True)
    ##invoice_id = fields.Many2one('account.invoice', string=u'Documento relacionado')