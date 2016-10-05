# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GNSS3DCapture
                                 A QGIS plugin
 A plugin for capture 3D points from GNSS equipment
                             -------------------
        begin                : 2016-10-05
        copyright            : (C) 2016 by David Hernández López, Insittuto de Desarrollo Regional - UCLM
        email                : david.hernandez@uclm.es
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load GNSS3DCapture class from file GNSS3DCapture.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .gnss_3d_capture import GNSS3DCapture
    return GNSS3DCapture(iface)
