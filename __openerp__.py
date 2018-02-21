# -*- encoding: utf-8 -*-

#
# Status 1.0 - tested on Open ERP 8
#

{
    'name': 'Produccion',
    'version': '1.0',
    'category': 'Custom',
    'description': """
Adaptaciones al módulo de producción
""",
    'author': 'Rodrigo Fernandez',
    'website': 'http://solucionesprisma.com/',
    'depends': ['mrp'],
    'data': [
            'reports.xml',
            'views/costo_produccion.xml',
            'views/sale_view.xml',
            'wizard/asignar_costos.xml',
    ],
    'demo': [],
    'installable': True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
