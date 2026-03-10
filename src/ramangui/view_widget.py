"""Image/spectrum viewer widget for Raman map exploration.

This module defines :class:`~ramangui.view_widget.ViewWidget`, a composite PyQt6 widget
built on top of *pyqtgraph* for interactive Raman mapping analysis.

The widget combines:

- An :class:`pyqtgraph.ImageView` for displaying 2D map data (fit results, masks, etc.).
- A :class:`pyqtgraph.PlotWidget` for displaying the spectrum at the current cursor position,
  including both raw data and the fitted model spectrum.
- Interactive tools: a movable crosshair, a ROI (rectangular or circular), and optional
  persistence of ROI and colormap settings to ``.npy`` sidecar files.

The widget can forward ROI updates and cursor selections to external statistics and
histogram widgets (when connected).
"""

import logging

import numpy as np
import pyqtgraph as pg
import qdarktheme
from PyQt6 import QtCore, QtGui, QtWidgets

from ramangui import utils
from ramangui.crosshair import Crosshair

logger = logging.getLogger(__name__)


class ViewWidget(QtWidgets.QWidget):
    """Interactive map + spectrum viewer.

    The upper panel renders a 2D map in an :class:`pyqtgraph.ImageView`. The lower
    panel shows the spectrum at the current crosshair location, including the raw
    spectrum and the fitted spectrum (where available).

    Notes:
    -----
    This widget persists some UI state to disk (if a filename is set):

    - ROI state is saved to ``<filename>.roi.npy``.
    - Colormap/levels are saved per channel to
      ``<filename>.colorbar<index>.npy`` and ``<filename>.colorbar_values<index>.npy``.
    """

    def __init__(self, args):
        """Initialize the widget layout, plots, and interaction tools.

        Parameters
        ----------
        args : Any
            Argument passed to the underlying :class:`PyQt6.QtWidgets.QWidget`
            constructor. (Kept for backward compatibility with existing UI code.)
        """
        logger.debug("Initializing ViewWidget...")
        QtWidgets.QWidget.__init__(self, args)

        # Define default label style for plot axes
        # labelStyle = {'color': '#000000', 'font-size': '12pt'}
        labelStyle = {"font-size": "12pt"}

        # Set up grid layout for organizing widgets within ViewWidget
        self.l = QtWidgets.QGridLayout()
        self.setLayout(self.l)

        # Set global plot options for PyQtGraph
        theme = QtWidgets.QApplication.instance().property("theme")
        color_palette = qdarktheme.load_palette(theme)
        window_color = color_palette.window().color().name()
        text_color = color_palette.windowText().color().name()
        pg.setConfigOption("background", window_color)
        pg.setConfigOption("foreground", text_color)

        # Create a primary plot item for displaying data with configured axes
        self.plt = pg.PlotItem()
        self.plt.showAxis("left", show=True)
        self.plt.showAxis("right", show=True)
        self.plt.showAxis("top", show=True)
        self.plt.showAxis("bottom", show=True)
        self.plt.getAxis("bottom").setLabel("x", "m", **labelStyle)
        self.plt.getAxis("left").setLabel("y", "m", **labelStyle)

        # Customize label style for top and right axes (invisible)
        labelStyle_invisible = {"font-size": "1pt"}
        self.plt.getAxis("top").setLabel("x", "m", **labelStyle_invisible)
        self.plt.getAxis("right").setLabel("y", "m", **labelStyle_invisible)

        # Create an ImageView with custom plot for image display
        self.imv1 = pg.ImageView(view=self.plt)

        # Create a secondary PlotWidget for displaying additional plots
        self.imv2 = pg.PlotWidget()
        self.imv2.showAxis("left", show=True)
        self.imv2.showAxis("right", show=True)
        self.imv2.showAxis("top", show=True)
        self.imv2.showAxis("bottom", show=True)

        # Set labels for secondary plot axes
        self.imv2.setLabel("left", "CCD counts", **labelStyle)
        self.imv2.setLabel("bottom", "Raman shift (rel 1/cm)", **labelStyle)

        # Add image and plot widgets to layout
        self.l.addWidget(self.imv1, 0, 0)
        self.l.addWidget(self.imv2, 1, 0)

        # Configure row stretching for layout
        self.l.setRowStretch(0, 3)
        self.l.setRowStretch(1, 1)

        # Add Crosshair object for marking positions on the image view
        self.cross = Crosshair(pen=0.0)
        self.cross.hide()
        self.imv1.addItem(self.cross)
        self.cross.sigRegionChanged.connect(self.update_Plot)

        # Initialize data array and fonts
        self.data = []
        font = QtGui.QFont()
        font.setPixelSize(12)
        font2 = QtGui.QFont()
        font2.setPixelSize(1)  # For invisible axes

        # Set font and styles for secondary plot axes
        self.imv2.getAxis("bottom").tickFont = font
        self.imv2.getAxis("bottom").setStyle(tickTextOffset=12)
        self.imv2.getAxis("left").tickFont = font
        self.imv2.getAxis("left").setStyle(tickTextOffset=12)
        self.imv2.getAxis("right").tickFont = font2
        self.imv2.getAxis("right").setStyle(tickTextOffset=12)
        self.imv2.getAxis("top").tickFont = font2
        self.imv2.getAxis("top").setStyle(tickTextOffset=12)
        self.imv2.getAxis("top").setStyle(showValues=False)
        self.imv2.getAxis("right").setStyle(showValues=False)

        # Set font and style for primary plot axes
        self.plt.getAxis("bottom").tickFont = font
        self.plt.getAxis("bottom").setStyle(tickTextOffset=12)
        self.plt.getAxis("left").tickFont = font
        self.plt.getAxis("left").setStyle(tickTextOffset=12)

        # Hide ROI and menu buttons in the ImageView UI
        self.imv1.ui.roiBtn.hide()
        self.imv1.ui.menuBtn.hide()

        # Add a label for displaying the area of the ROI
        self.roi_area_label = QtWidgets.QLabel("ROI Area:")
        self.l.addWidget(self.roi_area_label, 2, 0)

        # Connect histogram widget signals for color setting changes
        self.imv1.getHistogramWidget().sigLevelChangeFinished.connect(self.save_color_settings)
        self.imv1.getHistogramWidget().gradient.sigGradientChangeFinished.connect(
            self.save_color_settings
        )

        # Initialize ROI save state
        self.roi_save_enabled = False

        # Internal state
        self.roi = None
        self.filename = None
        self.index = None
        self.counter = 0
        self.keys = None
        self.stat = None
        self.histo = None

        logger.info("ViewWidget initialized.")

    def changeROI_Tools(self, state):
        """Show or hide the ROI tools (ROI + crosshair).

        Parameters
        ----------
        state : bool
            If ``True``, show ROI and crosshair. If ``False``, hide them.
        """
        logger.debug("changeROI_Tools called (state=%s).", state)
        if self.roi is None:
            logger.debug("ROI not initialized yet; nothing to show/hide.")
            return

        if state:
            self.roi.show()
            self.cross.show()
        else:
            self.roi.hide()
            self.cross.hide()

    def resetROI(self):
        """Reset the ROI to cover the full image with zero rotation."""
        if self.roi is None:
            logger.debug("resetROI called but ROI is not initialized.")
            return

        logger.info("Resetting ROI to full image.")
        self.roi.setPos([0, 0])
        self.roi.setSize([self.imv1.getImageItem().width(), self.imv1.getImageItem().height()])
        self.roi.setAngle(0.0)

    def roi_area(self):
        """Compute ROI area and update the on-screen ROI area label.

        The label displays:

        - ROI area in µm²
        - Total graphene area (based on the mask) in µm²
        """
        if self.roi is None or self.data is None:
            logger.debug("roi_area called but ROI/data not ready.")
            return

        x, y = self.roi.size()
        num_pix = x * y
        xscale = self.data.get_xmap()[1] * 1e-6
        yscale = self.data.get_ymap()[1] * 1e-6
        scaling = xscale * yscale
        area = num_pix * scaling  # ROI area in m^2
        total_gr_area = np.nansum(self.data.get_mask()) * scaling  # Total graphene area in m^2
        self.roi_area_label.setText(
            "ROI Area: "
            + str(np.round(area * 1e12, 3))
            + " µm^2"
            + "   "
            + "Total graphene area: "
            + str(np.round(total_gr_area * 1e12, 3))
            + " µm^2"
        )

        logger.debug(
            "ROI area updated (roi_um2=%s, total_graphene_um2=%s).",
            np.round(area * 1e12, 3),
            np.round(total_gr_area * 1e12, 3),
        )

    def roi_update(self):
        """Propagate ROI changes and refresh derived ROI information.

        This forwards the ROI and image item to any connected statistic and histogram
        widgets (if present), then updates the ROI area readout.
        """
        logger.debug("roi_update triggered.")
        if self.stat is not None:
            try:
                self.stat.roi_update(self.roi, self.imv1.getImageItem())
            except Exception:
                logger.debug("Failed to forward ROI update to statistic widget.", exc_info=True)
        else:
            logger.debug("Statistic widget not connected; skipping.")

        if self.histo is not None:
            try:
                self.histo.roi_update(self.roi, self.imv1.getImageItem())
            except Exception:
                logger.debug("Failed to forward ROI update to histogram widget.", exc_info=True)
        else:
            logger.debug("Histogram widget not connected; skipping.")

        self.roi_area()

    def save_roi(self):
        """Persist the current ROI state to disk.

        The state is saved to ``<filename>.roi.npy`` if ROI saving is enabled via
        :attr:`roi_save_enabled`.
        """
        if not self.roi_save_enabled:
            logger.debug("ROI save skipped (roi_save_enabled=False).")
            return
        if self.roi is None or self.filename is None:
            logger.warning("ROI save requested but ROI or filename is missing.")
            return

        roi_state = self.roi.getState()
        name = self.filename + ".roi.npy"
        try:
            np.save(name, roi_state)
            logger.info("Saved ROI state to %s", name)
            logger.debug("ROI state content: %s", roi_state)
        except Exception:
            logger.exception("Failed to save ROI state to %s", name)

    def update_Plot(self):
        """Redraw the spectrum plot for the current crosshair position.

        This clears and repopulates the lower plot widget with:

        - Raw spectrum (scatter points)
        - Fitted spectrum (line), excluding NaNs

        It also forwards the cursor position to the connected statistic widget for
        highlight updates (if connected).
        """
        self.imv2.clear()
        pos = self.cross.pos()
        logger.debug("Spectrum: update_Plot triggered (pos=%s).", pos)

        if self.stat is not None:
            try:
                self.stat.update_Plot(pos)
            except Exception:
                logger.debug("Failed to forward plot update to statistic widget.", exc_info=True)

        x = int(pos.x())
        y = int(pos.y())
        if x >= 0 and y >= 0:
            try:
                xx = self.data.get_xaxis()
                yy = self.data.get_fit_intens()[x, y]
                yy2 = self.data.get_intens()[x, y]
                self.imv2.plot(
                    xx, yy2, symbol="p", symbolSize=4, symbolPen=None, pen=pg.mkPen(None)
                )

                xx_fit = xx[~np.isnan(yy)]
                yy_fit = yy[~np.isnan(yy)]
                self.imv2.plot(xx_fit, yy_fit, pen="r", connect="finite")
            except Exception:
                logger.debug(
                    "Failed to update secondary plot at (x=%d, y=%d).", x, y, exc_info=True
                )

    def set_filename(self, name):
        """Set the base filename used for saving sidecar state files.

        Parameters
        ----------
        name : str
            Base path/name used to save ROI and colormap settings.
        """
        self.filename = name
        logger.debug("Filename set: %s", name)

    def save_color_settings(self):
        """Save the current colormap gradient and level range to disk.

        The state is stored per displayed channel index as:

        - ``<filename>.colorbar<index>.npy`` for the gradient state
        - ``<filename>.colorbar_values<index>.npy`` for the (min, max) levels

        Notes:
        -----
        The first invocation is ignored (``counter == 0``) to preserve existing
        behavior during initial widget setup.
        """
        if self.counter == 0:
            logger.debug("Initial save_color_settings call ignored (counter==0).")
        else:
            if self.filename is None or self.index is None:
                logger.warning("Color settings save skipped (filename or index missing).")
            else:
                try:
                    colorbar = np.array([self.imv1.getHistogramWidget().gradient.saveState()])
                    name = self.filename + ".colorbar" + str(self.index) + ".npy"
                    np.save(name, colorbar)

                    colorbar_value = self.imv1.getLevels()
                    name2 = self.filename + ".colorbar_values" + str(self.index) + ".npy"
                    np.save(name2, colorbar_value)

                    logger.info("Saved color settings (%s, %s).", name, name2)
                except Exception:
                    logger.exception("Failed to save color settings.")

                try:
                    if self.stat is not None and self.stat.link_colors.isChecked():
                        logger.debug(
                            "Statistic colors are linked; updating statistic LUT from view."
                        )
                        self.stat.handle_checkBox_link()
                except Exception:
                    logger.debug("Failed to update linked statistic LUT.", exc_info=True)

        self.counter += 1

    def update_Data(self, dat=None, plotindex=None, roi_circle=False, keys=None):
        """Update the displayed map channel and ensure ROI/cursor are in sync.

        Parameters
        ----------
        dat : object, optional
            Data provider (typically :class:`~ramangui.data.DataObject`). Must provide
            ``get_fitresults()``, ``get_xmap()``, ``get_ymap()``, ``get_xaxis()``,
            ``get_fit_intens()``, and ``get_intens()``.
        plotindex : int, optional
            Index into ``keys`` selecting which map to display.
        roi_circle : bool, default=False
            If ``True``, initialize a :class:`pyqtgraph.CircleROI`. Otherwise use
            :class:`pyqtgraph.RectROI`.
        keys : list[str], optional
            Keys used to index into the fit results dictionary for selecting map channels.

        Notes:
        -----
        This method keeps existing behavior intact, including the fallback to a
        ``comboBox_View`` attribute if ``plotindex`` is not provided.
        """
        self.index = plotindex
        self.counter = 0
        if dat is not None:
            self.data = dat
            logger.debug("ViewWidget data object updated: %s", type(dat).__name__)
        if keys is not None:
            self.keys = keys

        if plotindex is None:
            plotindex = self.comboBox_View.currentIndex()

        logger.info(
            "Updating ViewWidget image (plotindex=%s, roi_circle=%s).", plotindex, roi_circle
        )

        try:
            self.imv1.setImage(self.data.get_fitresults()[self.keys[plotindex]])
        except Exception:
            logger.exception("Failed to set image for plotindex=%s.", plotindex)
            return

        try:
            colorbar = np.load(
                self.filename + ".colorbar" + str(plotindex) + ".npy",
                encoding="bytes",
                allow_pickle=True,
            )
            levels = np.load(
                self.filename + ".colorbar_values" + str(plotindex) + ".npy",
                encoding="bytes",
                allow_pickle=True,
            )
            self.imv1.getHistogramWidget().gradient.restoreState(colorbar[0])
            self.imv1.setHistogramRange(levels[0], levels[1])
            self.imv1.setLevels(levels[0], levels[1])
            logger.info("Loaded saved color settings for plotindex=%s.", plotindex)
        except Exception:
            try:
                vmin = np.nanmin(self.data.get_fitresults()[self.keys[plotindex]])
                vmax = np.nanmax(self.data.get_fitresults()[self.keys[plotindex]])
                self.imv1.setHistogramRange(vmin, vmax)
                self.imv1.setLevels(vmin, vmax)
                logger.debug("Applied default color range (vmin=%s, vmax=%s).", vmin, vmax)
            except Exception:
                logger.debug("Failed to set default color range.", exc_info=True)

        self.imv1.getHistogramWidget().update()

        try:
            yscale = self.data.get_ymap()[1] * 1e-6
            self.plt.getAxis("left").setScale(yscale)
            self.plt.getAxis("right").setScale(yscale)
            xscale = self.data.get_xmap()[1] * 1e-6
            self.plt.getAxis("bottom").setScale(xscale)
            self.plt.getAxis("top").setScale(xscale)
        except Exception:
            logger.debug("Failed to apply axis scaling.", exc_info=True)

        if self.roi is None:
            logger.debug("Creating ROI (roi_circle=%s).", roi_circle)
            if roi_circle:
                self.roi = pg.CircleROI(
                    [0, 0],
                    [self.imv1.getImageItem().width(), self.imv1.getImageItem().height()],
                    pen=0.0,
                )
            else:
                self.roi = pg.RectROI(
                    [0, 0],
                    [self.imv1.getImageItem().width(), self.imv1.getImageItem().height()],
                    pen=0.0,
                )
            self.roi.sigRegionChanged.connect(self.roi_update)
            self.roi.sigRegionChangeFinished.connect(self.save_roi)
            self.roi.addRotateHandle((0.5, 0), (0.5, 0.5))
            self.imv1.addItem(self.roi)

        self.roi_update()
        self.cross.show()
        self.update_Plot()

    def connect2statistic(self, stat):
        """Attach an external statistics widget to receive ROI/cursor updates.

        Parameters
        ----------
        stat : object
            Statistics widget instance (typically :class:`~ramangui.statistic_widget.StatisticWidget`).
        """
        self.stat = stat
        logger.debug("Connected StatisticWidget: %s", type(stat).__name__)

    def connect2histo(self, histo):
        """Attach an external histogram widget to receive ROI updates.

        Parameters
        ----------
        histo : object
            Histogram widget instance (typically :class:`~ramangui.histogram_widget.HistoWidget`).
        """
        self.histo = histo
        logger.debug("Connected HistoWidget: %s", type(histo).__name__)

    def addElementsToBoxes(self, box):
        """Populate a combo box with preconfigured labels and math-text icons.

        Parameters
        ----------
        box : PyQt6.QtWidgets.QComboBox
            Combo box to populate.

        Notes:
        -----
        This expects :attr:`liste_comboBox_names` and :attr:`liste_comboBox_icons`
        to exist on the instance (provided by the hosting application).
        """
        box.clear()
        if self.liste_comboBox_names is not None:
            for i in range(len(self.liste_comboBox_names)):
                box.addItem("")
                box.setItemText(i, self.liste_comboBox_names[i])
                box.setIconSize(QtCore.QSize(30, 30))
                icon = utils.mathTex_to_QPixmap(self.liste_comboBox_icons[i], "xx-large")
                box.setItemIcon(i, QtGui.QIcon(icon))
