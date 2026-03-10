"""Qt dialog for exporting Raman analysis results and visualizations.

Provides :class:`ExportApp`, a modal Qt dialog that allows exporting maps, spectra,
scatter plots, and histograms to common formats (CSV, SVG, PNG). The module bridges
Qt-based application state with Matplotlib rendering to ensure exported figures
match the on-screen view, including colormaps, ROIs, and axis limits.
"""

from __future__ import annotations

import matplotlib
import matplotlib.colors as mcolors
import matplotlib.pyplot as pl
import numpy as np
from PyQt6 import QtWidgets


class ExportApp(QtWidgets.QDialog):
    """Modal dialog that lets the user export various visualizations / data.

    Parameters
    ----------
    keys : list[str]
        Keys used to access fit results / labels.
    parent : QWidget | None
        Optional parent widget.
    """

    def __init__(self, keys, parent=None):
        """Initialize the export dialog and its UI controls.

        Sets up the dialog layout, widgets, default values, and signal connections
        for exporting maps, spectra, and derived visualizations in various formats.

        Args:
            keys: List of keys used to access available fit results and labels.
            parent: Optional parent widget for the dialog.
        """
        super().__init__(parent)
        self.keys = keys

        layout = QtWidgets.QGridLayout(self)

        # Controls
        self.comboBox_Source = QtWidgets.QComboBox()
        self.comboBox_Format = QtWidgets.QComboBox()
        self.text_Source = QtWidgets.QLabel("Export Source")
        self.text_Format = QtWidgets.QLabel("Export Format")

        layout.addWidget(self.text_Source, 0, 0)
        layout.addWidget(self.comboBox_Source, 0, 1)
        layout.addWidget(self.text_Format, 1, 0)
        layout.addWidget(self.comboBox_Format, 1, 1)

        self.checkBox_ROI = QtWidgets.QCheckBox("Include ROI tools")
        self.checkBox_ROI.setToolTip(
            "Include ROI (Region of Interest) rectangle and spectrum selection cross."
        )
        layout.addWidget(self.checkBox_ROI, 2, 1)

        self.checkBox_CurrentView = QtWidgets.QCheckBox("Export Current View")
        self.checkBox_CurrentView.setToolTip(
            "Export only the currently visible range; otherwise export the full dataset."
        )
        layout.addWidget(self.checkBox_CurrentView, 3, 1)

        self.button_Export = QtWidgets.QPushButton("Export")
        self.button_Cancel = QtWidgets.QPushButton("Cancel")
        layout.addWidget(self.button_Export, 6, 1)
        layout.addWidget(self.button_Cancel, 6, 0)

        self.spinBox_Width = QtWidgets.QDoubleSpinBox()
        self.spinBox_Height = QtWidgets.QDoubleSpinBox()
        layout.addWidget(self.spinBox_Width, 4, 1)
        layout.addWidget(self.spinBox_Height, 5, 1)

        self.text_Width = QtWidgets.QLabel("Width (cm)")
        self.text_Height = QtWidgets.QLabel("Height (cm)")
        self.spinBox_Width.setToolTip("Figure width in centimeters")
        self.spinBox_Height.setToolTip("Figure height in centimeters")
        layout.addWidget(self.text_Width, 4, 0)
        layout.addWidget(self.text_Height, 5, 0)

        # Default figure size
        self.spinBox_Width.setValue(5.00)
        self.spinBox_Height.setValue(3.00)

        # Actions
        self.button_Cancel.clicked.connect(self.close_window)
        self.button_Export.clicked.connect(self.handle_export)

        # Source / format options
        self.comboBox_Source.addItems(["Map", "Spectrum", "Scatter Plot", "Histogram"])
        self.items_box_format()

        # Defaults
        self.checkBox_CurrentView.setChecked(False)

    def close_window(self) -> None:
        """Close the dialog."""
        self.close()

    def handle_export(self) -> None:
        """Dispatch export based on selected source and format."""
        source = self.comboBox_Source.currentText()
        fmt = self.comboBox_Format.currentText()

        if source == "Map":
            if fmt == "ASCII (.csv)":
                self.map_to_ascii()
            elif fmt == "Vector graphic (.svg)":
                self.map_to_svg()
            elif fmt == "Bitmap (.png)":
                self.map_to_png()

        elif source == "Spectrum":
            if fmt == "ASCII (.csv)":
                self.spectrum_to_ascii()
            elif fmt == "Vector graphic (.svg)":
                self.spectrum_to_svg()
            elif fmt == "Bitmap (.png)":
                self.spectrum_to_png()

        elif source == "Scatter Plot":
            if fmt == "ASCII (.csv)":
                self.scatter_to_ascii()
            elif fmt == "Vector graphic (.svg)":
                self.scatter_to_svg()
            elif fmt == "Bitmap (.png)":
                self.scatter_to_png()

        elif source == "Histogram":
            if fmt == "ASCII (.csv)":
                self.histo_to_ascii()
            elif fmt == "Vector graphic (.svg)":
                self.histo_to_svg()
            elif fmt == "Bitmap (.png)":
                self.histo_to_png()

    def items_box_format(self) -> None:
        """Populate the format combobox with supported export types."""
        self.comboBox_Format.clear()
        self.comboBox_Format.addItems(["ASCII (.csv)", "Vector graphic (.svg)", "Bitmap (.png)"])

    # --- Wiring to host application widgets ---------------------------------

    def connect_widgets(self, data, view, index, statistics, histo, mpl) -> None:
        """Connect external widgets that provide data and rendering state.

        Parameters
        ----------
        data : object
            Data widget; must provide get_fitresults(), get_xmap(), get_ymap().
        view : object
            View widget; must provide imv1/imv2 images/plots, ROI and cross info.
        index : int
            Index into `keys` / labels.
        statistics : object
            Statistics widget for scatter plots.
        histo : object
            Histogram widget.
        mpl : list[str]
            Matplotlib axis labels for each data channel.
        """
        self.data_widget = data
        self.view_widget = view
        self.index = index
        self.statistics_widget = statistics
        self.histo_widget = histo
        self.mpl_labels = mpl

    # --- Map exports ---------------------------------------------------------

    def map_to_ascii(self) -> None:
        """Export the current map as a CSV (tab-separated)."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Text Files (*.csv)"
        )
        if fileName:
            data = self.data_widget.get_fitresults()[self.keys[self.index]]
            data = np.transpose(data)

            header = ["x (mum)", "y (mum)", self.get_mpl_label(self.index)]
            sep = "\t"

            # Use context manager to ensure file is closed even if errors occur.
            with open(fileName, "w", encoding="utf-8", newline="") as fd:
                fd.write(sep.join(header) + "\n")
                for x in range(np.shape(data)[0]):
                    for y in range(np.shape(data)[1]):
                        fd.write(
                            f"{x * self.data_widget.get_xmap()[1]}"
                            f"{sep}{y * self.data_widget.get_ymap()[1]}"
                            f"{sep}{data[x, y]}\n"
                        )

    def _draw_map_common(self, fileName: str) -> None:
        """Common map drawing routine for SVG/PNG exports.

        Parameters
        ----------
        fileName : str
            Path to save the figure (extension determines the backend).
        """
        data = self.data_widget.get_fitresults()[self.keys[self.index]]

        # Build colormap from the view's lookup table to match on-screen colors.
        lut = self.view_widget.imv1.getHistogramWidget().getLookupTable(n=256)
        colors = np.array([x for x in lut]) / 255.0
        cm = mcolors.ListedColormap(colors)

        pl.figure()
        vmin, vmax = self.view_widget.imv1.getHistogramWidget().getLevels()
        extent = [0, self.data_widget.get_xmap()[-1], self.data_widget.get_ymap()[-1], 0]

        pl.imshow(np.transpose(data), extent=extent, cmap=cm, vmin=vmin, vmax=vmax)
        pl.xlabel("x ($\\mu$m)")
        pl.ylabel("y ($\\mu$m)")

        cb1 = pl.colorbar()
        cb1.set_label(self.get_mpl_label(self.index))

        # If requested, limit to currently visible view range.
        if self.checkBox_CurrentView.isChecked():
            xax = self.view_widget.plt.getAxis("bottom").range
            yax = self.view_widget.plt.getAxis("left").range
            xlim = [
                xax[0] * self.data_widget.get_xmap()[1],
                xax[1] * self.data_widget.get_xmap()[1],
            ]
            ylim = [
                yax[0] * self.data_widget.get_ymap()[1],
                yax[1] * self.data_widget.get_ymap()[1],
            ]
            pl.xlim(xlim)
            pl.ylim(ylim)

        # Optionally draw ROI rectangle and crosshair.
        if self.checkBox_ROI.isChecked():
            x_cross = int(self.view_widget.cross.pos().x()) * self.data_widget.get_xmap()[1]
            y_cross = int(self.view_widget.cross.pos().y()) * self.data_widget.get_ymap()[1]
            x_roi, y_roi = self.view_widget.roi.pos()
            dx_roi, dy_roi = self.view_widget.roi.size()
            x_roi *= self.data_widget.get_xmap()[1]
            y_roi *= self.data_widget.get_ymap()[1]
            dx_roi *= self.data_widget.get_xmap()[1]
            dy_roi *= self.data_widget.get_ymap()[1]
            angle = self.view_widget.roi.angle()

            pl.axvline(x_cross, color="black")
            pl.axhline(y_cross, color="black")

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
            pl.gca().add_patch(rect)

        pl.tight_layout()
        pl.savefig(fileName)
        pl.close()

    def map_to_svg(self) -> None:
        """Export the current map as an SVG vector graphic."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Scalable vector graphic (*.svg)"
        )
        if fileName:
            self._draw_map_common(fileName)

    def map_to_png(self) -> None:
        """Export the current map as a PNG bitmap."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Image files (*.png)"
        )
        if fileName:
            self._draw_map_common(fileName)

    # --- Spectrum exports ----------------------------------------------------

    def spectrum_to_ascii(self) -> None:
        """Export the current spectrum and fit as a CSV (tab-separated)."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Text Files (*.csv)"
        )
        if fileName:
            curves = self.view_widget.imv2.getPlotItem().curves
            data = []
            header = [
                "Raman shift DATA (1/cm)",
                "CCD Counts DATA",
                "Raman shift FIT (1/cm)",
                "CCD Counts FIT",
            ]

            for cu in curves:
                x, y = cu.getData()
                if x is None:
                    continue
                data.append((x, y))

            sep = "\t"
            # num_format = f"%0.{10}dg"
            num_format = f"%0.{10}d"
            num_rows = max((len(d[0]) for d in data), default=0)

            with open(fileName, "w", encoding="utf-8", newline="") as fd:
                fd.write(sep.join(header) + "\n")
                for i in range(num_rows):
                    for x, y in data:
                        fd.write((num_format % x[i]) + sep if i < len(x) else f" {sep}")
                        fd.write((num_format % y[i]) + sep if i < len(y) else f" {sep}")
                    fd.write("\n")

    def _draw_spectrum_common(self, fileName: str) -> None:
        """Common spectrum drawing routine for SVG/PNG exports."""
        curves = self.view_widget.imv2.getPlotItem().curves
        pl.figure(figsize=(self.spinBox_Width.value(), self.spinBox_Height.value()))
        for i, cu in enumerate(curves):
            x, y = cu.getData()
            if x is None:
                continue
            if i == 0:
                pl.plot(x, y, ".")  # data points
            elif i == 1:
                pl.plot(x, y)  # fit curve

        pl.xlabel("Raman shift (cm$^{-1}$)")
        pl.ylabel("Counts")

        if self.checkBox_CurrentView.isChecked():
            pl.xlim(self.view_widget.imv2.getAxis("bottom").range)
            pl.ylim(self.view_widget.imv2.getAxis("left").range)

        pl.tight_layout()
        pl.savefig(fileName)
        pl.close()

    def spectrum_to_svg(self) -> None:
        """Export the current spectrum as an SVG vector graphic."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Scalable vector graphic (*.svg)"
        )
        if fileName:
            self._draw_spectrum_common(fileName)

    def spectrum_to_png(self) -> None:
        """Export the current spectrum as a PNG bitmap."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Image files (*.png)"
        )
        if fileName:
            self._draw_spectrum_common(fileName)

    # --- Scatter plot exports ------------------------------------------------

    def scatter_to_ascii(self) -> None:
        """Export the current scatter data as a CSV (tab-separated)."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Text Files (*.csv)"
        )
        if fileName:
            # Only the first curve is the scatter points
            curve = self.statistics_widget.plt.getPlotItem().curves[0]
            x, y = curve.getData()
            header = [
                self.statistics_widget.comboBox_B.currentText(),
                self.statistics_widget.comboBox_A.currentText(),
            ]
            sep = "\t"
            num_format = f"%0.{10}dg"
            n = max(len(x or []), len(y or []))

            with open(fileName, "w", encoding="utf-8", newline="") as fd:
                fd.write(sep.join(header) + "\n")
                for i in range(n):
                    fd.write((num_format % x[i]) + sep if i < len(x) else f" {sep}")
                    fd.write((num_format % y[i]) + sep if i < len(y) else f" {sep}")
                    fd.write("\n")

    def _draw_scatter_common(self, fileName: str) -> None:
        """Common scatter drawing routine for SVG/PNG exports."""
        curves = self.statistics_widget.plt.getPlotItem().curves

        # Rebuild colormap to match the widget when colored-by-Z is enabled.
        lut = self.statistics_widget.lut.getLookupTable(n=256)
        colors = np.array([x for x in lut]) / 255.0
        cm = mcolors.ListedColormap(colors)

        if self.statistics_widget.colored.isChecked():
            z = self.statistics_widget.z
            vmin, vmax = self.statistics_widget.lut.getLevels()
        else:
            z = vmin = vmax = None

        pl.figure(figsize=(self.spinBox_Width.value(), self.spinBox_Height.value()))
        for i, cu in enumerate(curves):
            x, y = cu.getData()
            if x is None:
                continue
            if i == 0:
                if self.statistics_widget.colored.isChecked():
                    pl.scatter(x, y, c=z, vmin=vmin, vmax=vmax, s=5, cmap=cm)
                else:
                    pl.scatter(x, y, s=5)
            elif i == 1:
                pl.plot(x, y)

        if self.statistics_widget.colored.isChecked():
            cb1 = pl.colorbar()
            cb1.set_label(self.get_mpl_label(self.statistics_widget.comboBox_C.currentIndex()))

        pl.xlabel(self.get_mpl_label(self.statistics_widget.comboBox_B.currentIndex()))
        pl.ylabel(self.get_mpl_label(self.statistics_widget.comboBox_A.currentIndex()))

        if self.checkBox_CurrentView.isChecked():
            pl.xlim(self.statistics_widget.plt.getAxis("bottom").range)
            pl.ylim(self.statistics_widget.plt.getAxis("left").range)

        pl.tight_layout()
        pl.savefig(fileName)
        pl.close()

    def scatter_to_svg(self) -> None:
        """Export the current scatter plot as an SVG vector graphic."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Scalable vector graphic (*.svg)"
        )
        if fileName:
            self._draw_scatter_common(fileName)

    def scatter_to_png(self) -> None:
        """Export the current scatter plot as a PNG bitmap."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Image files (*.png)"
        )
        if fileName:
            self._draw_scatter_common(fileName)

    # --- Histogram exports ---------------------------------------------------

    def histo_to_ascii(self) -> None:
        """Export the histogram data (bin centers vs. counts) as a CSV."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Text Files (*.csv)"
        )
        if fileName:
            # Histogram curve is at index 0
            curve = self.histo_widget.plt.getPlotItem().curves[0]
            x, y = curve.getData()
            header = [self.histo_widget.comboBox_B.currentText(), "#"]
            sep = "\t"
            num_format = f"%0.{10}dg"
            n = max(len(x or []), len(y or []))

            with open(fileName, "w", encoding="utf-8", newline="") as fd:
                fd.write(sep.join(header) + "\n")
                for i in range(n):
                    fd.write((num_format % x[i]) + sep if i < len(x) else f" {sep}")
                    fd.write((num_format % y[i]) + sep if i < len(y) else f" {sep}")
                    fd.write("\n")

    def _draw_histo_common(self, fileName: str) -> None:
        """Common histogram drawing routine for SVG/PNG exports."""
        data = self.histo_widget.x
        nBins = self.histo_widget.nBins
        pl.figure(figsize=(self.spinBox_Width.value(), self.spinBox_Height.value()))
        pl.hist(data, bins=nBins)
        pl.xlabel(self.get_mpl_label(self.histo_widget.comboBox_B.currentIndex()))
        pl.ylabel("#")

        if self.checkBox_CurrentView.isChecked():
            pl.xlim(self.histo_widget.plt.getAxis("bottom").range)
            pl.ylim(self.histo_widget.plt.getAxis("left").range)

        pl.tight_layout()
        pl.savefig(fileName)
        pl.close()

    def histo_to_svg(self) -> None:
        """Export the histogram as an SVG vector graphic."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Scalable vector graphic (*.svg)"
        )
        if fileName:
            self._draw_histo_common(fileName)

    def histo_to_png(self) -> None:
        """Export the histogram as a PNG bitmap."""
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export to", "", "Image files (*.png)"
        )
        if fileName:
            self._draw_histo_common(fileName)

    # --- Utilities -----------------------------------------------------------

    def get_mpl_label(self, index: int) -> str:
        """Return the matplotlib label string for the given channel index."""
        return self.mpl_labels[index]
