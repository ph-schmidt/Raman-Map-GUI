"""Qt Designer-style UI definition for the main application window.

This module provides the :class:`Ui_MainWindow` helper class, which constructs
and lays out all widgets, menus, and actions for the main Raman GUI window.
It is responsible only for UI creation and translation, not application logic.
"""

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtGui import QAction

from ramangui.histogram_widget import HistoWidget
from ramangui.statistic_widget import StatisticWidget
from ramangui.view_widget import ViewWidget


class Ui_MainWindow:
    """UI builder class for the main application window.

    This class follows the Qt Designer pattern, separating widget creation
    (:meth:`setupUi`) from text translation (:meth:`retranslateUi`).
    """

    def setupUi(self, MainWindow):
        """Set up widgets, layouts, menus, and actions for the main window.

        Args:
            MainWindow: The :class:`QMainWindow` instance to populate with UI elements.
        """
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1702, 1026)

        self.l = QtWidgets.QGridLayout()
        self.l2 = QtWidgets.QGridLayout()
        self.l.addLayout(self.l2, 1, 1, 1, 1)

        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum, QtWidgets.QSizePolicy.Policy.Maximum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.widget = ViewWidget(args=None)
        # self.widget.setGeometry(QtCore.QRect(50, 60, 841, 801))
        self.l.addWidget(self.widget, 2, 1, 2, 1)
        self.widget.setObjectName("widget")

        self.comboBox_Plot = QtWidgets.QComboBox()
        # self.comboBox_Plot.setGeometry(QtCore.QRect(720, 25, 171, 35))
        self.l2.addWidget(self.comboBox_Plot, 0, 4, 1, 1)
        self.comboBox_Plot.setObjectName("comboBox_Plot")

        self.buttonNewFit = QtWidgets.QPushButton()
        # self.buttonNewFit.setGeometry(QtCore.QRect(60, 30, 111, 31))
        self.l2.addWidget(self.buttonNewFit, 0, 0, 1, 1)
        self.buttonNewFit.setObjectName("buttonNewFit")

        self.widget_stat = StatisticWidget(args=None)
        # self.widget_stat.setGeometry(QtCore.QRect(990, 20, 711, 381))
        self.l.addWidget(self.widget_stat, 1, 2, 2, 1)
        self.widget_stat.setObjectName("widget_stat")

        self.widget_histo = HistoWidget(args=None)
        # self.widget_histo.setGeometry(QtCore.QRect(990, 480, 711, 381))
        self.l.addWidget(self.widget_histo, 3, 2, 1, 1)
        self.widget_histo.setObjectName("widget_histo")

        self.buttonResetROI = QtWidgets.QPushButton()
        # self.buttonResetROI.setGeometry(QtCore.QRect(490, 30, 75, 31))
        self.l2.addWidget(self.buttonResetROI, 0, 3, 1, 1)
        self.buttonResetROI.setObjectName("buttonResetROI")

        self.checkBox_ROI = QtWidgets.QCheckBox()
        # self.checkBox_ROI.setGeometry(QtCore.QRect(360, 40, 101, 17))
        self.l2.addWidget(self.checkBox_ROI, 0, 1, 1, 1)
        self.checkBox_ROI.setObjectName("checkBox_ROI")

        self.checkBox_ROI_circle = QtWidgets.QCheckBox()
        # self.checkBox_ROI.setGeometry(QtCore.QRect(360, 40, 101, 17))
        self.l2.addWidget(self.checkBox_ROI_circle, 0, 2, 1, 1)
        self.checkBox_ROI_circle.setObjectName("checkBox_ROI_circle")

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 500, 20))
        self.menubar.setObjectName("menubar")

        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuExport = QtWidgets.QMenu(self.menubar)
        self.menuExport.setObjectName("menuExport")
        self.menuSettings = QtWidgets.QMenu(self.menubar)
        self.menuSettings.setEnabled(True)
        self.menuSettings.setObjectName("menuSettings")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionNew = QAction(MainWindow)
        self.actionNew.setObjectName("actionNew")
        self.actionOpen = QAction(MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.actionSave = QAction(MainWindow)
        self.actionSave.setObjectName("actionSave")
        self.actionSave_As = QAction(MainWindow)
        self.actionSave_As.setObjectName("actionSave_As")
        self.actionLoad_Map = QAction(MainWindow)
        self.actionLoad_Map.setObjectName("actionLoad_Map")
        self.menuFile.addAction(self.actionNew)
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addSeparator()
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionLoad_Map)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuExport.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.l.setRowStretch(1, 1)
        self.l.setRowStretch(2, 5)
        self.l.setRowStretch(3, 5)

        self.centralwidget.setLayout(self.l)

    def retranslateUi(self, MainWindow):
        """Assign translatable text to widgets and menus.

        Args:
            MainWindow: The :class:`QMainWindow` instance whose labels and titles
                are updated.
        """
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Interactive Raman Analysis"))
        self.buttonNewFit.setText(_translate("MainWindow", "Initiate New Fit"))
        self.buttonResetROI.setText(_translate("MainWindow", "Reset ROI"))
        self.checkBox_ROI.setText(_translate("MainWindow", "Show ROI Tools"))
        self.checkBox_ROI_circle.setText(_translate("MainWindow", "Circular ROI"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuExport.setTitle(_translate("MainWindow", "Export"))
        self.menuSettings.setTitle(_translate("MainWindow", "Settings"))
        self.menuHelp.setTitle(_translate("MainWindow", "Help"))
        self.actionNew.setText(_translate("MainWindow", "New Project"))
        self.actionOpen.setText(_translate("MainWindow", "Open Project"))
        self.actionSave.setText(_translate("MainWindow", "Save"))
        self.actionSave_As.setText(_translate("MainWindow", "Save As"))
        self.actionLoad_Map.setText(_translate("MainWindow", "Load Map"))
