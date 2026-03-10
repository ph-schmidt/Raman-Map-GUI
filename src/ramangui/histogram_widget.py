"""Histogram widget for Raman parameter maps.

Provides :class:`HistoWidget`, a PyQt6/pyqtgraph widget that computes and displays
histograms of selected fit-result channels (optionally restricted to a ROI).
The widget supports interactive bin control, optional Gaussian fitting, and
integrates with the application theme and labeling utilities.
"""

import logging

import numpy as np
import pyqtgraph as pg
import qdarktheme
from PyQt6 import QtCore, QtGui, QtWidgets
from scipy.optimize import least_squares

from ramangui import utils

logger = logging.getLogger(__name__)


class HistoWidget(QtWidgets.QWidget):
    """A widget for displaying a histogram with adjustable bins and fitting options.

    Includes dropdown selection for data type and a slider for bin count.
    """

    def __init__(self, args):
        """Initialize the HistoWidget with a grid layout, plot area, and controls.

        Parameters:
        args: Arguments to be passed to the parent QWidget class.
        """
        logger.debug("Initializing HistoWidget...")
        QtWidgets.QWidget.__init__(self, args)

        # Define default label style for plot axes
        self.labelStyle = {"font-size": "12pt"}

        # Set up grid layout for organizing widgets within HistoWidget
        self.l = QtWidgets.QGridLayout()
        self.setLayout(self.l)

        # Create and add a label for the histogram description
        self.textB = QtWidgets.QLabel("Histogram for")
        self.textB.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        # Create and add a dropdown menu for selecting data types
        self.comboBox_B = QtWidgets.QComboBox()

        # Set up the plot widget and configure axes visibility and font style
        self.plt = pg.PlotWidget()
        self.plt.enableAutoRange()
        self.plt.showAxis("left", show=True)
        self.plt.showAxis("right", show=True)
        self.plt.showAxis("top", show=True)
        self.plt.showAxis("bottom", show=True)

        # Customize font and offset for tick labels on bottom and left axes
        font = QtGui.QFont()
        font.setPixelSize(12)
        self.plt.getAxis("bottom").tickFont = font
        self.plt.getAxis("bottom").setStyle(tickTextOffset=12)
        self.plt.getAxis("left").tickFont = font
        self.plt.getAxis("left").setStyle(tickTextOffset=12)

        # Hide values on top and right axes
        self.plt.getAxis("top").setStyle(showValues=False)
        self.plt.getAxis("right").setStyle(showValues=False)

        # Add widgets to the layout grid
        self.l.addWidget(self.textB, 0, 2)
        self.l.addWidget(self.comboBox_B, 0, 3)
        self.l.addWidget(self.plt, 1, 0, 3, 4)

        # Add elements to comboBox and configure default settings
        self.addElementsToBoxes()

        # Set plot colors and connect comboBox selection change to update method
        theme = QtWidgets.QApplication.instance().property("theme")
        color_palette = qdarktheme.load_palette(theme)
        window_color = color_palette.window().color().name()
        text_color = color_palette.windowText().color().name()
        pg.setConfigOption("background", window_color)
        pg.setConfigOption("foreground", text_color)
        self.comboBox_B.currentIndexChanged.connect(self.update_Data)

        # Create an empty plot item for data highlighting
        self.highlight = pg.PlotDataItem()
        self.plt.addItem(self.highlight)

        # Set up slider for adjusting number of bins in the histogram
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Vertical)
        self.slider.setMinimum(25)  # Minimum number of bins
        self.slider.setMaximum(300)  # Maximum number of bins
        self.slider.setValue(100)  # Default bin count
        self.l.addWidget(self.slider, 2, 4)
        self.slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksRight)
        self.slider.setTickInterval(5)

        # Add labels for slider range (max and min bin count)
        self.textSliderT = QtWidgets.QLabel("#Bins\n300")
        self.textSliderB = QtWidgets.QLabel("25")
        self.textSliderT.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.textSliderB.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.l.addWidget(self.textSliderT, 1, 4)
        self.l.addWidget(self.textSliderB, 3, 4)

        # Connect slider value change to update method for dynamic bin adjustment
        self.slider.valueChanged.connect(lambda _: self.update_Data())

        # Initialize legend and settings variables
        self.leg = None
        self.settings = None

        logger.info("HistoWidget initialized.")

    def setSettings(self, settings):
        """Set the settings for the widget.

        Parameters:
        settings (dict): A dictionary of settings for the widget.
        """
        logger.debug("Setting HistoWidget settings.")
        self.settings = settings

    def roi_update(self, roi, img):
        """Update the Region of Interest (ROI) and image data.

        Parameters:
        roi: Region of interest to update.
        img: Image data associated with the ROI.
        """
        logger.debug("ROI update received; triggering histogram update.")
        self.roi = roi
        self.imv = img
        self.update_Data()

    def setData(self, dat, lists=None):
        """Set data for histogram and initialize comboBox items if provided.

        Parameters:
        dat: Data source for histogram values.
        lists (optional): Lists of names, icons, keys, and labels for dropdown items.
        """
        logger.info("Setting data for HistoWidget.")
        self.dat = dat
        if lists is not None:
            # Extract lists for comboBox names, icons, keys, and labels
            self.liste_comboBox_names = lists[0]
            self.liste_comboBox_icons = lists[1]
            self.keys = lists[2]
            self.mpl_labels = lists[3]
            self.labels = lists[4]
            logger.debug("Dropdown lists provided (items=%d).", len(self.liste_comboBox_names))
        self.data = self.dat.get_fitresults()  # Retrieve data fit results
        logger.debug(
            "Fit results loaded for histogram (keys=%d).",
            len(self.data) if hasattr(self.data, "__len__") else -1,
        )

    def update_Data(self, indexnew=None):
        """Update histogram data based on comboBox selection and slider value.

        Parameters:
        indexnew (optional): Manually specified index for comboBox selection.
        """
        # Get current comboBox index or use provided index
        if indexnew is None:
            index = self.comboBox_B.currentIndex()
        else:
            index = indexnew

        # Get number of bins from slider and selected data key
        nBins = self.slider.value()
        try:
            key = self.keys[index]
        except Exception:
            logger.debug("update_Data called before keys are available; skipping.", exc_info=False)
            return

        logger.debug("Updating histogram (index=%d, key=%s, bins=%d).", index, key, nBins)

        try:
            x = self.data[key]
        except Exception:
            logger.exception("Failed to access histogram data for key=%s.", key)
            return

        # Apply ROI region to data and remove NaN values
        try:
            x = self.roi.getArrayRegion(x, self.imv)
        except Exception:
            logger.debug("ROI not available yet; cannot compute histogram.", exc_info=False)
            return

        x = np.reshape(x, np.size(x))
        x = x[~np.isnan(x)]

        # Proceed only if there is valid data
        if np.size(x) != 0:
            self.x = x
            self.nBins = nBins

            # Generate histogram data
            yy, xx = np.histogram(x, bins=np.linspace(x.min(), x.max(), nBins))

            # Calculate mean and standard deviation for histogram
            mean = np.sum(xx[:-1] * yy) / np.sum(yy)
            sigma = np.sqrt(np.sum(yy * (xx[:-1] - mean) ** 2) / np.sum(yy))
            self.mean = mean
            self.sigma = sigma

            logger.debug("Histogram stats: mean=%s sigma=%s n=%d", mean, sigma, np.size(x))

            # Define Gaussian function for curve fitting
            def gauss(x, a, x0, sigma):
                if sigma > 0:
                    return a * np.exp(-((x - x0) ** 2) / (2 * sigma**2))
                else:
                    return 0.0

            def residuals(p, x, y):
                return gauss(x, *p) - y

            # Attempt to fit Gaussian to histogram
            tmp = False
            try:
                if self.keys[self.comboBox_B.currentIndex()] == "Mask":
                    popt = [0.0, 1.0, 1.0]
                else:
                    # popt, pcov = curve_fit(gauss, xx[:-1], yy, p0=[1, mean, sigma])
                    res = least_squares(residuals, x0=[1, mean, sigma], args=(xx[:-1], yy))
                    popt = res.x
                xxx = np.linspace(
                    np.min([xx.min(), popt[1] - 4 * popt[2]]),
                    np.max([xx.max(), popt[1] + 4 * popt[2]]),
                    4 * nBins,
                )
                curve2 = pg.PlotCurveItem(
                    xxx,
                    gauss(xxx, *popt),
                    pen="r",
                    name="  Mean="
                    + str(np.round(popt[1], 2))
                    + "\nSigma="
                    + str(np.round(popt[2], 2)),
                )
                tmp = True
                logger.debug("Gaussian fit succeeded: popt=%s", popt)
            except Exception:
                # Fitting may fail for degenerate distributions; not necessarily an error.
                logger.debug("Gaussian fit failed (index=%d, key=%s).", index, key, exc_info=False)
                tmp = False

            # Create histogram plot curve
            curve = pg.PlotCurveItem(xx, yy, stepMode=True, fillLevel=0, brush=(0, 0, 255, 80))
            self.plt.clear()

            # Manage legend
            if self.leg is not None:
                try:
                    self.plt.removeItem(self.leg)
                except Exception:
                    logger.debug("Failed to remove previous legend; continuing.", exc_info=True)

            self.leg = self.plt.addLegend(offset=[0.5, 0.5])
            self.plt.addItem(curve)
            if tmp:
                self.plt.addItem(curve2)

            # Update plot labels
            self.plt.setLabel("left", "#", **self.labelStyle)
            self.plt.setLabel("bottom", self.get_label(index), **self.labelStyle)
        else:
            logger.info("No valid data for histogram (index=%d, key=%s).", index, key)

    def setCross(self, c):
        """Set crosshair object for use with plot.

        Parameters:
        c: Crosshair object.
        """
        logger.debug("Crosshair set on HistoWidget.")
        self.cross = c

    def addElementsToBoxes(self, lists=None, settings=None):
        """Populate comboBox with items, optionally set settings.

        Parameters:
        lists (optional): Lists of comboBox names, icons, keys, and labels.
        settings (optional): Settings dictionary.
        """
        if settings is not None:
            self.settings = settings
            logger.debug("Settings updated via addElementsToBoxes.")

        if lists is not None:
            self.liste_comboBox_names = lists[0]
            self.liste_comboBox_icons = lists[1]
            self.keys = lists[2]
            self.mpl_labels = lists[3]
            self.labels = lists[4]
            self.comboBox_B.clear()  # Clear existing items

            logger.info("Populating histogram dropdown (items=%d).", len(self.liste_comboBox_names))

            # Populate comboBox with items and icons
            for i in range(len(self.liste_comboBox_names)):
                self.comboBox_B.addItem("")
                self.comboBox_B.setItemText(i, self.liste_comboBox_names[i])
                self.comboBox_B.setIconSize(QtCore.QSize(30, 30))
                icon = utils.mathTex_to_QPixmap(self.liste_comboBox_icons[i], "xx-large")
                self.comboBox_B.setItemIcon(i, QtGui.QIcon(icon))

            # Set default comboBox selection based on settings
            try:
                if not self.settings.get("4_P_mode"):  # check if multipeak mode is enabled
                    self.comboBox_B.setCurrentIndex(self.liste_comboBox_names.index("2D-peak FWHM"))
                    logger.debug("Default histogram selection set to '2D-peak FWHM'.")
                else:
                    self.comboBox_B.setCurrentIndex(0)
                    logger.debug("Default histogram selection set to index 0.")
            except Exception:
                logger.debug("Could not apply default selection from settings.", exc_info=True)

    def get_label(self, index):
        """Get the label for the comboBox item at a specific index.

        Parameters:
        index (int): Index of the comboBox item.

        Returns:
        str: The label for the selected item, or an empty string if no labels are set.
        """
        if self.labels is not None:
            return self.labels[index]
        else:
            return ""
