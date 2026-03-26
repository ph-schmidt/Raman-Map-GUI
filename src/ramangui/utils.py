"""Utility helpers for settings, data slicing, and Qt-friendly math text rendering.

This module centralizes small helper functions used throughout the GUI:

- Creating and restoring default application settings (via :class:`easysettings.EasySettings`).
- Extracting a subset of a spectrum within a given x-range.
- Rendering LaTeX-like math text to a :class:`~PyQt6.QtGui.QPixmap` using Matplotlib,
  for use as icons/labels in Qt widgets.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from easysettings import EasySettings
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PyQt6 import QtGui

DEFAULT_SETTINGS = {
    "StrainType": "uniaxial",  # uniaxial or biaxial
    "Slope_Strain": 2.2,
    "Slope_Doping": 0.4,
    "ScanDirection": 0,
    "Gamma_G_0": 15,
    "Gamma_2D_0": 25,
    "Gamma_D_0": 10,
    "omega_G_0": 1585,
    "omega_2D_0": 2675,
    "omega_D_0": 1350,
    "spec_width_G": 120,
    "spec_width_2D": 170,
    "spec_width_D": 100,
    "omega_2D_maxError": 3,
    "area_2D_min": 50,
    "area_2D_max": 1e7,
    "Gamma_G_min": 3,
    "Gamma_G_max": 70,
    "Gamma_2D_min": 7,
    "Gamma_2D_max": 110,
    "UseFitMask": 1,
    "LaserWavelength": 532,
    "4_P_mode": False,
    "omega_peak_1": 2650,
    "omega_peak_2": 2685,
    "omega_peak_3": 2700,
    "omega_peak_4": 2720,
    "Gamma_peak_1": 20,
    "Gamma_peak_2": 20,
    "Gamma_peak_3": 20,
    "Gamma_peak_4": 20,
}


def restore_default_settings(settings):
    """Reset a settings object to the application's default values.

    Parameters
    ----------
    settings : easysettings.EasySettings
        Settings instance to modify in-place.

    Returns:
    -------
    easysettings.EasySettings
        The same settings object, after defaults have been written and saved.
    """
    for key, value in DEFAULT_SETTINGS.items():
        settings.set(key, value)

    settings.save()
    return settings


def create_settings(file):
    """Create a settings file and populate it with default values.

    Parameters
    ----------
    file : str | os.PathLike
        Path to the configuration file.

    Returns:
    -------
    easysettings.EasySettings
        Settings object backed by ``file`` and initialized with defaults.
    """
    settings = EasySettings(file)
    restore_default_settings(settings)
    return settings


def ensure_settings_defaults(settings, logger=None):
    """Ensure all required settings exist; fill missing ones with defaults.

    Parameters
    ----------
    settings : easysettings.EasySettings
        Settings instance to modify in-place.
    logger : logging.Logger, optional
        Logger used to report inserted keys.

    Returns:
    -------
    easysettings.EasySettings
        The same settings object, after missing defaults have been written.
    """
    missing_keys = []

    for key, default_value in DEFAULT_SETTINGS.items():
        if settings.get(key) == "":
            settings.set(key, default_value)
            missing_keys.append(key)

    if missing_keys:
        settings.save()
        if logger is not None:
            logger.info("Inserted missing default settings: %s", missing_keys)
    else:
        if logger is not None:
            logger.debug("No missing settings found.")

    return settings


def subset(x, y, x0, x1):
    """Return the subset of (x, y) where ``x0 <= x <= x1``.

    Parameters
    ----------
    x : array-like
        X-axis values.
    y : array-like
        Y values (same length as ``x``).
    x0, x1 : float
        Inclusive bounds in x.

    Returns:
    -------
    tuple[np.ndarray, np.ndarray]
        ``(xn, yn)`` arrays containing only values within the requested x-range.
    """
    xn = []
    yn = []
    for i, v in enumerate(x):
        if x0 <= v <= x1:
            xn.append(x[i])
            yn.append(y[i])

    return (np.array(xn), np.array(yn))


def mathTex_to_QPixmap(mathTex, fs):
    """Render a LaTeX-like math expression to a Qt pixmap.

    This is typically used to generate math-styled icons for combo boxes and labels.

    Parameters
    ----------
    mathTex : str
        Math expression understood by Matplotlib's mathtext engine.
    fs : int | float
        Font size passed to Matplotlib for rendering.

    Returns:
    -------
    PyQt6.QtGui.QPixmap
        Pixmap containing the rendered expression with a transparent background.
    """
    # Create a new matplotlib figure with a large size to ensure sufficient resolution
    fig = mpl.figure.Figure(figsize=[50, 50])
    fig.patch.set_facecolor("none")
    fig.set_canvas(FigureCanvasAgg(fig))
    renderer = fig.canvas.get_renderer()

    # Add an axes that fills the entire figure (no margins) and hide it
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.patch.set_facecolor("none")

    # Add the text containing the LaTeX math expression
    t = ax.text(0, 0, mathTex, ha="left", va="bottom", fontsize=fs)

    # Compute tight figure size to fit the rendered text
    fwidth, fheight = fig.get_size_inches()
    fig_bbox = fig.get_window_extent(renderer)
    text_bbox = t.get_window_extent(renderer)

    tight_fwidth = text_bbox.width * fwidth / fig_bbox.width
    tight_fheight = text_bbox.height * fheight / fig_bbox.height
    fig.set_size_inches(tight_fwidth, tight_fheight)

    # Render the figure to a buffer in RGBA format
    buf, size = fig.canvas.print_to_buffer()

    # Convert the buffer to a QImage and then to a QPixmap
    qimage = QtGui.QImage.rgbSwapped(
        QtGui.QImage(buf, size[0], size[1], QtGui.QImage.Format.Format_ARGB32)
    )
    qpixmap = QtGui.QPixmap(qimage)

    plt.close(fig)
    return qpixmap
