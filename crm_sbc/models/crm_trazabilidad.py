# coding=utf-8
from odoo import models, fields, api

class CrmTrazabilidad(models.Model):
    _name='crm.trazabilidad'

    sale_order_id=fields.Many2one('sale.order', string=u'cotización')

    partner_id=fields.Many2one('res.partner', string=u'Cliente')
    partner_ruc=fields.Char(related='partner_id.vat')

    etd=fields.Date(string=u'ETD')
    eta=fields.Date(string=u'ETA')
    cita_planta=fields.Date(string=u'Cita Planta')
    mes=fields.Integer(string=u'Mes CitaPlanta')
    fechaRetiro_contendor=fields.Date(string=u'RetiroContendor')
    referencia_cliente=fields.Text(string=u'ReferenciaCliente')
    puerto_embarque=fields.Text(string=u'Puerto de Embarque')
    puerto_destino=fields.Text(string=u'Puerto de Destino')
    numero_dam=fields.Text(string=u'Nª de DAM')
    e_canal = fields.Char(string=u'Canal')
    i_canal = fields.Char(string=u'Canal')
    sale_order_id=fields.Many2one('sale.order')
    sale_order_referencia=fields.Char(related='sale_order_id.referencia')
    po_=fields.Char(string=U'Po')
    booking=fields.Char(string=u'Booking')
    n_bl=fields.Char(strig=u'Nª Bl')
    n_contenedor=fields.Char(string=u'Número Contenedor')
    sale_order_id_tipo_contendor_id=fields.Many2one('sale.contenedor.tipo',related='sale_order_id.tipo_contendor_id')
    consignatorio=fields.Char(string=u'Consginatorio')
    factura_consignatario=fields.Char(string=u'Número Consignatrio')
    fob=fields.Char(string=u'FOB')
    cif=fields.Char(string=u'CIF')
    nave=fields.Char(string=u'Nave')
    viaje=fields.Char(string=u'Viaje')
    fecha_vencimiento=fields.Date(string=u'fecha Vencimiento')
    incoterm=fields.Char(string=u'Incoterm')
    observacion = fields.Char(string=u'_observación')
    vencimiento_estadia=fields.Date(string=u'Vencimiento de Estadia')
    vencimiento_almacenaje=fields.Date(string=u'Vencimiento Almacenaje')
    estado_regulirazcion_id=fields.Many2one('cmr.estado_regularizacion')