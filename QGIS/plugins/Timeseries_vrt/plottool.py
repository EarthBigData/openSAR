# -*- coding: utf-8 -*-
import os
import pkgutil

# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import QgsMapToolEmitPoint, QgsMessageBar

# Initialize Qt resources from file resources.py
import resources_rc

class plottool(QObject):

	def __init__(self, iface):
		#super(plottool, self).__init__()
		# Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n', 'Timeseries_vrt_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Location info - define these elsewhere #TODO
        self.location = os.getcwd()

        # Toolbar
        self.init_toolbar()

        # Map tool on/off
        self.tool_enabled = True