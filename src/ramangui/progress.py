"""Progress dialog user interface.

This module defines a Qt Designer-style UI class for a simple progress dialog.
The dialog contains a progress bar and a text display area intended to show
status messages during long-running operations.
"""

import logging

from PyQt6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)


class Ui_Dialog:
    """UI definition for a progress dialog.

    This class defines a simple dialog window containing a progress bar and
    a text display area. It is intended to provide visual feedback during
    long-running operations.
    """

    def setupUi(self, Dialog):
        """Set up and initialize the progress dialog UI.

        This method creates and positions all UI elements within the dialog,
        including the progress bar and the text browser, and connects Qt slots
        automatically by object name.

        Parameters
        ----------
        Dialog : QDialog
            The dialog instance to which the UI elements are added.
        """
        logger.debug("Setting up Progress dialog UI...")

        Dialog.setObjectName("Dialog")
        Dialog.resize(320, 240)

        self.progressBar = QtWidgets.QProgressBar(Dialog)
        self.progressBar.setGeometry(QtCore.QRect(10, 160, 301, 41))
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName("progressBar")
        logger.debug("Progress bar created and initialized.")

        self.textBrowser = QtWidgets.QTextBrowser(Dialog)
        self.textBrowser.setGeometry(QtCore.QRect(10, 10, 301, 121))
        self.textBrowser.setObjectName("textBrowser")
        logger.debug("Text browser created.")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

        logger.info("Progress dialog UI setup complete.")

    def retranslateUi(self, Dialog):
        """Apply translatable text to the dialog.

        This method sets user-visible strings, allowing Qt's translation
        system to localize the dialog title if required.

        Parameters
        ----------
        Dialog : QDialog
            The dialog whose window title is set.
        """
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Progress"))
