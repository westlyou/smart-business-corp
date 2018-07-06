# coding=utf-8
from odoo import models, fields, api


class CrmContacto(models.Model):
    _name = 'crm.contacto'
    nombre=fields.Char(string=u'Nombre')
    compania=fields.Char(string=u'Compania')
    correo=fields.Char(string=u'Correo')
    telefono=fields.Char(string=u'Telefono')
    motivo=fields.Char(string=u'Motivo')
    mensaje=fields.Text(string=u'Mensaje')

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        partner_vals = {
            'name': vals['nombre'],
             ''
        }
        return super(CrmContacto, self).create(vals)


