"""Data loading, caching, and Raman spectrum fitting.

Defines :class:`~ramangui.data.DataObject`, which loads Raman mapping data (from cache or raw
import), performs peak fitting (G, D, 2D and optional 4-peak mode), and exposes fitted results
and derived quantities such as mask, doping, and strain.
"""

import logging
import multiprocessing

import numpy as np
import PyQt6 as PyQt
import scipy.optimize as opt

from ramangui import data_import, utils

logger = logging.getLogger(__name__)


class DataObject:
    """Load Raman map data, cache intermediate arrays, and perform peak fitting.

    The object tries to load cached arrays/results from disk first. If that fails, it imports raw
    data and performs an initial fit.

    Attributes:
        filename: Base filename used for loading/saving cached arrays and fit results.
        settings: Mapping-like configuration controlling peak regions, starting values, and modes.
        pyqt: Parent Qt widget used for progress dialogs.
        fitresult: Dictionary containing fitted parameter maps and derived quantities.
        mask: Fit validity mask.
        xmap: X coordinate map.
        ymap: Y coordinate map.
        spec: X-axis (Raman shift axis) for spectra.
        intensarray: 2D array of spectra for the map.
    """

    def __init__(self, filename, settings, pyqt):
        """Initialize a DataObject from cached results or raw import.

        Attempts to load cached arrays/results from disk using ``filename`` as a base path.
        If loading fails, imports raw data and runs an initial fit.

        Args:
            filename: Base filename used for caching (without extension).
            settings: Settings object/dict controlling import and fitting behavior.
            pyqt: Parent Qt widget for progress dialogs.
        """
        self.settings = settings
        self.filename = filename
        self.pyqt = pyqt

        logger.debug("Initializing DataObject (filename=%s)...", filename)

        try:
            logger.info("Loading cached fit/raw arrays from disk...")
            self.fitresult = np.load(
                filename + ".fit.npy", encoding="bytes", allow_pickle=True
            ).item()
            self.xmap = np.load(filename + ".xmap.npy", encoding="bytes", allow_pickle=True)
            self.ymap = np.load(filename + ".ymap.npy", encoding="bytes", allow_pickle=True)
            # self.intens = np.load(filename+'.intens.npy',encoding='bytes',allow_pickle=True)
            self.spec = np.load(filename + ".spec.npy", encoding="bytes", allow_pickle=True)
            self.intensarray = np.load(
                filename + ".intensarray.npy", encoding="bytes", allow_pickle=True
            )

            self.mask = self.fitresult["mask"]

            # Apply mask if selected
            if self.settings.get("UseFitMask") == 1:  # Use Mask
                logger.info("Applying fit mask to cached results (UseFitMask=1).")
                keys = list(self.fitresult)
                for key in keys:
                    if (
                        "area" in key
                        or "gamma" in key
                        or "omega" in key
                        or "offset" in key
                        or "doping" in key
                        or "strain" in key
                    ):
                        self.fitresult[key] = np.multiply(self.mask, self.fitresult[key])
            else:
                logger.debug("UseFitMask disabled; leaving cached results unchanged.")

            logger.info("Saved data loaded successfully.")
        except Exception:
            logger.info(
                "No saved fit data found or failed to load; falling back to raw import.",
                exc_info=False,
            )
            self.load_from_file(filename)
            logger.info("Raw data loaded; starting initial fit.")
            self.perform_fit()

    def load_from_file(self, filename):
        """Import raw data from disk and save arrays for caching.

        Uses the configured importer to load x/y maps and spectral arrays, then writes them to
        ``.npy`` files so future runs can load from cache.

        Args:
            filename: Base filename to import from (typically the same as ``self.filename``).
        """
        logger.info("Importing raw data from file: %s", filename)
        importer = data_import.Witec_Matlab(self.filename)
        import_result = importer.get_data()
        self.xmap = import_result["xmap"]
        self.ymap = import_result["ymap"]
        self.spec = import_result["spec"]
        self.intensarray = import_result["intensarray"]

        logger.debug(
            "Raw import complete: xmap=%s ymap=%s spec=%s intensarray=%s",
            getattr(self.xmap, "shape", None),
            getattr(self.ymap, "shape", None),
            getattr(self.spec, "shape", None),
            getattr(self.intensarray, "shape", None),
        )

        try:
            np.save(self.filename + ".xmap", self.xmap)
            np.save(self.filename + ".ymap", self.ymap)
            # np.save(self.filename+'.intens',self.intens)
            np.save(self.filename + ".spec", self.spec)
            np.save(self.filename + ".intensarray", self.intensarray)
            logger.info("Raw import arrays saved to disk for caching.")
        except Exception:
            logger.exception("Failed to save imported raw arrays to disk.")

    def fit_map(self, xaxis, intensspectrum_array):
        """Fit Raman peaks for each spectrum in a map and derive parameter maps.

        Fits Lorentzian models to G, D, and 2D peaks across a 2D map of spectra. Optionally fits a
        4-peak model for the 2D band (``4_P_mode``). Produces parameter maps, uncertainties,
        validity mask, fitted intensity arrays, and derived doping/strain maps.

        Args:
            xaxis: 1D Raman shift axis corresponding to each spectrum.
            intensspectrum_array: 2D array (map) where each entry is a 1D spectrum.

        Returns:
            A dictionary of fit results including parameter maps, errors, mask, derived quantities,
            and fitted intensity arrays.
        """
        settings = self.settings
        num_cores = multiprocessing.cpu_count()
        logger.info(
            "Starting fit_map: spectra_shape=%s, cpu_count=%d",
            getattr(intensspectrum_array, "shape", None),
            num_cores,
        )

        # Starting values and region for the G peak
        omega_g_0 = settings.get("omega_G_0")
        spec_width_g = settings.get("spec_width_G")
        omega_g_min = omega_g_0 - spec_width_g
        omega_g_max = omega_g_0 + spec_width_g
        Gamma_g_0 = settings.get("Gamma_G_0")

        # Starting values and region for the 2D peak
        omega_2d_0 = settings.get("omega_2D_0")
        spec_width_2d = settings.get("spec_width_2D")
        omega_2d_min = omega_2d_0 - spec_width_2d
        omega_2d_max = omega_2d_0 + spec_width_2d
        Gamma_2d_0 = settings.get("Gamma_2D_0")

        # Starting values and region for the D peak
        omega_d_0 = settings.get("omega_D_0")
        spec_width_d = settings.get("spec_width_D")
        omega_d_min = omega_d_0 - spec_width_d
        omega_d_max = omega_d_0 + spec_width_d
        Gamma_d_0 = settings.get("Gamma_D_0")

        logger.debug(
            "Fit windows: G=[%s,%s], D=[%s,%s], 2D=[%s,%s] (cm^-1); 4_P_mode=%s",
            omega_g_min,
            omega_g_max,
            omega_d_min,
            omega_d_max,
            omega_2d_min,
            omega_2d_max,
            bool(settings.get("4_P_mode")),
        )

        # Starting values and region for the 4-P bilayer graphene 2D peaks
        bilayer4P_PeakPositions = np.array(
            [
                settings.get("omega_peak_1"),
                settings.get("omega_peak_2"),
                settings.get("omega_peak_3"),
                settings.get("omega_peak_4"),
            ]
        )
        bilayer4P_PeakWidths = np.array(
            [
                settings.get("Gamma_peak_1"),
                settings.get("Gamma_peak_2"),
                settings.get("Gamma_peak_3"),
                settings.get("Gamma_peak_4"),
            ]
        )

        def model_4P(p, x):
            """Evaluate the 4-peak Lorentzian model plus offset."""
            return (
                p[0]
                + (p[1] / np.pi) * (p[2] / 2) / ((p[2] / 2) ** 2 + (x - p[3]) ** 2)
                + (p[4] / np.pi) * (p[5] / 2) / ((p[5] / 2) ** 2 + (x - p[6]) ** 2)
                + (p[7] / np.pi) * (p[8] / 2) / ((p[8] / 2) ** 2 + (x - p[9]) ** 2)
                + (p[10] / np.pi) * (p[11] / 2) / ((p[11] / 2) ** 2 + (x - p[12]) ** 2)
            )

        def residues_4P(p, x, y):
            """Residual function for 4-peak fitting with penalty for negative parameters."""
            w = True
            for par in p:
                if par < 0:
                    w = False
            if w:
                return y - model_4P(p, x)
            return (y - model_4P(p, x)) * 10**9

        def lorentz_2d(p, x):
            """Lorentzian model for 2D peak (single peak) with offset."""
            return (p[0] / np.pi) * (p[1] / 2) / ((p[1] / 2) ** 2 + (x - p[2]) ** 2) + p[3]

        def lorentz_G(p, x):
            """Lorentzian model for G peak with offset."""
            return (p[0] / np.pi) * (p[1] / 2) / ((p[1] / 2) ** 2 + (x - p[2]) ** 2) + p[3]

        def lorentz_D(p, x):
            """Lorentzian model for D peak with offset."""
            return (p[0] / np.pi) * (p[1] / 2) / ((p[1] / 2) ** 2 + (x - p[2]) ** 2) + p[3]

        def res_2d(p, x, y):
            """Residuals for 2D peak least-squares fitting."""
            return y - lorentz_2d(p, x)

        def res_G(p, x, y):
            """Residuals for G peak least-squares fitting."""
            return y - lorentz_G(p, x)

        def res_D(p, x, y):
            """Residuals for D peak least-squares fitting."""
            return y - lorentz_D(p, x)

        xaxis_min = np.min(xaxis)
        xaxis_max = np.max(xaxis)

        # Fit function to fit every spectrum...
        def fit_spec(spec):
            """Fit peaks for a single spectrum.

            Args:
                spec: 1D intensity array for one spectrum.

            Returns:
                Tuple of fitted parameters/errors for G, D, 2D and optionally 4P plus reduced chi^2.
            """
            # Fit G Peak
            if (omega_g_min >= xaxis_min) & (omega_g_max <= xaxis_max):
                xxg, yyg = utils.subset(xaxis, spec, omega_g_min, omega_g_max)
                x0_G = xxg[np.argmax(yyg)]
                y0_G = (yyg[0] + yyg[-1]) / 2
                intensmax_G = np.max(yyg)
                startvalues_G = np.array(
                    [(intensmax_G - y0_G) * Gamma_g_0 * np.pi / 2, Gamma_g_0, x0_G, y0_G]
                )
                fit_results_G, cov_G, info, errmsg, ierr = opt.leastsq(
                    res_G, startvalues_G, args=(xxg, yyg), full_output=True
                )
                try:
                    fit_errors_G = np.array(
                        [np.sqrt(cov_G[i, i]) for i in range(0, len(startvalues_G))]
                    )
                except Exception:
                    fit_errors_G = np.array([np.nan for i in range(0, len(startvalues_G))])
            else:
                fit_results_G = np.array([0.0 for i in range(0, 4)])
                fit_errors_G = np.array([np.nan for i in range(0, 4)])

            # Fit D Peak
            if (omega_d_min >= xaxis_min) & (omega_d_max <= xaxis_max):
                xxd, yyd = utils.subset(xaxis, spec, omega_d_min, omega_d_max)
                x0_D = xxd[np.argmax(yyd)]
                y0_D = (yyd[0] + yyd[-1]) / 2
                intensmax_D = np.max(yyd)
                startvalues_D = np.array(
                    [(intensmax_D - y0_D) * Gamma_d_0 * np.pi / 2, Gamma_d_0, x0_D, y0_D]
                )
                fit_results_D, cov_D, info, errmsg, ierr = opt.leastsq(
                    res_D, startvalues_D, args=(xxd, yyd), full_output=True
                )
                try:
                    fit_errors_D = np.array(
                        [np.sqrt(cov_D[i, i]) for i in range(0, len(startvalues_D))]
                    )
                except Exception:
                    fit_errors_D = np.array([np.nan for i in range(0, len(startvalues_D))])
            else:
                fit_results_D = np.array([0.0 for i in range(0, 4)])
                fit_errors_D = np.array([np.nan for i in range(0, 4)])

            # Fit 2D Peak
            if (omega_2d_min >= xaxis_min) & (omega_2d_max <= xaxis_max):
                xx2d, yy2d = utils.subset(xaxis, spec, omega_2d_min, omega_2d_max)
                x0_2D = xx2d[np.argmax(yy2d)]
                y0_2D = (yy2d[0] + yy2d[-1]) / 2
                intensmax_2D = np.max(yy2d)
                startvalues_2D = np.array(
                    [(intensmax_2D - y0_2D) * Gamma_2d_0 * np.pi / 2, Gamma_2d_0, x0_2D, y0_2D]
                )
                fit_results_2D, cov_2D, info, errmsg, ierr = opt.leastsq(
                    res_2d, startvalues_2D, args=(xx2d, yy2d), full_output=True
                )
                try:
                    fit_errors_2D = np.array(
                        [np.sqrt(cov_2D[i, i]) for i in range(0, len(startvalues_2D))]
                    )
                except Exception:
                    fit_errors_2D = np.array([np.nan for i in range(0, len(startvalues_2D))])

                # Bilayer/4-P case:
                if settings.get("4_P_mode"):
                    xx_4p, yy_4p = utils.subset(xaxis, spec, omega_2d_min, omega_2d_max)
                    # start values
                    p_start = np.array([yy_4p.min()])  # offset
                    for i in range(0, len(bilayer4P_PeakPositions)):
                        p_start = np.append(
                            p_start, [(intensmax_2D - y0_2D) * bilayer4P_PeakWidths[i] * np.pi]
                        )  # area
                        p_start = np.append(p_start, [bilayer4P_PeakWidths[i]])  # width
                        p_start = np.append(p_start, [bilayer4P_PeakPositions[i]])  # position
                    fit_4p, cov_4p, info, errmsg, ierr = opt.leastsq(
                        residues_4P, p_start, args=(xx_4p, yy_4p), full_output=True
                    )
                    try:
                        fit_errors_4p = np.array(
                            [np.sqrt(cov_4p[i, i]) for i in range(0, len(p_start))]
                        )
                    except Exception:
                        fit_errors_4p = np.array([np.nan for i in range(len(p_start))])
                    if info is not None and "fvec" in info:
                        residuals = info["fvec"]
                        chi_squared = np.sum(residuals**2)
                        dof = len(yy_4p) - len(
                            p_start
                        )  # number of data points - number of parameters
                        if dof > 0:
                            chi2_dof_4p = chi_squared / dof
                        else:
                            chi2_dof_4p = np.nan
                    else:
                        chi2_dof_4p = np.nan
                else:
                    fit_4p = np.zeros(13)
                    fit_errors_4p = np.zeros(13)
                    chi2_dof_4p = np.nan
            else:
                fit_results_2D = np.array([0.0 for i in range(0, 4)])
                fit_errors_2D = np.array([np.nan for i in range(0, 4)])
                fit_4p = np.zeros(13)
                fit_errors_4p = np.zeros(13)
                chi2_dof_4p = np.nan

            return (
                fit_results_G,
                fit_results_D,
                fit_results_2D,
                fit_errors_G,
                fit_errors_D,
                fit_errors_2D,
                fit_4p,
                fit_errors_4p,
                chi2_dof_4p,
            )

        # Fit each spectrum in the array
        area_G = np.empty(intensspectrum_array.shape, dtype=float)
        offset_G = np.empty(intensspectrum_array.shape, dtype=float)
        omega_G = np.empty(intensspectrum_array.shape, dtype=float)
        omega_G_doping = np.empty(intensspectrum_array.shape, dtype=float)
        Gamma_G = np.empty(intensspectrum_array.shape, dtype=float)
        area_G_error = np.empty(intensspectrum_array.shape, dtype=float)
        offset_G_error = np.empty(intensspectrum_array.shape, dtype=float)
        omega_G_error = np.empty(intensspectrum_array.shape, dtype=float)
        Gamma_G_error = np.empty(intensspectrum_array.shape, dtype=float)

        area_D = np.empty(intensspectrum_array.shape, dtype=float)
        offset_D = np.empty(intensspectrum_array.shape, dtype=float)
        omega_D = np.empty(intensspectrum_array.shape, dtype=float)
        Gamma_D = np.empty(intensspectrum_array.shape, dtype=float)
        area_D_error = np.empty(intensspectrum_array.shape, dtype=float)
        offset_D_error = np.empty(intensspectrum_array.shape, dtype=float)
        omega_D_error = np.empty(intensspectrum_array.shape, dtype=float)
        Gamma_D_error = np.empty(intensspectrum_array.shape, dtype=float)

        area_2D = np.empty(intensspectrum_array.shape, dtype=float)
        offset_2D = np.empty(intensspectrum_array.shape, dtype=float)
        omega_2D = np.empty(intensspectrum_array.shape, dtype=float)
        Gamma_2D = np.empty(intensspectrum_array.shape, dtype=float)
        area_2D_error = np.empty(intensspectrum_array.shape, dtype=float)
        offset_2D_error = np.empty(intensspectrum_array.shape, dtype=float)
        omega_2D_error = np.empty(intensspectrum_array.shape, dtype=float)
        Gamma_2D_error = np.empty(intensspectrum_array.shape, dtype=float)

        # 4 Peak case
        area1_4p = np.empty(intensspectrum_array.shape, dtype=float)
        area2_4p = np.empty(intensspectrum_array.shape, dtype=float)
        area3_4p = np.empty(intensspectrum_array.shape, dtype=float)
        area4_4p = np.empty(intensspectrum_array.shape, dtype=float)
        omega1_4p = np.empty(intensspectrum_array.shape, dtype=float)
        omega2_4p = np.empty(intensspectrum_array.shape, dtype=float)
        omega3_4p = np.empty(intensspectrum_array.shape, dtype=float)
        omega4_4p = np.empty(intensspectrum_array.shape, dtype=float)
        gamma1_4p = np.empty(intensspectrum_array.shape, dtype=float)
        gamma2_4p = np.empty(intensspectrum_array.shape, dtype=float)
        gamma3_4p = np.empty(intensspectrum_array.shape, dtype=float)
        gamma4_4p = np.empty(intensspectrum_array.shape, dtype=float)
        offset_4p = np.empty(intensspectrum_array.shape, dtype=float)
        area1_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        area2_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        area3_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        area4_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        omega1_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        omega2_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        omega3_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        omega4_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        gamma1_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        gamma2_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        gamma3_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        gamma4_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        offset_4p_error = np.empty(intensspectrum_array.shape, dtype=float)
        chi_2_4p = np.empty(intensspectrum_array.shape, dtype=float)

        Mask = np.empty(intensspectrum_array.shape, dtype=float)

        doping = np.empty(intensspectrum_array.shape, dtype=float)
        strain = np.empty(intensspectrum_array.shape, dtype=float)

        # doping and strain for 4-peak mode
        doping_1 = np.empty(intensspectrum_array.shape, dtype=float)
        strain_1 = np.empty(intensspectrum_array.shape, dtype=float)
        doping_2 = np.empty(intensspectrum_array.shape, dtype=float)
        strain_2 = np.empty(intensspectrum_array.shape, dtype=float)
        doping_3 = np.empty(intensspectrum_array.shape, dtype=float)
        strain_3 = np.empty(intensspectrum_array.shape, dtype=float)
        doping_4 = np.empty(intensspectrum_array.shape, dtype=float)
        strain_4 = np.empty(intensspectrum_array.shape, dtype=float)

        # Call the fit function for every spectrum + filter the results (Mask)
        self.progress = PyQt.QtWidgets.QProgressDialog(
            "Fitting Raman Spectra...", "Cancel", 0, intensspectrum_array.shape[0], self.pyqt
        )
        self.progress.setWindowTitle("Please wait...")
        self.progress.setModal(True)
        self.progress.show()

        q = 1.602e-19  # e in C
        hb = 1.055e-34  # h_bar in Js
        hbeV = hb / q  # h_bar in eVs
        vF = 1.15e6  # vF in m/s
        alpha = np.arctan(0.4)
        beta = np.arctan(2.2)
        if settings.get("StrainType") == "uniaxial":  # uniaxial strain
            denom = 23.5
        else:  # biaxial strain
            denom = 69.1

        logger.info("Fitting spectra loop started.")
        for x in range(0, intensspectrum_array.shape[0]):
            for y in range(0, intensspectrum_array.shape[1]):
                temp = fit_spec(intensspectrum_array[x, y])
                area_G[x, y], Gamma_G[x, y], omega_G[x, y], offset_G[x, y] = temp[0]
                (
                    area_G_error[x, y],
                    Gamma_G_error[x, y],
                    omega_G_error[x, y],
                    offset_G_error[x, y],
                ) = temp[3]
                area_D[x, y], Gamma_D[x, y], omega_D[x, y], offset_D[x, y] = temp[1]
                (
                    area_D_error[x, y],
                    Gamma_D_error[x, y],
                    omega_D_error[x, y],
                    offset_D_error[x, y],
                ) = temp[4]
                area_2D[x, y], Gamma_2D[x, y], omega_2D[x, y], offset_2D[x, y] = temp[2]
                (
                    area_2D_error[x, y],
                    Gamma_2D_error[x, y],
                    omega_2D_error[x, y],
                    offset_2D_error[x, y],
                ) = temp[5]

                if settings.get("4_P_mode"):
                    (
                        offset_4p[x, y],
                        area1_4p[x, y],
                        gamma1_4p[x, y],
                        omega1_4p[x, y],
                        area2_4p[x, y],
                        gamma2_4p[x, y],
                        omega2_4p[x, y],
                        area3_4p[x, y],
                        gamma3_4p[x, y],
                        omega3_4p[x, y],
                        area4_4p[x, y],
                        gamma4_4p[x, y],
                        omega4_4p[x, y],
                    ) = temp[6]
                    (
                        offset_4p_error[x, y],
                        area1_4p_error[x, y],
                        gamma1_4p_error[x, y],
                        omega1_4p_error[x, y],
                        area2_4p_error[x, y],
                        gamma2_4p_error[x, y],
                        omega2_4p_error[x, y],
                        area3_4p_error[x, y],
                        gamma3_4p_error[x, y],
                        omega3_4p_error[x, y],
                        area4_4p_error[x, y],
                        gamma4_4p_error[x, y],
                        omega4_4p_error[x, y],
                    ) = temp[7]
                    chi_2_4p[x, y] = temp[8]

                # Is fit in bounds?
                bool_2D = (
                    (omega_2D_error[x, y] < float(settings.get("omega_2D_maxError")))
                    and (area_2D[x, y] > float(settings.get("area_2D_min")))
                    and (area_2D[x, y] < float(settings.get("area_2D_max")))
                    and (Gamma_2D[x, y] > float(settings.get("Gamma_2D_min")))
                    and (Gamma_2D[x, y] < float(settings.get("Gamma_2D_max")))
                )
                bool_G = (Gamma_G[x, y] > float(settings.get("Gamma_G_min"))) and (
                    Gamma_G[x, y] < float(settings.get("Gamma_G_max"))
                )
                if bool_2D and bool_G:
                    Mask[x, y] = 1
                    try:
                        omega_G_doping[x, y] = (
                            np.cos(alpha)
                            / np.sin(beta - alpha)
                            * (
                                np.sin(beta) * (omega_G[x, y] - 1581.6)
                                - np.cos(beta) * (omega_2D[x, y] - 2678.6)
                            )
                        )
                        doping[x, y] = (
                            1e-12
                            * 1
                            / np.pi
                            * ((omega_G_doping[x, y]) / (42 * hbeV * vF * 100)) ** 2
                        )  # doping in 1e12 cm^-2
                        strain[x, y] = -(
                            np.cos(beta)
                            / np.sin(beta - alpha)
                            * (
                                -np.sin(alpha) * (omega_G[x, y] - 1581.6)
                                + np.cos(alpha) * (omega_2D[x, y] - 2678.6)
                            )
                            / denom
                        )  # strain in %
                    except Exception:
                        logger.debug(
                            "Doping/strain calculation failed at (x=%d,y=%d).", x, y, exc_info=True
                        )
                        doping[x, y] = np.nan
                        strain[x, y] = np.nan

                    if settings.get("4_P_mode"):
                        try:
                            omega_G_dop1 = (
                                np.cos(alpha)
                                / np.sin(beta - alpha)
                                * (
                                    np.sin(beta) * (omega_G[x, y] - 1581.6)
                                    - np.cos(beta) * (omega1_4p[x, y] - 2678.6)
                                )
                            )
                            doping_1[x, y] = (
                                1e-12 * 1 / np.pi * ((omega_G_dop1) / (42 * hbeV * vF * 100)) ** 2
                            )
                            strain_1[x, y] = -(
                                np.cos(beta)
                                / np.sin(beta - alpha)
                                * (
                                    -np.sin(alpha) * (omega_G[x, y] - 1581.6)
                                    + np.cos(alpha) * (omega1_4p[x, y] - 2678.6)
                                )
                                / denom
                            )

                            omega_G_dop2 = (
                                np.cos(alpha)
                                / np.sin(beta - alpha)
                                * (
                                    np.sin(beta) * (omega_G[x, y] - 1581.6)
                                    - np.cos(beta) * (omega2_4p[x, y] - 2678.6)
                                )
                            )
                            doping_2[x, y] = (
                                1e-12 * 1 / np.pi * ((omega_G_dop2) / (42 * hbeV * vF * 100)) ** 2
                            )
                            strain_2[x, y] = -(
                                np.cos(beta)
                                / np.sin(beta - alpha)
                                * (
                                    -np.sin(alpha) * (omega_G[x, y] - 1581.6)
                                    + np.cos(alpha) * (omega2_4p[x, y] - 2678.6)
                                )
                                / denom
                            )

                            omega_G_dop3 = (
                                np.cos(alpha)
                                / np.sin(beta - alpha)
                                * (
                                    np.sin(beta) * (omega_G[x, y] - 1581.6)
                                    - np.cos(beta) * (omega3_4p[x, y] - 2678.6)
                                )
                            )
                            doping_3[x, y] = (
                                1e-12 * 1 / np.pi * ((omega_G_dop3) / (42 * hbeV * vF * 100)) ** 2
                            )
                            strain_3[x, y] = -(
                                np.cos(beta)
                                / np.sin(beta - alpha)
                                * (
                                    -np.sin(alpha) * (omega_G[x, y] - 1581.6)
                                    + np.cos(alpha) * (omega3_4p[x, y] - 2678.6)
                                )
                                / denom
                            )

                            omega_G_dop4 = (
                                np.cos(alpha)
                                / np.sin(beta - alpha)
                                * (
                                    np.sin(beta) * (omega_G[x, y] - 1581.6)
                                    - np.cos(beta) * (omega4_4p[x, y] - 2678.6)
                                )
                            )
                            doping_4[x, y] = (
                                1e-12 * 1 / np.pi * ((omega_G_dop4) / (42 * hbeV * vF * 100)) ** 2
                            )
                            strain_4[x, y] = -(
                                np.cos(beta)
                                / np.sin(beta - alpha)
                                * (
                                    -np.sin(alpha) * (omega_G[x, y] - 1581.6)
                                    + np.cos(alpha) * (omega4_4p[x, y] - 2678.6)
                                )
                                / denom
                            )
                        except Exception:
                            logger.debug(
                                "4P doping/strain calculation failed at (x=%d,y=%d).",
                                x,
                                y,
                                exc_info=True,
                            )
                            doping_1[x, y] = np.nan
                            strain_1[x, y] = np.nan
                            doping_2[x, y] = np.nan
                            strain_2[x, y] = np.nan
                            doping_3[x, y] = np.nan
                            strain_3[x, y] = np.nan
                            doping_4[x, y] = np.nan
                            strain_4[x, y] = np.nan

                elif bool_2D:
                    Mask[x, y] = 1
                    doping[x, y] = np.nan
                    strain[x, y] = np.nan
                else:
                    Mask[x, y] = np.nan
                    doping[x, y] = np.nan
                    strain[x, y] = np.nan

            self.progress.setValue(x + 1)
            if self.progress.wasCanceled():
                logger.warning("Fit cancelled by user at x=%d.", x)
                break

        # Applying mask
        self.progress = PyQt.QtWidgets.QProgressDialog(
            "Creating Mask...", "Cancel", 0, intensspectrum_array.shape[0], self.pyqt
        )
        self.progress.setWindowTitle("Please wait...")
        self.progress.setModal(True)
        self.progress.show()

        logger.info("Creating fitted intensity arrays (fit_intens) ...")
        fit_intens = np.empty(intensspectrum_array.shape, dtype=list)
        for x in range(0, intensspectrum_array.shape[0]):
            for y in range(0, intensspectrum_array.shape[1]):
                yy = np.empty(len(xaxis), dtype=float)
                for i in range(0, len(xaxis)):
                    if xaxis[i] > omega_g_min and xaxis[i] < omega_g_max:
                        yy[i] = lorentz_G(
                            np.array([area_G[x, y], Gamma_G[x, y], omega_G[x, y], offset_G[x, y]]),
                            xaxis[i],
                        )
                    elif xaxis[i] > omega_d_min and xaxis[i] < omega_d_max:
                        yy[i] = lorentz_D(
                            np.array([area_D[x, y], Gamma_D[x, y], omega_D[x, y], offset_D[x, y]]),
                            xaxis[i],
                        )
                    elif (
                        xaxis[i] > omega_2d_min
                        and xaxis[i] < omega_2d_max
                        and not settings.get("4_P_mode")
                    ):
                        yy[i] = lorentz_2d(
                            np.array(
                                [area_2D[x, y], Gamma_2D[x, y], omega_2D[x, y], offset_2D[x, y]]
                            ),
                            xaxis[i],
                        )
                    elif (
                        xaxis[i] > omega_2d_min
                        and xaxis[i] < omega_2d_max
                        and settings.get("4_P_mode")
                    ):  # 4Peak
                        yy[i] = model_4P(
                            np.array(
                                [
                                    offset_4p[x, y],
                                    area1_4p[x, y],
                                    gamma1_4p[x, y],
                                    omega1_4p[x, y],
                                    area2_4p[x, y],
                                    gamma2_4p[x, y],
                                    omega2_4p[x, y],
                                    area3_4p[x, y],
                                    gamma3_4p[x, y],
                                    omega3_4p[x, y],
                                    area4_4p[x, y],
                                    gamma4_4p[x, y],
                                    omega4_4p[x, y],
                                ]
                            ),
                            xaxis[i],
                        )
                    else:
                        yy[i] = np.nan
                if settings.get("UseFitMask") == 1:  # Use Mask
                    yy = yy * Mask[x, y]
                fit_intens[x, y] = yy
            self.progress.setValue(x + 1)
            if self.progress.wasCanceled():
                logger.warning("Mask creation cancelled by user at x=%d.", x)
                break

        # Create results dictionary
        result = {}
        result["mask"] = Mask
        result["area_g"] = area_G
        result["gamma_g"] = Gamma_G
        result["omega_g"] = omega_G
        result["offset_g"] = offset_G
        result["area_d"] = area_D
        result["gamma_d"] = Gamma_D
        result["omega_d"] = omega_D
        result["offset_d"] = offset_D
        result["area_2d"] = area_2D
        result["gamma_2d"] = Gamma_2D
        result["omega_2d"] = omega_2D
        result["offset_2d"] = offset_2D
        result["area_g_error"] = area_G_error
        result["gamma_g_error"] = Gamma_G_error
        result["omega_g_error"] = omega_G_error
        result["offset_g_error"] = offset_G_error
        result["area_d_error"] = area_D_error
        result["gamma_d_error"] = Gamma_D_error
        result["omega_d_error"] = omega_D_error
        result["offset_d_error"] = offset_D_error
        result["area_2d_error"] = area_2D_error
        result["gamma_2d_error"] = Gamma_2D_error
        result["omega_2d_error"] = omega_2D_error
        result["offset_2d_error"] = offset_2D_error

        result["area_2d_1"] = area1_4p
        result["gamma_2d_1"] = gamma1_4p
        result["omega_2d_1"] = omega1_4p
        result["area_2d_2"] = area2_4p
        result["gamma_2d_2"] = gamma2_4p
        result["omega_2d_2"] = omega2_4p
        result["area_2d_3"] = area3_4p
        result["gamma_2d_3"] = gamma3_4p
        result["omega_2d_3"] = omega3_4p
        result["area_2d_4"] = area4_4p
        result["gamma_2d_4"] = gamma4_4p
        result["omega_2d_4"] = omega4_4p
        result["area_2d_1_error"] = area1_4p_error
        result["gamma_2d_1_error"] = gamma1_4p_error
        result["omega_2d_1_error"] = omega1_4p_error
        result["area_2d_2_error"] = area2_4p_error
        result["gamma_2d_2_error"] = gamma2_4p_error
        result["omega_2d_2_error"] = omega2_4p_error
        result["area_2d_3_error"] = area3_4p_error
        result["gamma_2d_3_error"] = gamma3_4p_error
        result["omega_2d_3_error"] = omega3_4p_error
        result["area_2d_4_error"] = area4_4p_error
        result["gamma_2d_4_error"] = gamma4_4p_error
        result["omega_2d_4_error"] = omega4_4p_error
        result["offset_2d_4p_error"] = offset_4p_error
        result["chi_2_4p"] = chi_2_4p

        result["doping"] = doping
        result["strain"] = strain

        result["doping_1"] = doping_1
        result["strain_1"] = strain_1
        result["doping_2"] = doping_2
        result["strain_2"] = strain_2
        result["doping_3"] = doping_3
        result["strain_3"] = strain_3
        result["doping_4"] = doping_4
        result["strain_4"] = strain_4

        result["fit_intens"] = fit_intens
        result["xaxis"] = xaxis
        result["intensspectrum_array"] = intensspectrum_array

        logger.info("fit_map completed.")
        return result

    def perform_fit(self):
        """Run peak fitting for the currently loaded dataset and cache the results.

        Updates ``self.fitresult`` and ``self.mask``. Optionally applies the fit mask to selected
        parameter maps based on settings.
        """
        logger.info("Performing fit for current dataset...")
        self.fitresult = self.fit_map(self.spec, self.intensarray)
        try:
            np.save(self.filename + ".fit", self.fitresult)
            logger.info("Fit results saved: %s", self.filename + ".fit.npy")
        except Exception:
            logger.exception("Failed to save fit results to disk.")

        self.mask = self.fitresult["mask"]
        # Apply mask if selected
        if self.settings.get("UseFitMask") == 1:  # Use Mask
            logger.info("Applying fit mask to new results (UseFitMask=1).")
            keys = list(self.fitresult)
            for key in keys:
                if (
                    "area" in key
                    or "gamma" in key
                    or "omega" in key
                    or "offset" in key
                    or "doping" in key
                    or "strain" in key
                ):
                    self.fitresult[key] = np.multiply(self.mask, self.fitresult[key])
        else:
            logger.debug("UseFitMask disabled; leaving results unchanged.")

    def update_Settings(self, settings):
        """Update the settings used for fitting and masking.

        Args:
            settings: New settings mapping/object.
        """
        self.settings = settings

    def get_mask(self):
        """Return the fit validity mask."""
        return self.mask

    def get_xaxis(self):
        """Return the Raman shift axis (x-axis) for spectra."""
        return self.spec

    def get_fit_intens(self):
        """Return the fitted intensity array stored in the fit results."""
        return self.fitresult["fit_intens"]

    def get_intens(self):
        """Return the raw intensity spectra array."""
        return self.intensarray

    def get_fitresults(self):
        """Return the full fit results dictionary."""
        return self.fitresult

    def get_xmap(self):
        """Return the x coordinate map."""
        return self.xmap

    def get_ymap(self):
        """Return the y coordinate map."""
        return self.ymap

    def get_width(self):
        """Return the image/map width, if available."""
        return self.imagewidth

    def get_height(self):
        """Return the image/map height, if available."""
        return self.imageheight
