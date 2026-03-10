"""Crosshair overlay widget for pyqtgraph views.

Provides a movable and toggleable crosshair composed of horizontal and
vertical InfiniteLine objects, implemented as a custom ROI.
"""

from pyqtgraph import ROI, InfiniteLine
from pyqtgraph.Qt import QtCore


class Crosshair(ROI):
    """Crosshair class for creating a movable, resizable crosshair overlay in a pyqtgraph view.

    This class inherits from ROI (Region of Interest) and represents a crosshair tool
    with both vertical and horizontal lines that can be added to a plot for reference.
    It includes methods for setting position and toggling visibility.
    """

    def __init__(self, pen="g"):
        """Initialize the Crosshair object.

        Parameters:
        pen (str): Color of the crosshair lines (default is green 'g').

        Creates a vertical and a horizontal line using InfiniteLine, both of which
        are immovable and form the crosshair structure.
        """
        # Create a vertical InfiniteLine with a 90-degree angle (vertical) that is not movable
        self.vLine = InfiniteLine(pen=pen, angle=90, movable=False)
        # Create a horizontal InfiniteLine with a 0-degree angle (horizontal) that is not movable
        self.hLine = InfiniteLine(pen=pen, angle=0, movable=False)

        # Call the parent constructor (ROI) to initialize the ROI with position (0,0), size (1,1), immovable, and snap-to-translate enabled
        super().__init__([0, 0], [1, 1], movable=False, translateSnap=True, pen=pen)

        # Set the size of the handle (control point) for the crosshair
        self.handleSize = 10
        # Add a translate handle at the center of the crosshair for moving it
        self.handle = self.addTranslateHandle([0, 0])

        # Set the parent item of the vertical and horizontal lines to this Crosshair instance
        self.vLine.setParentItem(self)
        self.hLine.setParentItem(self)

    def setPos(self, pos, **kwargs):
        """Set the position of the crosshair.

        Parameters:
        pos (QPointF or list): The new position to set for the crosshair.
        **kwargs: Additional keyword arguments to pass to the parent class's setPos method.

        This method also resets the position of the vertical and horizontal lines to align
        with the origin of the Crosshair's ROI.
        """
        # Call the parent class's setPos to set the position of the ROI itself
        super().setPos(pos, **kwargs)

        # Reset the position of the vertical and horizontal lines to the origin of the Crosshair's ROI
        self.vLine.p = QtCore.QPointF(0, 0)  # Set the vertical line's anchor point to (0,0)
        self.vLine.setPos(0)  # Position the vertical line at x = 0
        self.hLine.p = QtCore.QPointF(0, 0)  # Set the horizontal line's anchor point to (0,0)
        self.hLine.setPos(0)  # Position the horizontal line at y = 0

    def toggle_show(self, bol):
        """Show or hide the crosshair based on a boolean parameter.

        Parameters:
        bol (bool): If True, the crosshair is displayed and centered in the current view.
                    If False, the crosshair is hidden.

        When shown, the crosshair centers itself within the view box it is contained in.
        """
        # If bol is True, show the crosshair centered in its view box
        if bol:
            # Center the crosshair in the current view
            self.setPos(self.getViewBox().viewRect().center())
            self.show()  # Show the crosshair
        else:
            # Hide the crosshair if bol is False
            self.hide()
