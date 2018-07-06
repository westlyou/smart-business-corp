# coding=utf-8
from odoo import models, fields, api

class CrmEstadoRegularizacion(models.Model):
    _name='crm.estado_regularizacion'
    name=fields.Char(string=u'Estado')
    tipo_operacion= fields.Selection(('i',u'Importación'),('e',u'Exportación'))
