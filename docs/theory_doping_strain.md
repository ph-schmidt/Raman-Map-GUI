# Extraction of Charge Carrier Density and Strain

The positions of the **G** and **2D** Raman modes are influenced simultaneously by strain, doping and screening, which makes a direct interpretation ambiguous.

Screening in principle also influences only the 2D mode, and for undoped graphene, depends on the dielectric environment [6].

Here, we consider only the case of graphene encapsulated in hBN, i.e. no screening contribution and consider only strain and doping.

This ambiguity in strain and doping can be resolved by exploiting the fact that strain and doping shift the Raman peaks along different directions in the $(\omega_G,\omega_{2D})$ plane, and by knowing the reference peak positions for pristine, unstrained and undoped graphene.

---

## Raman Shift Decomposition

Strain and doping induce approximately linear but distinct Raman shifts in the  
$(\omega_G,\omega_{2D})$ space.  
These directions are characterized by two experimentally determined angles, extracted for graphene on $\mathrm{SiO_2}$ [1]:

```math
\alpha = \arctan(0.7), \qquad
\beta = \arctan(2.2).
```

Here, $\alpha$ corresponds to the doping axis and $\beta$ to the strain axis.

For graphene encapsulated in hBN, the orientation of the doping axis differs from that on $\mathrm{SiO_2}$ [7], reflecting the sensitivity of doping-induced Raman shifts to the surrounding dielectric environment. In this case, the doping axis is characterized by

```math
\alpha = \arctan(0.4),
```

which is used in this software package.

*Note that the slopes of the doping and strain axes can be adjusted in the program’s fit settings.*

The reference Raman frequencies for pristine, unstrained graphene (graphene encapsulated in hBN) are [2]

```math
\omega_G^0 = 1581.6~\mathrm{cm^{-1}}, \qquad
\omega_{2D}^0 = 2678.6~\mathrm{cm^{-1}}.
```

Measured Raman shifts are defined relative to these reference values as

```math
\Delta \omega_G = \omega_G - \omega_G^0, \qquad
\Delta \omega_{2D} = \omega_{2D} - \omega_{2D}^0.
```

---

## Charge Carrier Density

To isolate the contribution arising purely from charge doping, the measured Raman shifts are projected onto the doping axis.  
This yields the doping-induced G-mode shift

```math
\Delta \omega_G^{\mathrm{dop}}=\frac{\cos(\alpha)}{\sin(\beta-\alpha)}
\left[\sin(\beta)\,\Delta \omega_G-\cos(\beta)\,\Delta \omega_{2D}\right].
```

Near the Dirac point, graphene exhibits a linear electronic dispersion, leading to the relation

```math
E_F = \hbar v_F \sqrt{\pi n},
```

where $E_F$ is the Fermi energy, $\hbar$ the reduced Planck constant, and $v_F$ the
Fermi velocity.

Electrostatic gating experiments show that the doping-induced shift of the G mode is proportional to the Fermi energy [3]:

```math
\Delta \omega_G^{\mathrm{dop}}
\approx
42~\mathrm{cm^{-1}\,eV^{-1}} \times E_F
```

Combining these expressions gives the carrier density

```math
n
=
\frac{10^{-12}}{\pi}
\left(
\frac{\Delta \omega_G^{\mathrm{dop}}}
{42\,\hbar_{\mathrm{eV}}\, v_F \, 100}
\right)^2
```

Here, $\hbar_{\mathrm{eV}}$ is the reduced Planck constant in eV·s, the factor of
$100$ converts meters to centimeters, and $n$ is expressed in units of
$10^{12}~\mathrm{cm^{-2}}$.

---

## Strain Extraction

The strain contribution is obtained by projecting the Raman shifts onto the
strain axis.

This yields the strain-induced G-mode shift:

```math
\Delta \omega_G^{\mathrm{strain}}
=
\frac{\cos(\beta)}{\sin(\beta - \alpha)}
\left[
-\sin(\alpha)\, \Delta \omega_G
+
\cos(\alpha)\, \Delta \omega_{2D}
\right]
```

and, in linear approximation, the strain:

```math
\varepsilon
=
\frac{\Delta \omega_G^{\mathrm{strain}}}{\frac{\partial\omega_G}{\partial\varepsilon}}
=
\frac{\cos(\beta)}{\sin(\beta - \alpha)}
\,
\frac{
-\sin(\alpha)\, \Delta \omega_G
+
\cos(\alpha)\, \Delta \omega_{2D}
}
{\frac{\partial\omega_G}{\partial\varepsilon}}
```

The quantity $\frac{\partial\omega_G}{\partial\varepsilon}$ depends on the strain configuration [4,5]:

```math
\frac{\partial\omega_G}{\partial\varepsilon} =
\begin{cases}
-23.5, & \text{uniaxial strain} \\
-69.1, & \text{biaxial strain}
\end{cases}
```

## References

1. J.E. Lee, G. Ahn, J. Shim, Y.S. Lee, and S. Ryu,   
   **Optical separation of mechanical strain from charge doping in graphene**,  
   *Nature Communications* **3**, 1024 (2012).  
   https://doi.org/10.1038/ncomms2022

2. L. Banszerus, H. Janssen, M. Otto, A. Epping, T. Taniguchi, K. Watanabe,  
   B. Beschoten, D. Neumaier, and C. Stampfer,  
   **Identifying suitable substrates for high-quality graphene-based heterostructures**,  
   *2D Materials* **4**, 025030 (2017).  
   https://doi.org/10.1088/2053-1583/aa5b0f

3. G. Froehlicher and S. Berciaud,  
   **Raman spectroscopy of electrochemically gated graphene transistors: Geometrical capacitance, electron–phonon, electron–electron, and electron–defect scattering**,  
   *Physical Review B* **91**, 205413 (2015).  
   https://doi.org/10.1103/PhysRevB.91.205413

4. T. M. G. Mohiuddin, A. Lombardo, R. R. Nair, A. Bonetti, G. Savini, R. Jalil, N. Bonini, D. M. Basko, C. Galiotis, N. Marzari, K. S. Novoselov, A. K. Geim, and A. C. Ferrari,  
   **Uniaxial strain in graphene by Raman spectroscopy: G peak splitting, Grüneisen parameters, and sample orientation**,  
   *Physical Review B* **79**, 205433 (2009).  
   https://doi.org/10.1103/PhysRevB.79.205433

5. M. Goldsche, J. Sonntag, T. Khodkov, G. J. Verbiest, S. Reichardt, C. Neumann, T. Ouaj, N. von den Driesch, D. Buca, and C. Stampfer,  
   **Tailoring mechanically tunable strain fields in graphene**,  
   *Nano Letters* **18**(3), 1707–1713 (2018).  
   https://doi.org/10.1021/acs.nanolett.7b04774

6. L. Moczko, S. Reichardt, A. Singh, X. Zhang, E. Jouaiti, L. E. Parra López, J. L. P. Wolff, A. R. Moghe, E. Lorchat, R. Singh, K. Watanabe, T. Taniguchi, H. Majjad, M. Romeo, A. Gloppe, L. Wirtz, and S. Berciaud,  
   **Symmetry-Dependent Dielectric Screening of Optical Phonons in Monolayer Graphene**,  
   *Physical Review X* **15**(2), 021043 (2025).  
   https://doi.org/10.1103/PhysRevX.15.021043

7. J. Sonntag, K. Watanabe, T. Taniguchi, B. Beschoten, and C. Stampfer,  
   **Charge carrier density dependent Raman spectra of graphene encapsulated in hexagonal boron nitride**,  
   *Physical Review B* **107**(7), 075420 (2023).  
   https://doi.org/10.1103/PhysRevB.107.075420