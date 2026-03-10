"""Qt dialog wrapper for the gradient editor widget.

Provides :class:`GradientApp`, a modal dialog that embeds the gradient editor UI
and connects it to an external view widget. This module acts as a lightweight
bridge between the Qt Designer–generated gradient editor and the main
application view.
"""

import logging

import PyQt6 as PyQt

from ramangui import gradient_editor

logger = logging.getLogger(__name__)


class GradientApp(PyQt.QtWidgets.QDialog):
    """Dialog for displaying and interacting with the gradient editor."""

    def __init__(self, viewWidget_object):
        """Initialize the gradient editor dialog.

        Args:
            viewWidget_object: External view widget that the gradient editor
                synchronizes with.
        """
        logger.debug(
            "Initializing GradientApp (viewWidget_object=%s)...", type(viewWidget_object).__name__
        )
        # Call the parent constructor for QDialog
        super().__init__()

        # Initialize the gradient editor UI
        self.ui = gradient_editor.Ui_Dialog_GradientEditor()
        self.ui.setupUi(self)  # Set up the dialog UI components
        logger.debug("Gradient editor UI setup completed.")

        # Connect the gradient editor widget to the external viewWidget_object
        self.ui.widget.connect_viewer(viewWidget_object)
        logger.info(
            "Gradient editor connected to view widget: %s", type(viewWidget_object).__name__
        )

        # Connect the 'Close' button in the dialog's button box to the close method
        self.ui.buttonBox.clicked.connect(self.close)
        logger.debug("Close button connected.")

    def close(self):
        """Close the gradient editor widget and the dialog window."""
        logger.info("Closing GradientApp dialog.")
        try:
            self.ui.widget.close()  # Close the gradient editor widget
        except Exception:
            logger.exception("Error while closing gradient editor widget.")
