"""Qt-based gradient editor dialog and widget.

Defines the Qt Designer-style UI class
:class:`Ui_Dialog_GradientEditor` and the interactive
:class:`GradientEditor` widget, which wraps a
:class:`pyqtgraph.GradientWidget` to allow loading, editing, and saving
color gradients. The gradient editor can be synchronized with an external
image viewer so that changes are applied directly to its histogram gradient.
"""

import logging

import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)


class Ui_Dialog_GradientEditor:
    """UI definition for the gradient editor dialog."""

    def setupUi(self, Dialog_GradientEditor: QtWidgets.QDialog) -> None:
        """Sets up the UI components and layout for the Gradient Editor dialog.

        Parameters
        ----------
        Dialog_GradientEditor:
            The dialog window where the UI is set up.
        """
        logger.debug("Setting up Gradient Editor dialog UI...")
        Dialog_GradientEditor.setObjectName("Dialog_GradientEditor")
        Dialog_GradientEditor.resize(634, 494)

        # Set dialog size policy to fixed (non-resizable)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Dialog_GradientEditor.sizePolicy().hasHeightForWidth())
        Dialog_GradientEditor.setSizePolicy(sizePolicy)

        # Set up the button box with a 'Close' button
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog_GradientEditor)
        self.buttonBox.setGeometry(QtCore.QRect(300, 450, 301, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Close)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName("buttonBox")

        # Add the custom GradientEditor widget to the dialog
        self.widget = GradientEditor(parent=Dialog_GradientEditor)
        self.widget.setGeometry(QtCore.QRect(10, 10, 611, 411))
        self.widget.setObjectName("widget")

        # Set up connections
        self.retranslateUi(Dialog_GradientEditor)

        # Close button emits rejected/close role; don't connect accepted here.
        self.buttonBox.rejected.connect(Dialog_GradientEditor.reject)

        QtCore.QMetaObject.connectSlotsByName(Dialog_GradientEditor)
        logger.debug("Gradient Editor dialog UI setup complete.")

    def retranslateUi(self, Dialog_GradientEditor: QtWidgets.QDialog) -> None:
        """Set the window title of the Gradient Editor dialog."""
        _translate = QtCore.QCoreApplication.translate
        Dialog_GradientEditor.setWindowTitle(
            _translate("Dialog_GradientEditor", "Color Gradient Editor")
        )


class GradientEditor(QtWidgets.QWidget):
    """Interactive widget for editing and synchronizing color gradients."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        """Initialize the GradientEditor widget."""
        logger.debug("Initializing GradientEditor widget...")
        super().__init__(parent)

        # Use layout to control sizing; don't set geometry here.
        self.viewer = None

        self.l = QtWidgets.QGridLayout(self)

        # Gradient editor widget from pyqtgraph
        self.gedit = pg.GradientWidget()
        self.l.addWidget(self.gedit, 0, 0, 1, 3)

        # Control buttons
        self.button_Load = QtWidgets.QPushButton("Load")
        self.button_Add = QtWidgets.QPushButton("Add Tick")
        self.button_Save = QtWidgets.QPushButton("Save")
        self.l.addWidget(self.button_Load, 1, 0)
        self.l.addWidget(self.button_Add, 1, 1)
        self.l.addWidget(self.button_Save, 1, 2)

        # Connect button actions
        self.button_Add.clicked.connect(self.add_tick)
        self.button_Load.clicked.connect(self.load)
        self.button_Save.clicked.connect(self.save)

        logger.debug("GradientEditor initialized and signals connected.")

    def add_tick(self) -> None:
        """Add a new tick mark to the gradient editor at the midpoint (0.5)."""
        logger.debug("Adding gradient tick at position 0.5.")
        self.gedit.addTick(0.5)

    def save(self) -> None:
        """Save the current gradient state to a .npy file."""
        name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save File",
            "",
            "Numpy data file (*.npy)",
        )
        logger.info("Save gradient requested: %s", name if name else "(cancelled)")

        if not name:
            logger.debug("Save cancelled by user.")
            return

        try:
            state = np.array([self.gedit.saveState()], dtype=object)
            np.save(name, state)
            logger.info("Gradient state saved successfully: %s", name)
        except Exception:
            logger.exception("Failed to save gradient state to: %s", name)

    def load(self) -> None:
        """Load a gradient state from a .npy file and apply it to the gradient editor."""
        name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Numpy data file (*.npy)",
        )
        logger.info("Load gradient requested: %s", name if name else "(cancelled)")

        if not name:
            logger.debug("Load cancelled by user.")
            return

        try:
            # GradientWidget state is a dict; np.load may require allow_pickle=True
            state = np.load(name, allow_pickle=True)[0]
            self.gedit.restoreState(state)
            logger.info("Gradient state loaded successfully: %s", name)
        except Exception:
            logger.exception("Failed to load gradient state from: %s", name)

    def connect_viewer(self, viewWidget_object) -> None:
        """Connect the gradient editor to an external viewer widget for synchronization."""
        self.viewer = viewWidget_object
        logger.info("GradientEditor connected to viewer: %s", type(viewWidget_object).__name__)
        try:
            self.gedit.restoreState(self.viewer.imv1.getHistogramWidget().gradient.saveState())
            logger.debug("GradientEditor state synchronized from viewer histogram gradient.")
        except Exception:
            logger.exception("Failed to synchronize GradientEditor state from viewer.")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Apply the gradient state back to the viewer when this widget is closed."""
        logger.info("Closing GradientEditor (applying state back to viewer).")
        try:
            if self.viewer is not None:
                self.viewer.imv1.getHistogramWidget().gradient.restoreState(self.gedit.saveState())
                logger.debug("Viewer histogram gradient updated from GradientEditor.")
        except Exception:
            logger.exception("Failed to apply GradientEditor state back to viewer.")
        event.accept()
