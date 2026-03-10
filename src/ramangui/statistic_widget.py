"""Statistical scatter plot widget for Raman analysis.

This module defines :class:`StatisticWidget`, a PyQt6/pyqtgraph-based widget
for visualizing correlations between fitted Raman parameters. It supports
ROI-restricted data, optional coloring via a lookup table (LUT), linked
colorscales with external views, and interactive highlighting.
"""

import logging

import numpy as np
import pyqtgraph as pg
import qdarktheme
from PyQt6 import QtCore, QtGui, QtWidgets

from ramangui import utils

logger = logging.getLogger(__name__)


class StatisticWidget(QtWidgets.QWidget):
    """Interactive scatter-plot widget for exploring fitted Raman parameters.

    The widget plots one fitted quantity against another for the current ROI and can
    optionally:

    - show all points in addition to ROI points,
    - color ROI points by a third quantity using a LUT,
    - link its LUT to an external view widget,
    - highlight the point corresponding to a selected map position.
    """

    def __init__(self, args):
        """Create the widget, build the UI, and connect signals.

        Parameters
        ----------
        args : Any
            Argument forwarded to :class:`~PyQt6.QtWidgets.QWidget` (typically the parent).
        """
        logger.debug("Initializing StatisticWidget...")
        QtWidgets.QWidget.__init__(self, args)

        # Define default label style for plot axes
        self.labelStyle = {"color": "#000000", "font-size": "12pt"}
        self.labelStyle = {"font-size": "12pt"}

        # Initialize list to store comboBox items
        self.liste_comboBox_names = []

        # Set up grid layout for organizing widgets within StatisticWidget
        self.l = QtWidgets.QGridLayout()
        self.setLayout(self.l)

        # Create and configure label and comboBox for selecting the primary plot attribute
        self.textA = QtWidgets.QLabel("Plot")
        self.textA.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.comboBox_A = QtWidgets.QComboBox()

        # Create and configure label and comboBox for selecting the comparison attribute (vs.)
        self.textB = QtWidgets.QLabel("vs.")
        self.textB.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.comboBox_B = QtWidgets.QComboBox()

        # Create a third comboBox for additional attribute selection
        self.comboBox_C = QtWidgets.QComboBox()

        # Set up the plot widget and configure axes visibility and font style
        self.plt = pg.PlotWidget()
        theme = QtWidgets.QApplication.instance().property("theme")
        color_palette = qdarktheme.load_palette(theme)
        window_color = color_palette.window().color().name()
        text_color = color_palette.windowText().color().name()
        pg.setConfigOption("background", window_color)
        pg.setConfigOption("foreground", text_color)
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

        # Add checkboxes for controlling data display options
        self.showAll = QtWidgets.QCheckBox("Show all")
        self.showAll.setToolTip("Show all data in addition to the region of interest (ROI)")
        self.exclude = QtWidgets.QCheckBox("Exclude 5% edges")  # Option to exclude edge values
        self.colored = QtWidgets.QCheckBox("Colored")  # Option to color-code data points
        self.link_colors = QtWidgets.QCheckBox("Link colorscale")  # Option to link color scales

        # Add widgets to the layout grid
        self.l.addWidget(self.textA, 0, 0)
        self.l.addWidget(self.comboBox_A, 0, 1)
        self.l.addWidget(self.textB, 0, 2)
        self.l.addWidget(self.comboBox_B, 0, 3)
        self.l.addWidget(self.comboBox_C, 0, 4)
        self.l.addWidget(self.plt, 1, 0, 1, 4)
        self.l.addWidget(self.showAll, 2, 2)
        self.l.addWidget(self.colored, 2, 3)
        self.l.addWidget(self.link_colors, 2, 4)

        # Populate comboBoxes with items
        self.addElementsToBoxes(self.comboBox_A)
        self.addElementsToBoxes(self.comboBox_B)
        self.addElementsToBoxes(self.comboBox_C)

        # Set default selected indices for comboBoxes
        self.comboBox_A.setCurrentIndex(11)
        self.comboBox_B.setCurrentIndex(3)
        self.comboBox_C.setCurrentIndex(10)

        # Connect comboBox selection changes and checkbox states to update methods
        self.comboBox_A.currentIndexChanged.connect(self.update_Data)
        self.comboBox_B.currentIndexChanged.connect(self.update_Data)
        self.comboBox_C.currentIndexChanged.connect(self.update_Data)
        self.showAll.stateChanged.connect(self.update_Data)
        self.exclude.stateChanged.connect(self.update_Data)
        self.colored.stateChanged.connect(self.update_Data)
        self.link_colors.stateChanged.connect(self.handle_checkBox_link)

        # Create a plot item for highlighting data points
        self.highlight = pg.PlotDataItem()
        self.plt.addItem(self.highlight)

        # Set up a color scale (HistogramLUTWidget) for data visualization
        self.lut = pg.HistogramLUTWidget()
        self.l.addWidget(self.lut, 1, 4)
        self.connect_lutData()

        # Connect LUT color scale changes to update method
        self.lut.sigLevelChangeFinished.connect(self.update_after_lut_change)
        self.lut.gradient.sigGradientChangeFinished.connect(self.update_after_lut_change)

        # Internal state used by update_Data/update_Plot
        self.pos = None
        self.roi = None
        self.imv = None
        self.data = None
        self.keys = None
        self.labels = None
        self.view_widget_imv = None

        logger.info("StatisticWidget initialized.")

    def connect_lutData(self):
        """Attach the LUT to a temporary ImageItem.

        pyqtgraph's :class:`~pyqtgraph.HistogramLUTWidget` requires an ImageItem to
        compute and display histogram/levels. This widget uses a temporary ImageItem
        for that purpose.
        """
        logger.debug("Connecting LUT to temporary ImageItem.")
        self.imv_temp = pg.ImageItem()
        self.lut.setImageItem(self.imv_temp)

    def handle_checkBox_link(self):
        """Link or unlink this widget's LUT to an external view.

        When *Link colorscale* is enabled, this widget hides its own LUT control and
        mirrors gradient/levels from the connected external view (``view_widget_imv``).
        """
        logger.debug("Link colorscale toggled: %s", self.link_colors.isChecked())

        if self.link_colors.isChecked():
            # Hide local color scale and use external view's color scale
            if self.view_widget_imv is None:
                logger.warning("Cannot link colorscale: view_widget_imv is not set.")
                self.link_colors.setChecked(False)
                return

            self.lut.hide()
            try:
                self.lut.gradient.restoreState(
                    self.view_widget_imv.getHistogramWidget().gradient.saveState()
                )
                levels = self.view_widget_imv.getLevels()
                self.lut.setLevels(levels[0], levels[1])
                self.lut.setHistogramRange(levels[0], levels[1])
                self.lut.update()
                logger.info("Linked StatisticWidget LUT to external view widget LUT.")
            except Exception:
                logger.exception("Failed to link colorscale to external view widget.")
        else:
            # Show local color scale
            self.lut.show()
            logger.info("Unlinked StatisticWidget LUT from external view widget (using local LUT).")

        self.update_after_lut_change()

    def roi_update(self, roi, img):
        """Receive ROI/image updates and refresh the plot.

        Parameters
        ----------
        roi : object
            ROI object providing ``getArrayRegion``.
        img : object
            ImageItem (or compatible) used by ``roi.getArrayRegion``.
        """
        logger.debug("ROI update received; triggering statistic update.")
        self.roi = roi
        self.imv = img
        self.update_Data()

    def setData(self, dat, lut=None, lists=None):
        """Set the backing data and optional metadata used by the UI.

        Parameters
        ----------
        dat : object
            Data provider; must expose ``get_fitresults()``.
        lut : object, optional
            External image/LUT provider used for linking colorscales.
        lists : list, optional
            Sequence of lists as used by the main application:
            ``[names, icons, keys, mpl_labels, labels]``.
        """
        logger.info("Setting data for StatisticWidget.")
        self.dat = dat
        if lists is not None:
            self.liste_comboBox_names = lists[0]
            self.liste_comboBox_icons = lists[1]
            self.keys = lists[2]
            self.mpl_labels = lists[3]
            self.labels = lists[4]
            logger.debug("Dropdown lists provided (items=%d).", len(self.liste_comboBox_names))
        self.data = self.dat.get_fitresults()  # Retrieve data fit results
        self.view_widget_imv = lut  # Link external color scale, if provided
        logger.debug(
            "Fit results set (keys=%d).", len(self.data) if hasattr(self.data, "__len__") else -1
        )

    def get_color(self, value):
        """Map a numeric value to a QColor using the current LUT levels.

        Parameters
        ----------
        value : float
            Value to map onto the LUT.

        Returns:
        -------
        QtGui.QColor
            The corresponding color.
        """
        x0, x1 = self.lut.getLevels()
        if value < x0:
            return self.lut.gradient.getColor(0, toQColor=True)
        elif value > x1:
            return self.lut.gradient.getColor(1, toQColor=True)
        else:
            return self.lut.gradient.getColor((value - x0) / (x1 - x0), toQColor=True)

    def update_Plot(self, pos):
        """Highlight the point corresponding to a selected map position.

        Parameters
        ----------
        pos : QtCore.QPointF
            Position in map pixel coordinates (x, y) used to index the fit-result arrays.
        """
        logger.debug("Statistics: update_Plot triggered (pos=%s).", pos)
        self.pos = pos
        xpos = int(pos.x())
        ypos = int(pos.y())
        if xpos >= 0 and ypos >= 0:
            try:
                x = self.data[self.keys[self.comboBox_B.currentIndex()]][xpos, ypos]
                y = self.data[self.keys[self.comboBox_A.currentIndex()]][xpos, ypos]
                # What about the case where the position is outside the graphene regione?
                if np.isfinite(x) and np.isfinite(y):
                    self.highlight.show()
                    self.highlight.setData(
                        x=np.array([x]),
                        y=np.array([y]),
                        symbol="p",
                        symbolSize=8,
                        symbolBrush="r",
                        pen=None,
                    )
                else:
                    self.highlight.hide()
            except Exception:
                logger.debug(
                    "Failed to update highlighted point at (%d,%d).", xpos, ypos, exc_info=False
                )

    def update_after_lut_change(self):
        """Refresh the plot after LUT levels/gradient changes."""
        logger.debug("LUT changed; updating plot (autoscale=False).")
        self.update_Data(autoscale=False)

    def update_Data(self, index=None, autoscale=True):
        """Recompute and redraw the scatter plot.

        The plotted quantities are controlled by the three combo boxes:
        ``A`` (y-axis), ``B`` (x-axis), and ``C`` (color axis).

        Parameters
        ----------
        index : int, optional
            Compatibility parameter for Qt signals; not used.
        autoscale : bool, default True
            Whether to autoscale the LUT levels from the current ROI z-data.
        """
        logger.debug("Statistic update_Data called (index=%s, autoscale=%s).", index, autoscale)
        self.plt.clear()

        if self.data is None or self.keys is None or self.labels is None:
            logger.debug(
                "StatisticWidget not fully initialized with data/keys/labels; skipping update."
            )
            return
        if self.roi is None or self.imv is None:
            logger.debug("StatisticWidget ROI/imv not set yet; skipping update.")
            return

        # Retrieve selected data for x, y, and z axes
        try:
            key_x = self.keys[self.comboBox_B.currentIndex()]
            key_y = self.keys[self.comboBox_A.currentIndex()]
            key_z = self.keys[self.comboBox_C.currentIndex()]
            x = self.data[key_x]
            y = self.data[key_y]
            z = self.data[key_z]
        except Exception:
            logger.exception("Failed to retrieve selected statistic data arrays.")
            return

        # If 'Show all' is checked, get full datasets for x and y
        if self.showAll.isChecked():
            x_full = np.reshape(x.copy(), np.size(x))
            y_full = np.reshape(y.copy(), np.size(y))

        # Apply ROI to selected data arrays
        try:
            x = self.roi.getArrayRegion(x, self.imv)
            y = self.roi.getArrayRegion(y, self.imv)
            z = self.roi.getArrayRegion(z, self.imv)
        except Exception:
            logger.debug("Failed to apply ROI to statistic data.", exc_info=True)
            return

        # Configure color scale based on z values if 'Colored' is checked
        if self.colored.isChecked():
            if autoscale:
                try:
                    self.lut.setHistogramRange(np.nanmin(z), np.nanmax(z))
                    self.lut.setLevels(np.nanmin(z), np.nanmax(z))
                except Exception:
                    logger.debug("Failed to autoscale LUT from z values.", exc_info=True)
            self.lut.update()

        self.z = z

        # Exclude 5% edges if specified
        alpha = 1 - 0.05
        if self.exclude.isChecked() and self.showAll.isChecked():
            try:
                x_full, y_full = self.exclude_edges(x_full, y_full, alpha)
            except Exception:
                logger.debug("Failed to exclude edges for full data.", exc_info=True)

        # before plotting remove all nan values
        mask = np.isfinite(x) & np.isfinite(y)
        if self.colored.isChecked():
            mask = mask & np.isfinite(z)
        if not np.any(mask):
            logger.info("Skipping statistic scatter: no finite ROI points.")
            return
        x = x[mask]
        y = y[mask]
        z = z[mask]

        # do not plot in case only one datapoint is available
        xmin, xmax = float(np.min(x)), float(np.max(x))
        ymin, ymax = float(np.min(y)), float(np.max(y))
        if xmin == xmax and ymin == ymax and not self.showAll.isChecked():
            logger.info("Skipping statistic scatter: only one point to plot.")
            return

        # Plot all data points if 'Show all' is checked
        if self.showAll.isChecked():
            self.plt.plot(x_full, y_full, symbol="p", symbolSize=1, pen=None)

        # Plot ROI data points with color if 'Colored' is checked
        if self.colored.isChecked():
            try:
                self.color = np.array([self.get_color(i) for i in z])
                self.plt.plot(
                    x, y, symbol="p", symbolSize=5, pen=None, symbolPen=None, symbolBrush=self.color
                )
            except Exception:
                logger.debug("Failed to plot colored ROI points.", exc_info=True)
        else:
            self.plt.plot(x, y, symbol="p", symbolSize=5, pen=None, symbolPen=None)

        # Set axis labels
        self.plt.setLabel("left", self.get_label(self.comboBox_A.currentIndex()), **self.labelStyle)
        self.plt.setLabel(
            "bottom", self.get_label(self.comboBox_B.currentIndex()), **self.labelStyle
        )

        # Add highlight item and update plot with specified position
        self.plt.addItem(self.highlight)
        try:
            if self.pos is not None:
                self.update_Plot(self.pos)
        except Exception:
            logger.debug("Failed to update highlighted point after redraw.", exc_info=True)

    def exclude_edges(self, x_full, y_full, alpha):
        """Drop points near the extremes (heuristic outlier trimming).

        Parameters
        ----------
        x_full, y_full : np.ndarray
            Flattened arrays of x/y values.
        alpha : float
            Fraction of the range to keep (e.g. ``0.95`` keeps the central 95%).

        Returns:
        -------
        tuple[np.ndarray, np.ndarray]
            Filtered ``(x_full, y_full)`` arrays.
        """
        x_full = x_full[
            np.abs(y_full - y_full.mean()) < alpha * (y_full.max() - y_full.mean())
        ].flatten()
        y_full = y_full[
            np.abs(x_full - x_full.mean()) < alpha * (x_full.max() - x_full.mean())
        ].flatten()
        return x_full, y_full

    def get_label(self, index):
        """Return the human-readable label for a combo box entry.

        Parameters
        ----------
        index : int
            Index into ``self.labels``.

        Returns:
        -------
        str
            Label text, or an empty string if labels are not configured.
        """
        return self.labels[index] if self.labels is not None else ""

    def setCross(self, c):
        """Store a crosshair object for interaction with other widgets.

        Parameters
        ----------
        c : object
            Crosshair object supplied by the view widget.
        """
        logger.debug("Crosshair set on StatisticWidget.")
        self.cross = c

    def redraw_boxes(self, lists=None, settings=None):
        """Repopulate the combo boxes from the provided lists and refresh the plot.

        Parameters
        ----------
        lists : list, optional
            Sequence of lists as used by the main application:
            ``[names, icons, keys, mpl_labels, labels]``.
        settings : dict, optional
            Present for API compatibility; not used here.
        """
        logger.info("Redrawing StatisticWidget dropdown boxes.")
        if lists is not None:
            self.liste_comboBox_names = lists[0]
            self.liste_comboBox_icons = lists[1]
            self.keys = lists[2]
            self.mpl_labels = lists[3]
            self.labels = lists[4]

            # Populate comboBoxes with items
            self.addElementsToBoxes(self.comboBox_A, settings)
            self.addElementsToBoxes(self.comboBox_B, settings)
            self.addElementsToBoxes(self.comboBox_C, settings)

            # Set default selected indices and update data display
            self.comboBox_A.setCurrentIndex(11)
            self.comboBox_B.setCurrentIndex(3)
            self.comboBox_C.setCurrentIndex(10)
            self.update_Data()

    def addElementsToBoxes(self, box, settings=None):
        """Fill a combo box with items and their math-text icons.

        Parameters
        ----------
        box : QtWidgets.QComboBox
            The combo box to populate.
        settings : dict, optional
            Present for API compatibility; not used here.
        """
        box.clear()
        if self.liste_comboBox_names is not None:
            for i, name in enumerate(self.liste_comboBox_names):
                box.addItem("")
                box.setItemText(i, name)
                box.setIconSize(QtCore.QSize(30, 30))
                icon = utils.mathTex_to_QPixmap(self.liste_comboBox_icons[i], "xx-large")
                box.setItemIcon(i, QtGui.QIcon(icon))
