"""Import Raman mapping data into a common in-memory structure.

Provides a base :class:`~ramangui.data_import.Data_Importer` interface and a
:class:`~ramangui.data_import.Witec_Matlab` implementation for reading WITec Matlab exports.
"""

import logging

import numpy as np
import scipy

logger = logging.getLogger(__name__)


class Data_Importer:
    """Base class for importing data. Defines structure for data loading and access methods.

    This class serves as an interface for loading various types of data, providing
    placeholders for essential methods. Subclasses must implement these methods.
    """

    def __init__(self, filename):
        """Initialize the Data_Importer with the given filename and load the file.

        Parameters:
        filename (str): Path to the file to be loaded.
        """
        self.filename = filename  # Store the filename
        logger.debug("Initializing Data_Importer (filename=%s)...", filename)
        self._load_file()  # Call method to load the file (to be implemented in subclasses)

    def get_data(self):
        """Retrieve imported data as a dictionary with various components.

        Returns:
        dict: A dictionary with 'xmap', 'ymap', 'spec', and 'intensarray' keys.
        """
        logger.debug("Collecting imported data into result dict.")
        result = {}
        result["xmap"] = self._get_xmap()
        result["ymap"] = self._get_ymap()
        result["spec"] = self._get_spec()
        result["intensarray"] = self._get_intensarray()

        logger.info(
            "Data collected: xmap=%s ymap=%s spec=%s intensarray=%s",
            getattr(result["xmap"], "shape", None),
            getattr(result["ymap"], "shape", None),
            getattr(result["spec"], "shape", None),
            getattr(result["intensarray"], "shape", None),
        )
        return result

    # Placeholder methods for subclasses to implement
    def _load_file(self):
        raise NotImplementedError

    def _get_xmap(self):
        raise NotImplementedError

    def _get_ymap(self):
        raise NotImplementedError

    def _get_spec(self):
        raise NotImplementedError

    def _get_intensarray(self):
        raise NotImplementedError


class Witec_Matlab(Data_Importer):
    """Subclass for importing data from a WITec Matlab file format.

    This class implements methods to load and extract data from Matlab files specific
    to WITec systems, providing access to data arrays such as xmap, ymap, spec, and intensarray.
    """

    def _load_file(self):
        """Load and process the data from a Matlab file using scipy.io.loadmat.

        Parses the file, handles both image and linescan data formats, and populates
        attributes like xmap, ymap, image dimensions, and intensity array.
        """
        logger.info("Loading WITec Matlab file: %s", self.filename)

        # Load data structure from Matlab file
        try:
            datastruct = scipy.io.loadmat(self.filename, struct_as_record=False, squeeze_me=True)
        except Exception:
            logger.exception("Failed to load Matlab file via scipy.io.loadmat: %s", self.filename)
            raise

        logger.debug("Matlab file loaded; keys=%s", list(datastruct.keys()))

        setname = None
        for key in list(datastruct.keys()):
            if not list(key)[0] == "_":  # Ignore private keys (starting with '_')
                setname = key
                break

        if setname is None:
            logger.error("No valid dataset key found in Matlab file (only private keys).")
            raise KeyError("No non-private key found in Matlab file.")

        logger.debug("Using dataset key: %s", setname)

        # Get the main data structure
        data = datastruct[setname]

        # Check if data is a linescan (no imagesize) or a full image scan
        try:
            is_linescan = np.size(data.imagesize) == 0
        except Exception:
            logger.exception("Could not determine whether dataset is linescan or image scan.")
            raise

        if is_linescan:
            # Process linescan data
            linescan = True
            logger.warning("Linescan detected. Linescans are currently not fully supported.")
            pointsperline = np.shape(data.data)[0] * 1.0
            linesperimage = 1.0
            specnum = pointsperline * linesperimage  # Total number of spectra
            self.xmap = data.axisscale[0, 0]  # X-axis values
            self.ymap = [0, 1]
            self.imagewidth = max(self.xmap) * (1 + 1 / (pointsperline - 1))  # Adjusted image width
            self.imageheight = 1
        else:
            # Process full image scan data
            linescan = False
            pointsperline = data.imagesize[1] * 1.0
            linesperimage = data.imagesize[0] * 1.0
            specnum = pointsperline * linesperimage  # Total number of spectra
            self.xmap = data.imageaxisscale[1, 0]  # X-axis values
            self.ymap = data.imageaxisscale[0, 0]  # Y-axis values
            self.imagewidth = max(self.xmap) * (1 + 1 / (pointsperline - 1))  # Adjusted image width
            self.imageheight = max(self.ymap) * (
                1 + 1 / (linesperimage - 1)
            )  # Adjusted image height

        logger.debug(
            "Scan parsed: linescan=%s pointsperline=%s linesperimage=%s specnum=%s imagewidth=%s imageheight=%s",
            linescan,
            pointsperline,
            linesperimage,
            specnum,
            self.imagewidth,
            self.imageheight,
        )

        # Store intensity and spectral data
        self.intens = data.data
        self.spec = data.axisscale[1, 0]

        logger.debug(
            "Loaded raw arrays: intens=%s spec=%s xmap=%s ymap=%s",
            getattr(self.intens, "shape", None),
            getattr(self.spec, "shape", None),
            getattr(self.xmap, "shape", None),
            getattr(self.ymap, "shape", None),
        )

        # Initialize and populate a 2D intensity array
        i = 0  # Index for iterating through intensity data
        if linescan:
            # Linescan case: Only one y point
            self.intensarray = np.empty((len(self.xmap), len(self.ymap) - 1), dtype=list)
            for x in range(len(self.xmap)):
                for y in range(len(self.ymap) - 1):
                    self.intensarray[x, y] = self.intens[i, :]
                    i += 1
        else:
            # Image scan case: Full 2D array of intensity values
            self.intensarray = np.empty((len(self.xmap), len(self.ymap)), dtype=list)
            for x in range(len(self.xmap)):
                for y in range(len(self.ymap)):
                    self.intensarray[x, y] = self.intens[i, :]
                    i += 1

        logger.info(
            "Intensity array constructed: intensarray_shape=%s (filled=%d)",
            getattr(self.intensarray, "shape", None),
            i,
        )

        # Sanity check (warn only; don't change behavior)
        expected = int(specnum)
        if i != expected:
            logger.warning(
                "Unexpected spectrum count while building intensarray: filled=%d expected=%d",
                i,
                expected,
            )

    def _get_xmap(self):
        """Retrieve the x-axis mapping data.

        Returns:
        ndarray: Array of x-axis values.
        """
        logger.debug("Returning xmap (shape=%s).", getattr(self.xmap, "shape", None))
        return self.xmap

    def _get_ymap(self):
        """Retrieve the y-axis mapping data.

        Returns:
        ndarray: Array of y-axis values.
        """
        logger.debug("Returning ymap (shape=%s).", getattr(self.ymap, "shape", None))
        return self.ymap

    def _get_spec(self):
        """Retrieve the spectral data.

        Returns:
        ndarray: Array of spectral values.
        """
        logger.debug("Returning spec (shape=%s).", getattr(self.spec, "shape", None))
        return self.spec

    def _get_intensarray(self):
        """Retrieve the intensity array data.

        Returns:
        ndarray: 2D array of intensity values.
        """
        logger.debug("Returning intensarray (shape=%s).", getattr(self.intensarray, "shape", None))
        return self.intensarray
