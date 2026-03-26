"""Application entry point and main window wiring for the Raman GUI.

Defines :class:`MainApp`, the main Qt window that coordinates project management,
data loading/fitting, view updates, and export actions. Also provides CLI startup
via :func:`run_main` (with logging configuration) and helper functions for
detecting IPython environments.
"""

import argparse
import logging
import os
import sys
import webbrowser
from importlib import resources

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import qdarktheme
from easysettings import EasySettings
from pyfiglet import Figlet
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QAction

from ramangui import __version__, export, main_window, utils
from ramangui.data import DataObject
from ramangui.gradient_app import GradientApp
from ramangui.settings_app import SettingsApp

logger = logging.getLogger(__name__)


class MainApp(QtWidgets.QMainWindow):
    """Main application window for interactive Raman map analysis.

    This window wires together the generated Qt Designer UI, data/model objects,
    and supporting widgets (map view, statistics, histogram). It also manages
    project creation/loading, map import/fitting, and export actions via the menu.
    """

    def __init__(self):
        """Initialize the main window UI, menus, and widget connections.

        Sets up the main window in a maximized state, creates menu actions
        (settings/export/help), wires UI signals to slots, and prepares the plot
        selection dropdown. Export is disabled until a map is loaded.
        """
        logger.debug("Initializing MainApp")

        super().__init__()
        self.ui = main_window.Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowState(QtCore.Qt.WindowState.WindowMaximized)
        logger.debug("UI setup completed; window maximized.")

        # Settings / Actions
        fitSettings = QAction("Fit Settings", self)
        gradSettings = QAction("Color Gradient Settings", self)
        export1 = QAction("Export Dialog", self)
        export2 = QAction("Export All", self)

        self.ui.menuSettings.setEnabled(False)
        self.ui.menuSettings.addAction(fitSettings)
        self.ui.menuSettings.addAction(gradSettings)
        self.ui.menuExport.addAction(export1)
        self.ui.menuExport.addAction(export2)

        self.ui.menuSettings.triggered[QAction].connect(self.menuHandle)
        self.ui.menuFile.triggered[QAction].connect(self.menuHandle)
        self.ui.menuExport.triggered[QAction].connect(self.menuHandle)

        onlineHelp = QAction("Online Help", self)
        self.ui.menuHelp.addAction(onlineHelp)
        self.ui.menuHelp.triggered[QAction].connect(self.menuHandle)
        about = QAction("About", self)
        self.ui.menuHelp.addAction(about)

        self.ui.comboBox_Plot.currentIndexChanged.connect(self.update_view)
        self.ui.comboBox_Plot.activated.connect(self.dropdown_selected)
        self.ui.buttonNewFit.clicked.connect(self.initiateNewFit)
        self.ui.buttonResetROI.clicked.connect(self.resetROI)

        self.ui.buttonNewFit.setEnabled(False)
        self.ui.comboBox_Plot.setEnabled(False)

        self.ui.widget.connect2statistic(self.ui.widget_stat)
        self.ui.widget.connect2histo(self.ui.widget_histo)

        self.ui.checkBox_ROI.setChecked(True)
        self.ui.checkBox_ROI.stateChanged.connect(self.changeROI_Tools)

        self.projectLoaded = False
        self.mapLoaded = False

        self.build_dropdown()
        self.ui.menuExport.setEnabled(False)
        logger.info("Application UI initialized. Ready for project selection.")

    def dropdown_selected(self, index):
        """Handle selection changes in the quantity dropdown menu.

        This method is triggered when the user selects a new entry in the
        QComboBox containing available quantities. The selected quantity is
        logged for debugging purposes.

        If the selected quantity corresponds to ``"doping"`` or ``"strain"``,
        an informational message box is displayed to inform the user that the
        extracted values are approximate and should only be interpreted as
        rough estimates. Users are referred to the project documentation on
        GitHub for further details on the methodology and its limitations.

        Parameters
        ----------
        index : int
            Index of the selected entry in the dropdown menu.
        """
        logger.debug("New quantity selected: %s", self.keys[index])
        if self.keys[index] in ["doping", "strain"]:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
            msg.setText("Doping and Strain Estimation")
            msg.setInformativeText(
                "The extracted doping and strain values are approximate and should "
                "only be interpreted as rough estimates. The implemented method is "
                "intended for qualitative analysis and may not provide quantitatively "
                "accurate results for all datasets.\n\n"
                "The parameters used for the computation can be adjusted in the settings "
                "to better match your specific experimental conditions.\n\n"
                "Please consult the software documentation on GitHub for details "
                "about the method, assumptions, and limitations."
            )
            msg.setWindowTitle("Doping and Strain")
            msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
            msg.exec()

    def build_dropdown(self):
        """Build the plot selection dropdown and associated metadata lists.

        Populates combo-box display names/icons and the corresponding `keys`,
        HTML labels, and Matplotlib labels used throughout the application.
        Content depends on whether 4-peak 2D fitting mode is enabled in settings.
        """
        global settings
        logger.debug("Building plot dropdown...")
        try:
            FourPeak2D = bool(settings.get("4_P_mode"))
            logger.debug("Settings: 4_P_mode=%s", FourPeak2D)
        except Exception:
            FourPeak2D = False
            logger.info("Settings not available yet; defaulting 4_P_mode=%s", FourPeak2D)

        self.ui.comboBox_Plot.clear()

        self.liste_comboBox_names = [
            "Mask",
            "G-peak area",
            "G-peak FWHM",
            "G-peak omega",
            "G-peak offset",
            "D-peak area",
            "D-peak FWHM",
            "D-peak omega",
            "D-peak offset",
        ]
        self.liste_comboBox_icons = [
            r"$0/1$",
            r"$A _ G$",
            r"$\Gamma _ G$",
            r"$\omega _ G$",
            r"$c _ G$",
            r"$A _ D$",
            r"$\Gamma _ D$",
            r"$\omega _ D$",
            r"$c _ D$",
        ]
        self.keys = [
            "mask",
            "area_g",
            "gamma_g",
            "omega_g",
            "offset_g",
            "area_d",
            "gamma_d",
            "omega_d",
            "offset_d",
        ]
        self.labels = [
            "<math> Mask </math>",
            "<math> A<sub>G</sub> (cm<sup>-1</sup>) </math>",
            "<math> &Gamma;<sub>G</sub> (cm<sup>-1</sup>) </math>",
            "<math> &omega;<sub>G</sub> (cm<sup>-1</sup>) </math>",
            "<math> c<sub>G</sub> (Counts) </math>",
            "<math> A<sub>D</sub> (cm<sup>-1</sup>) </math>",
            "<math> &Gamma;<sub>D</sub> (cm<sup>-1</sup>) </math>",
            "<math> &omega;<sub>D</sub> (cm<sup>-1</sup>) </math>",
            "<math> c<sub>D</sub> (Counts) </math>",
        ]
        self.mpl_labels = [
            "Mask",
            r"$A_G$ (cm$^{-1}$)",
            r"$\Gamma_G$ (cm$^{-1}$)",
            r"$\omega_G$ (cm$^{-1}$)",
            r"$c_G$ (Counts)",
            r"$A_D$ (cm$^{-1}$)",
            r"$\Gamma_D$ (cm$^{-1}$)",
            r"$\omega_D$ (cm$^{-1}$)",
            r"$c_D$ (Counts)",
        ]

        self.liste_comboBox_names.extend(
            ["2D-peak area", "2D-peak FWHM", "2D-peak omega", "2D-peak offset"]
        )
        self.liste_comboBox_icons.extend(
            [r"$A _ {2D}$", r"$\Gamma _ {2D}$", r"$\omega _ {2D}$", r"$c _ {2D}$"]
        )
        self.keys.extend(["area_2d", "gamma_2d", "omega_2d", "offset_2d"])
        self.labels.extend(
            [
                "<math> A<sub>2D</sub> (cm<sup>-1</sup>) </math>",
                "<math> &Gamma;<sub>2D</sub> (cm<sup>-1</sup>) </math>",
                "<math> &omega;<sub>2D</sub> (cm<sup>-1</sup>) </math>",
                "<math> c<sub>2D</sub> (Counts) </math>",
            ]
        )
        self.mpl_labels.extend(
            [
                r"$A_{2D}$ (cm$^{-1}$)",
                r"$\Gamma_{2D}$ (cm$^{-1}$)",
                r"$\omega_{2D}$ (cm$^{-1}$)",
                r"$c_{2D}$ (Counts)",
            ]
        )

        if FourPeak2D:
            self.liste_comboBox_names.extend(
                [
                    "2D-peak1 area",
                    "2D-peak1 FWHM",
                    "2D-peak1 omega",
                    "2D-peak2 area",
                    "2D-peak2 FWHM",
                    "2D-peak2 omega",
                    "2D-peak3 area",
                    "2D-peak3 FWHM",
                    "2D-peak3 omega",
                    "2D-peak4 area",
                    "2D-peak4 FWHM",
                    "2D-peak4 omega",
                    "2D-peak offset",
                ]
            )
            self.liste_comboBox_icons.extend(
                [
                    r"$A _ {2D1}$",
                    r"$\Gamma _ {2D1}$",
                    r"$\omega _ {2D1}$",
                    r"$A _ {2D2}$",
                    r"$\Gamma _ {2D2}$",
                    r"$\omega _ {2D2}$",
                    r"$A _ {2D3}$",
                    r"$\Gamma _ {2D3}$",
                    r"$\omega _ {2D3}$",
                    r"$A _ {2D4}$",
                    r"$\Gamma _ {2D4}$",
                    r"$\omega _ {2D4}$",
                    r"$c _ {2D}$",
                ]
            )
            self.keys.extend(
                [
                    "area_2d_1",
                    "gamma_2d_1",
                    "omega_2d_1",
                    "area_2d_2",
                    "gamma_2d_2",
                    "omega_2d_2",
                    "area_2d_3",
                    "gamma_2d_3",
                    "omega_2d_3",
                    "area_2d_4",
                    "gamma_2d_4",
                    "omega_2d_4",
                    "offset_2d",
                ]
            )
            self.labels.extend(
                [
                    "<math> A<sub>2D1</sub> (cm<sup>-1</sup>) </math>",
                    "<math> &Gamma;<sub>2D1</sub> (cm<sup>-1</sup>) </math>",
                    "<math> &omega;<sub>2D1</sub> (cm<sup>-1</sup>) </math>",
                    "<math> A<sub>2D2</sub> (cm<sup>-1</sup>) </math>",
                    "<math> &Gamma;<sub>2D2</sub> (cm<sup>-1</sup>) </math>",
                    "<math> &omega;<sub>2D2</sub> (cm<sup>-1</sup>) </math>",
                    "<math> A<sub>2D3</sub> (cm<sup>-1</sup>) </math>",
                    "<math> &Gamma;<sub>2D3</sub> (cm<sup>-1</sup>) </math>",
                    "<math> &omega;<sub>2D3</sub> (cm<sup>-1</sup>) </math>",
                    "<math> A<sub>2D4</sub> (cm<sup>-1</sup>) </math>",
                    "<math> &Gamma;<sub>2D4</sub> (cm<sup>-1</sup>) </math>",
                    "<math> &omega;<sub>2D4</sub> (cm<sup>-1</sup>) </math>",
                    "<math> c<sub>2D</sub> (Counts) </math>",
                ]
            )
            self.mpl_labels.extend(
                [
                    r"$A_{2D1}$ (cm$^{-1}$)",
                    r"$\Gamma_{2D1}$ (cm$^{-1}$)",
                    r"$\omega_{2D1}$ (cm$^{-1}$)",
                    r"$A_{2D2}$ (cm$^{-1}$)",
                    r"$\Gamma_{2D2}$ (cm$^{-1}$)",
                    r"$\omega_{2D2}$ (cm$^{-1}$)",
                    r"$A_{2D3}$ (cm$^{-1}$)",
                    r"$\Gamma_{2D3}$ (cm$^{-1}$)",
                    r"$\omega_{2D3}$ (cm$^{-1}$)",
                    r"$A_{2D4}$ (cm$^{-1}$)",
                    r"$\Gamma_{2D4}$ (cm$^{-1}$)",
                    r"$\omega_{2D4}$ (cm$^{-1}$)",
                    r"$c_{2D}$ (Counts)",
                ]
            )

        # Uncertainties
        self.liste_comboBox_names.extend(
            [
                "G-peak area uncertainty",
                "G-peak FWHM uncertainty",
                "G-peak omega uncertainty",
                "G-peak offset uncertainty",
                "D-peak area uncertainty",
                "D-peak FWHM uncertainty",
                "D-peak omega uncertainty",
                "D-peak offset uncertainty",
            ]
        )
        self.liste_comboBox_icons.extend(
            [
                r"$A _ G^{err}$",
                r"$\Gamma _ G^{err}$",
                r"$\omega _ G^{err}$",
                r"$c _ G^{err}$",
                r"$A _ D^{err}$",
                r"$\Gamma _ D^{err}$",
                r"$\omega _ D^{err}$",
                r"$c _ D^{err}$",
            ]
        )
        self.keys.extend(
            [
                "area_g_error",
                "gamma_g_error",
                "omega_g_error",
                "offset_g_error",
                "area_d_error",
                "gamma_d_error",
                "omega_d_error",
                "offset_d_error",
            ]
        )
        self.labels.extend(
            [
                "<math> A<sub>G</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                "<math> &Gamma;<sub>G</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                "<math> &omega;<sub>G</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                "<math> c<sub>G</sub><sup>err</sup> (Counts) </math>",
                "<math> A<sub>D</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                "<math> &Gamma;<sub>D</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                "<math> &omega;<sub>D</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                "<math> c<sub>D</sub><sup>err</sup> (Counts) </math>",
            ]
        )
        self.mpl_labels.extend(
            [
                r"$A_G^{err}$ (cm$^{-1}$)",
                r"$\Gamma_G^{err}$ (cm$^{-1}$)",
                r"$\omega_G^{err}$ (cm$^{-1}$)",
                r"$c_G^{err}$ (Counts)",
                r"$A_D^{err}$ (cm$^{-1}$)",
                r"$\Gamma_D^{err}$ (cm$^{-1}$)",
                r"$\omega_D^{err}$ (cm$^{-1}$)",
                r"$c_D^{err}$ (Counts)",
            ]
        )

        self.liste_comboBox_names.extend(
            [
                "2D-peak area uncertainty",
                "2D-peak FWHM uncertainty",
                "2D-peak omega uncertainty",
                "2D-peak offset uncertainty",
            ]
        )
        self.liste_comboBox_icons.extend(
            [
                r"$A _ {2D}^{err}$",
                r"$\Gamma _ {2D}^{err}$",
                r"$\omega _ {2D}^{err}$",
                r"$c _ {2D}^{err}$",
            ]
        )
        self.keys.extend(["area_2d_error", "gamma_2d_error", "omega_2d_error", "offset_2d_error"])
        self.labels.extend(
            [
                "<math> A<sub>2D</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                "<math> &Gamma;<sub>2D</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                "<math> &omega;<sub>2D</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                "<math> c<sub>2D</sub><sup>err</sup> (Counts) </math>",
            ]
        )
        self.mpl_labels.extend(
            [
                r"$A_{2D}^{err}$ (cm$^{-1}$)",
                r"$\Gamma_{2D}^{err}$ (cm$^{-1}$)",
                r"$\omega_{2D}^{err}$ (cm$^{-1}$)",
                r"$c_{2D}^{err}$ (Counts)",
            ]
        )

        if FourPeak2D:
            self.liste_comboBox_names.extend(
                [
                    "2D-peak1 area uncertainty",
                    "2D-peak1 FWHM uncertainty",
                    "2D-peak1 omega uncertainty",
                    "2D-peak2 area uncertainty",
                    "2D-peak2 FWHM uncertainty",
                    "2D-peak2 omega uncertainty",
                    "2D-peak3 area uncertainty",
                    "2D-peak3 FWHM uncertainty",
                    "2D-peak3 omega uncertainty",
                    "2D-peak4 area uncertainty",
                    "2D-peak4 FWHM uncertainty",
                    "2D-peak4 omega uncertainty",
                    "2D-peak offset uncertainty",
                    "2D-peak comb chi2/ndof",
                ]
            )
            self.liste_comboBox_icons.extend(
                [
                    r"$A _ {2D1}^{err}$",
                    r"$\Gamma _ {2D1}^{err}$",
                    r"$\omega _ {2D1}^{err}$",
                    r"$A _ {2D2}^{err}$",
                    r"$\Gamma _ {2D2}^{err}$",
                    r"$\omega _ {2D2}^{err}$",
                    r"$A _ {2D3}^{err}$",
                    r"$\Gamma _ {2D3}^{err}$",
                    r"$\omega _ {2D3}^{err}$",
                    r"$A _ {2D4}^{err}$",
                    r"$\Gamma _ {2D4}^{err}$",
                    r"$\omega _ {2D4}^{err}$",
                    r"$c _ {2D}^{err}$",
                    r"$\chi _ {2D}$",
                ]
            )
            self.keys.extend(
                [
                    "area_2d_1_error",
                    "gamma_2d_1_error",
                    "omega_2d_1_error",
                    "area_2d_2_error",
                    "gamma_2d_2_error",
                    "omega_2d_2_error",
                    "area_2d_3_error",
                    "gamma_2d_3_error",
                    "omega_2d_3_error",
                    "area_2d_4_error",
                    "gamma_2d_4_error",
                    "omega_2d_4_error",
                    "offset_2d_error",
                    "chi_2_4p",
                ]
            )
            self.labels.extend(
                [
                    "<math> A<sub>2D1</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> &Gamma;<sub>2D1</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> &omega;<sub>2D1</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> A<sub>2D2</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> &Gamma;<sub>2D2</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> &omega;<sub>2D2</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> A<sub>2D3</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> &Gamma;<sub>2D3</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> &omega;<sub>2D3</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> A<sub>2D4</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> &Gamma;<sub>2D4</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> &omega;<sub>2D4</sub><sup>err</sup> (cm<sup>-1</sup>) </math>",
                    "<math> c<sub>2D</sub><sup>err</sup> (Counts) </math>",
                    "<math> &chi<sub>2D</sub><sup>2</sup>/ndof </math>",
                ]
            )
            self.mpl_labels.extend(
                [
                    r"$A_{2D1}^{err}$ (cm$^{-1}$)",
                    r"$\Gamma_{2D1}^{err}$ (cm$^{-1}$)",
                    r"$\omega_{2D1}^{err}$ (cm$^{-1}$)",
                    r"$A_{2D2}^{err}$ (cm$^{-1}$)",
                    r"$\Gamma_{2D2}^{err}$ (cm$^{-1}$)",
                    r"$\omega_{2D2}^{err}$ (cm$^{-1}$)",
                    r"$A_{2D3}^{err}$ (cm$^{-1}$)",
                    r"$\Gamma_{2D3}^{err}$ (cm$^{-1}$)",
                    r"$\omega_{2D3}^{err}$ (cm$^{-1}$)",
                    r"$A_{2D4}^{err}$ (cm$^{-1}$)",
                    r"$\Gamma_{2D4}^{err}$ (cm$^{-1}$)",
                    r"$\omega_{2D4}^{err}$ (cm$^{-1}$)",
                    r"$c_{2D}^{err}$ (Counts)",
                    r"$\chi_{2D}^{2}$/ndof",
                ]
            )

        self.liste_comboBox_names.extend(["Doping", "Strain"])
        self.liste_comboBox_icons.extend([r"$D$", r"$\epsilon$"])
        self.keys.extend(["doping", "strain"])
        self.labels.extend(
            ["<math> D (10<sup>12</sup> cm<sup>-2</sup>) </math>", "<math> &epsilon; (%) </math>"]
        )
        self.mpl_labels.extend([r"$D$ ($10^{12}$ cm$^{-2}$)", r"$\epsilon$ (%)"])

        if FourPeak2D:
            self.liste_comboBox_names.extend(["Doping1", "Strain1"])
            self.liste_comboBox_icons.extend([r"$D_1$", r"$\epsilon _1$"])
            self.keys.extend(["doping_1", "strain_1"])
            self.labels.extend(
                [
                    "<math> D1 (10<sup>12</sup> cm<sup>-2</sup>) </math>",
                    "<math> &epsilon; 1 (%) </math>",
                ]
            )
            self.mpl_labels.extend([r"$D_1$ ($10^{12}$ cm$^{-2}$)", r"$\epsilon _1$ (%)"])

            self.liste_comboBox_names.extend(["Doping2", "Strain2"])
            self.liste_comboBox_icons.extend([r"$D_2$", r"$\epsilon _2$"])
            self.keys.extend(["doping_2", "strain_2"])
            self.labels.extend(
                [
                    "<math> D2 (10<sup>12</sup> cm<sup>-2</sup>) </math>",
                    "<math> &epsilon; 2 (%) </math>",
                ]
            )
            self.mpl_labels.extend([r"$D_2$ ($10^{12}$ cm$^{-2}$)", r"$\epsilon _2$ (%)"])

            self.liste_comboBox_names.extend(["Doping3", "Strain3"])
            self.liste_comboBox_icons.extend([r"$D_3$", r"$\epsilon _3$"])
            self.keys.extend(["doping_3", "strain_3"])
            self.labels.extend(
                [
                    "<math> D3 (10<sup>12</sup> cm<sup>-2</sup>) </math>",
                    "<math> &epsilon; 3 (%) </math>",
                ]
            )
            self.mpl_labels.extend([r"$D_3$ ($10^{12}$ cm$^{-2}$)", r"$\epsilon _3$ (%)"])

            self.liste_comboBox_names.extend(["Doping4", "Strain4"])
            self.liste_comboBox_icons.extend([r"$D_4$", r"$\epsilon _4$"])
            self.keys.extend(["doping_4", "strain_4"])
            self.labels.extend(
                [
                    "<math> D4 (10<sup>12</sup> cm<sup>-2</sup>) </math>",
                    "<math> &epsilon; 4 (%) </math>",
                ]
            )
            self.mpl_labels.extend([r"$D_4$ ($10^{12}$ cm$^{-2}$)", r"$\epsilon _4$ (%)"])

        for i in range(len(self.liste_comboBox_names)):
            self.ui.comboBox_Plot.addItem("")
            self.ui.comboBox_Plot.setItemText(i, self.liste_comboBox_names[i])
            self.ui.comboBox_Plot.setIconSize(QtCore.QSize(30, 30))
            icon = utils.mathTex_to_QPixmap(self.liste_comboBox_icons[i], "xx-large")
            self.ui.comboBox_Plot.setItemIcon(i, QtGui.QIcon(icon))

        self.ui.comboBox_Plot.setCurrentIndex(0)
        logger.info("Plot dropdown built (%d entries).", len(self.liste_comboBox_names))

    def changeROI_Tools(self):
        """Enable or disable ROI tools in the map view based on the checkbox state."""
        checked = self.ui.checkBox_ROI.isChecked()
        logger.info("ROI tools toggled: %s", checked)
        self.ui.widget.changeROI_Tools(checked)

    def menuHandle(self, choise):
        """Handle top-level menu actions from the main window.

        Dispatches actions from Settings/File/Export/Help menus, including opening
        dialogs (fit settings, gradient settings, export), creating/loading projects,
        loading maps, and showing help/about information.

        Args:
            choise: Triggered QAction (menu item).
        """
        global settings
        logger.info("Menu action triggered: %s", choise.text())

        if choise.text() == "Fit Settings":
            logger.debug("Opening Fit Settings dialog...")
            appSettings = SettingsApp(settings)
            appSettings.show()
            appSettings.exec()
            try:
                if self.mapLoaded:
                    logger.debug(
                        "Map loaded; rebuilding dropdown and refreshing statistics/histogram widgets."
                    )
                    self.build_dropdown()
                    lists = [
                        self.liste_comboBox_names,
                        self.liste_comboBox_icons,
                        self.keys,
                        self.mpl_labels,
                        self.labels,
                    ]
                    self.ui.widget_stat.redraw_boxes(lists=lists, settings=settings)
                    self.ui.widget_histo.addElementsToBoxes(lists=lists, settings=settings)
                else:
                    logger.debug("Fit Settings closed; no map loaded, skipping redraw.")
            except Exception:
                logger.exception("Error while applying Fit Settings changes.")
        elif choise.text() == "Export Dialog":
            try:
                if self.mapLoaded:
                    logger.info("Opening Export dialog...")
                    exporter = export.ExportApp(keys=self.keys)
                    exporter.connect_widgets(
                        data=self.data,
                        view=self.ui.widget,
                        index=self.ui.comboBox_Plot.currentIndex(),
                        statistics=self.ui.widget_stat,
                        histo=self.ui.widget_histo,
                        mpl=self.mpl_labels,
                    )
                    exporter.exec()
                else:
                    logger.warning("Export dialog requested but no map loaded.")
            except Exception:
                logger.exception("Error while opening Export dialog.")
        elif choise.text() == "Export All":
            try:
                if self.mapLoaded:
                    logger.info("Export All requested.")
                    self.exportAll()
                else:
                    logger.warning("Export All requested but no map loaded.")
            except Exception:
                logger.exception("Error during Export All.")
        elif choise.text() == "Color Gradient Settings":
            logger.info("Opening Color Gradient Settings dialog...")
            appGradient = GradientApp(self.ui.widget)
            appGradient.show()
            appGradient.exec()
        elif choise.text() == "New Project":
            logger.info("Creating new project...")
            self.newProject()
            self.projectLoaded = True
            logger.info("New project loaded: %s", globals().get("path", ""))
        elif choise.text() == "Open Project":
            logger.info("Opening existing project...")
            self.openProject()
            self.projectLoaded = True
            logger.info("Project loaded: %s", globals().get("path", ""))
        elif choise.text() == "Load Map":
            try:
                if self.projectLoaded:
                    logger.info("Loading map...")
                    self.loadMap()
                    self.mapLoaded = True
                    logger.info("Map loaded successfully.")
                else:
                    logger.warning("Load Map requested but project not loaded yet.")
                    QtWidgets.QMessageBox.warning(
                        self,
                        "No Project Loaded",
                        "Please load or create a project before loading a map.",
                    )
            except Exception:
                logger.exception("Error while loading map.")
        elif choise.text() == "Online Help":
            logger.info("Opening online help in web browser.")
            webbrowser.open_new_tab(
                "https://github.com/ph-schmidt/Raman-Map-GUI?tab=readme-ov-file"
            )
        elif choise.text() == "About":
            logger.debug("Showing About dialog.")
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
            msg.setText(f"Raman-Map-GUI - Interactive Raman Analysis, Version {__version__}")
            msg.setInformativeText(
                "Idea by Christoph Stampfer\n"
                "Developed by Philipp Schmidt\n"
                "2nd Institute of Physics A, RWTH Aachen University"
            )
            msg.setWindowTitle("About")
            msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
            msg.exec()

    def loadMap(self):
        """Load a Raman map from a Matlab file and update all dependent widgets.

        Opens a file dialog rooted at the current project path. If a file is selected,
        loads data into a :class:`~ramangui.data.DataObject`, rebuilds dropdown lists,
        updates the map/statistics/histogram widgets, and enables export and fitting UI.

        Also attempts to restore a persisted ROI state from ``<filename>.roi.npy``.
        """
        global path, settings
        logger.debug("Opening file dialog for Matlab file (path=%s)...", path)
        filename = str(
            QtWidgets.QFileDialog.getOpenFileName(
                self, "Open Matlab File", path, "Matlab files (*.mat)"
            )[0]
        )
        logger.info("Matlab file selection: %s", filename if filename else "(cancelled)")

        if filename != "":
            self.ui.widget.roi_save_enabled = False
            try:
                logger.info("Loading map data from file...")
                self.data = DataObject(filename, settings, self)
                self.build_dropdown()
                lists = [
                    self.liste_comboBox_names,
                    self.liste_comboBox_icons,
                    self.keys,
                    self.mpl_labels,
                    self.labels,
                ]
                self.ui.widget_stat.setData(self.data, lut=self.ui.widget.imv1, lists=lists)
                self.ui.widget_histo.setData(self.data, lists=lists)
                self.ui.widget.set_filename(filename)
                self.ui.widget.update_Data(
                    self.data,
                    self.ui.comboBox_Plot.currentIndex(),
                    roi_circle=self.ui.checkBox_ROI_circle.isChecked(),
                    keys=self.keys,
                )
                self.ui.checkBox_ROI_circle.setEnabled(False)
                self.ui.menuExport.setEnabled(True)
                self.ui.buttonNewFit.setEnabled(True)
                self.ui.comboBox_Plot.setEnabled(True)

                self.ui.widget_stat.redraw_boxes(lists=lists, settings=settings)
                self.ui.widget_histo.addElementsToBoxes(lists=lists, settings=settings)
                logger.info("Map loaded and UI updated.")
            except Exception:
                logger.exception("Error while loading map", exc_info=True)

            try:
                roi_path = filename + ".roi.npy"
                logger.debug("Attempting to load ROI state from: %s", roi_path)
                state = np.load(roi_path, encoding="bytes", allow_pickle=True).item()
                self.ui.widget.roi.setState(state)
                logger.info("ROI state loaded and applied.")
            except Exception:
                logger.warning("No ROI state loaded; resetting ROI (file missing or invalid).")
                self.ui.widget.resetROI()

            self.ui.widget.roi_save_enabled = True

    def resetROI(self):
        """Reset the ROI in the map view to its default state."""
        logger.info("Reset ROI requested.")
        self.ui.widget.resetROI()

    def initiateNewFit(self):
        """Prompt the user for confirmation and initiate a new fit if accepted."""
        logger.info("User requested new fit (confirmation dialog shown).")
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Icon.Question)
        msg.setText("Are you sure to perform a new fit?")
        msg.setInformativeText("A new Fit will take a few minutes...")
        msg.setWindowTitle("Initiate New Fit?")
        msg.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No
        )
        msg.buttonClicked.connect(self.msgbtn)
        msg.exec()

    def msgbtn(self, i):
        """Handle the confirmation dialog response for starting a new fit.

        Args:
            i: The clicked QMessageBox button.
        """
        global settings
        logger.debug("New fit confirmation clicked: %s", i.text())
        if i.text() == "&Yes":
            logger.info("Starting new fit...")
            lists = [
                self.liste_comboBox_names,
                self.liste_comboBox_icons,
                self.keys,
                self.mpl_labels,
                self.labels,
            ]
            try:
                self.data.update_Settings(settings)
                self.data.perform_fit()
                logger.info("Fit completed successfully.")
            except Exception:
                logger.exception("Fit failed.", exc_info=True)
                return

            try:
                self.update_view(self.ui.comboBox_Plot.currentIndex())
                self.ui.widget_stat.setData(self.data, lut=self.ui.widget.imv1, lists=lists)
                self.ui.widget_histo.setData(self.data, lists=lists)
                logger.debug("UI updated after fit.")
            except Exception:
                logger.exception("Error while updating UI after fit.", exc_info=True)
        else:
            logger.info("New fit cancelled by user.")

    def update_view(self, index):
        """Update the map view for the selected parameter index.

        Args:
            index: Index into `self.keys` / dropdown selection.
        """
        logger.debug("Updating view (index=%s)...", index)
        try:
            self.ui.widget.update_Data(self.data, index, keys=self.keys)
        except Exception:
            logger.debug("update_view skipped/failed (likely no data yet).", exc_info=False)

    def openProject(self, path_cli=""):
        """Open an existing project directory and load its settings."""
        global path
        global settings
        logger.debug("Opening directory dialog for existing project...")
        if path_cli == "":
            path = str(
                QtWidgets.QFileDialog.getExistingDirectory(self, "Select the project folder!")
            )
        else:
            path = path_cli
        logger.info("Project folder selection: %s", path if path else "(cancelled)")

        if path != "":
            try:
                settings_path = path + "/Settings/settings.conf"
                logger.debug("Loading settings from: %s", settings_path)
                settings = EasySettings(settings_path)
                settings = utils.ensure_settings_defaults(settings, logger)
                self.ui.menuSettings.setEnabled(True)
                self.setWindowTitle("Interactive Raman Analysis  -  " + path)
                logger.info("Project opened successfully.")
            except Exception:
                logger.exception("Failed to open project settings.")
        else:
            logger.debug("Open Project cancelled.")

    def newProject(self):
        """Create a new project directory structure and initialize default settings."""
        global path, settings
        logger.debug("Opening directory dialog for new project...")
        path = str(
            QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory for the new Project")
        )
        logger.info("New project base directory: %s", path if path else "(cancelled)")

        if path != "":
            tempvar = True
            while tempvar:
                projectname, ok = QtWidgets.QInputDialog.getText(
                    self, "New Project", "Enter name for the new project:"
                )
                logger.debug(
                    "New project name dialog result: ok=%s, projectname=%s", ok, projectname
                )
                if ok:
                    if not os.path.exists(path + "/" + projectname):
                        logger.info("Creating new project structure: %s", path + "/" + projectname)
                        os.makedirs(path + "/" + projectname)
                        tempvar = False
                        path = path + "/" + projectname
                        if not os.path.exists(path + "/Settings"):
                            os.makedirs(path + "/Settings")
                        if not os.path.exists(path + "/Maps"):
                            os.makedirs(path + "/Maps")
                        if not os.path.exists(path + "/Fits"):
                            os.makedirs(path + "/Fits")
                        self.setWindowTitle("Interactive Raman Analysis  -  " + path)

                        filename = path + "/Settings/settings.conf"
                        logger.debug("Creating default settings at: %s", filename)
                        settings = utils.create_settings(filename)
                        self.ui.menuSettings.setEnabled(True)
                        logger.info("New project created successfully: %s", path)
                    else:
                        logger.warning("Project already exists: %s", path + "/" + projectname)
                        msg = QtWidgets.QMessageBox()
                        msg.setIcon(QtWidgets.QMessageBox.Critical)
                        msg.setText(
                            "In the choosen folder a project with name "
                            + projectname
                            + " already exists."
                        )
                        msg.setInformativeText(
                            "Please choose another name or delete the old project folder!"
                        )
                        msg.setWindowTitle("Error")
                        msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
                        msg.exec()
                else:
                    logger.info("New project creation cancelled by user.")
                    break

    def exportAll(self):
        """Export all available maps and histogram statistics for the loaded dataset.

        Iterates over all parameter keys, exporting the current map (with and without ROI),
        exporting histogram summaries, and storing ROI-cropped arrays into a combined
        ``fullExport`` dictionary saved as a NumPy ``.npy`` file.
        """
        global path
        logger.info("Starting full export (Export All)...")

        self.histo_widget = self.ui.widget_histo
        startIndex = self.ui.comboBox_Plot.currentIndex()
        fileNames = np.array([self.ui.comboBox_Plot.itemText(i) for i in range(len(self.keys))])

        self.progress = QtWidgets.QProgressDialog("Export All", "Cancel", 0, len(self.keys), self)
        self.progress.setWindowTitle("Please wait...")
        self.progress.setModal(True)
        self.progress.show()

        try:
            fullExport = self.data.get_fitresults().copy()
        except Exception:
            logger.exception("Failed to read fit results for full export.")
            return

        for index in range(len(self.keys)):
            try:
                logger.info(
                    "Exporting index %d/%d: key=%s name=%s",
                    index + 1,
                    len(self.keys),
                    self.keys[index],
                    fileNames[index],
                )
                self.update_view(index)
                self.exportMap(index, fileNames)
                self.exportMap(index, fileNames, save_with_roi=True)
                self.update_Histo(index)
                self.exportHisto(index, fileNames)

                d = self.data.get_fitresults()[self.keys[index]]
                roi_data = self.ui.widget.roi.getArrayRegion(d, self.ui.widget.imv1.getImageItem())
                keyname = self.keys[index] + "_ROI"
                fullExport[keyname] = roi_data
                logger.debug(
                    "ROI data appended to fullExport as %s (shape=%s).",
                    keyname,
                    getattr(roi_data, "shape", None),
                )
            except Exception:
                logger.exception("Error while exporting index %d (%s).", index, self.keys[index])

            self.progress.setValue(index + 1)
            if self.progress.wasCanceled():
                logger.warning("Export All cancelled by user at index %d.", index)
                break

        try:
            fname = (
                path + "/Fits/" + self.data.filename.split(r"/")[-1] + "_" + "fullExport" + ".npy"
            )
            np.save(fname, fullExport)
            logger.info("Full export saved: %s", fname)
        except Exception:
            logger.exception("Failed to save fullExport npy file.")

        self.update_view(startIndex)
        self.update_Histo(startIndex)
        logger.info("Export All finished.")

    def update_Histo(self, index):
        """Update the histogram widget for the given parameter index.

        Args:
            index: Index into `self.keys` / dropdown selection.
        """
        logger.debug("Updating histogram view (index=%s)...", index)
        self.histo_widget.update_Data(indexnew=index)

    def exportHisto(self, index, fileNames):
        """Export histogram summary statistics and the histogram table to disk.

        Writes mean and sigma to separate CSV files and exports the histogram
        curve (bin positions and counts) as a tab-separated CSV table.

        Args:
            index: Index into the current parameter selection.
            fileNames: Array-like of export name strings (one per key).
        """
        global path
        logger.debug("Exporting histogram data (index=%s, name=%s)...", index, fileNames[index])

        fileName = (
            path
            + "/Fits/"
            + self.data.filename.split(r"/")[-1]
            + "_"
            + fileNames[index]
            + "_mean.csv"
        )
        if fileName != "":
            try:
                with open(fileName, "w", encoding="utf-8", newline="") as fd:
                    fd.write(str(self.histo_widget.mean))
                logger.info("Saved histogram mean: %s", fileName)
            except Exception:
                logger.exception("Failed to save histogram mean: %s", fileName)

        fileName = (
            path
            + "/Fits/"
            + self.data.filename.split(r"/")[-1]
            + "_"
            + fileNames[index]
            + "_sigma.csv"
        )
        if fileName != "":
            try:
                with open(fileName, "w", encoding="utf-8", newline="") as fd:
                    fd.write(str(self.histo_widget.sigma))
                logger.info("Saved histogram sigma: %s", fileName)
            except Exception:
                logger.exception("Failed to save histogram sigma: %s", fileName)

        fileName = (
            path
            + "/Fits/"
            + self.data.filename.split(r"/")[-1]
            + "_"
            + fileNames[index]
            + "_Histogram.csv"
        )
        if fileName != "":
            try:
                c = [self.histo_widget.plt.getPlotItem().curves[0]]
                data = []
                header = [self.histo_widget.comboBox_B.currentText(), "#"]
                for cu in c:
                    cd = cu.getData()
                    if cd[0] is None:
                        logger.warning("Histogram curve has no data; skipping (index=%s).", index)
                        continue
                    data.append(cd)

                sep = "\t"
                num_format = f"{{:.{10}g}}"
                num_rows = max((len(d[0]) for d in data), default=0)

                with open(fileName, "w", encoding="utf-8", newline="") as fd:
                    fd.write(sep.join(header) + "\n")
                    for i in range(num_rows):
                        for d in data:
                            # x
                            if d is not None and i < len(d[0]):
                                fd.write(num_format.format(d[0][i]) + sep)
                            else:
                                fd.write(" " + sep)

                            # y
                            if d is not None and i < len(d[1]):
                                fd.write(num_format.format(d[1][i]) + sep)
                            else:
                                fd.write(" " + sep)

                        fd.write("\n")
                logger.info("Saved histogram table: %s (rows=%d)", fileName, num_rows)
            except Exception:
                logger.exception("Failed to save histogram table: %s", fileName)

    def exportMap(self, index, fileNames, save_with_roi=False):
        """Export the currently selected map to SVG and PNG.

        Exports a Matplotlib-rendered image using the current pyqtgraph view's
        lookup table and levels so the exported map matches the on-screen view.
        Optionally overlays the ROI rectangle.

        Args:
            index: Index into `self.keys` / dropdown selection.
            fileNames: Array-like of export name strings (one per key).
            save_with_roi: If True, overlay ROI rectangle and save as *_withROI.
        """
        global path
        logger.debug(
            "Exporting map (index=%s, name=%s, with_roi=%s)...",
            index,
            fileNames[index],
            save_with_roi,
        )

        plt.ioff()

        data = self.data.get_fitresults()[self.keys[index]]

        lut = self.ui.widget.imv1.getHistogramWidget().getLookupTable(n=256)
        colors = np.array([x for x in lut]) / 255.0
        cm = mcolors.ListedColormap(colors)
        plt.figure()
        extent = [0, self.data.get_xmap()[-1], self.data.get_ymap()[-1], 0]
        vmin = self.ui.widget.imv1.getHistogramWidget().getLevels()[0]
        vmax = self.ui.widget.imv1.getHistogramWidget().getLevels()[1]
        plt.imshow(np.transpose(data), extent=extent, cmap=cm, vmin=vmin, vmax=vmax)
        plt.xlabel(r"x ($\mu$m)")
        plt.ylabel(r"y ($\mu$m)")
        cb1 = plt.colorbar()
        cb1.set_label(self.get_mpl_label(index))

        try:
            if save_with_roi:
                x_roi, y_roi = self.ui.widget.roi.pos()
                dx_roi, dy_roi = self.ui.widget.roi.size()
                x_roi = x_roi * self.data.get_xmap()[1]
                y_roi = y_roi * self.data.get_ymap()[1]
                dx_roi = dx_roi * self.data.get_xmap()[1]
                dy_roi = dy_roi * self.data.get_ymap()[1]
                angle = self.ui.widget.roi.angle()

                rect = matplotlib.patches.Rectangle(
                    (x_roi, y_roi),
                    dx_roi,
                    dy_roi,
                    angle=angle,
                    linewidth=1,
                    linestyle="dashed",
                    edgecolor="black",
                    facecolor="none",
                )
                plt.gca().add_patch(rect)
                plt.tight_layout()
                out_svg = (
                    path
                    + "/Fits/"
                    + self.data.filename.split(r"/")[-1]
                    + "_"
                    + fileNames[index]
                    + "_withROI.svg"
                )
                out_png = (
                    path
                    + "/Fits/"
                    + self.data.filename.split(r"/")[-1]
                    + "_"
                    + fileNames[index]
                    + "_withROI.png"
                )
                plt.savefig(out_svg)
                plt.savefig(out_png)
                logger.info("Saved map with ROI: %s and %s", out_svg, out_png)
            else:
                plt.tight_layout()
                out_svg = (
                    path
                    + "/Fits/"
                    + self.data.filename.split(r"/")[-1]
                    + "_"
                    + fileNames[index]
                    + ".svg"
                )
                out_png = (
                    path
                    + "/Fits/"
                    + self.data.filename.split(r"/")[-1]
                    + "_"
                    + fileNames[index]
                    + ".png"
                )
                plt.savefig(out_svg)
                plt.savefig(out_png)
                logger.info("Saved map: %s and %s", out_svg, out_png)
        except Exception:
            logger.exception(
                "Failed to save exported map (index=%s, with_roi=%s).", index, save_with_roi
            )
        finally:
            plt.close()

    def get_mpl_label(self, index):
        """Return the Matplotlib label string for the given channel index."""
        return self.mpl_labels[index]


def run_main():
    """Run the application from the command line.

    Parses CLI arguments, configures logging and theming, creates a QApplication,
    instantiates :class:`MainApp`, and starts the Qt event loop (unless running
    under IPython/Jupyter).
    """
    parser = argparse.ArgumentParser(description="2D Raman GUI")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--theme",
        default="auto",
        choices=["auto", "dark", "light"],
        help="Set GUI theme",
    )
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level)
    theme = args.theme

    logging.basicConfig(
        level=log_level,
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    print("")
    f = Figlet(font="slant", width=100)
    print(f.renderText("Raman-Map-GUI"))

    logger.info("Starting application...")
    if not QtWidgets.QApplication.instance():
        logger.debug("Creating new QApplication instance.")
        app = QtWidgets.QApplication(sys.argv)
    else:
        logger.debug("Reusing existing QApplication instance.")
        app = QtWidgets.QApplication.instance()

    icon_path = resources.files(__package__) / "icon.ico"
    app.setWindowIcon(QtGui.QIcon(str(icon_path)))
    qdarktheme.setup_theme(theme)
    app.setProperty("theme", theme)

    main = MainApp()
    main.show()
    logger.info("Main window shown.")

    if not is_ipython():
        logger.debug("Not running inside IPython; entering Qt event loop.")
        app.exec()
    else:
        logger.debug("Running inside IPython; skipping app.exec().")

    return main


def is_ipython() -> bool:
    """Return True if running inside an IPython environment (e.g., Jupyter)."""
    try:
        shell = get_ipython().__class__.__name__  # type: ignore
        if shell == "ZMQInteractiveShell":
            return True
        if shell == "TerminalInteractiveShell":
            return True
        return True
    except NameError:
        return False


def start():
    """Convenience entry point for starting the application."""
    run_main()
    print("\n")


if __name__ == "__main__":
    m = run_main()
