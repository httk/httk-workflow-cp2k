# Test data

Captured CP2K 2026.2 `cp2k.psmp` runs (conda-forge
`cp2k-2026.2-mpi_openmpi_h5bc1a91_3`, single process without `mpirun`,
`OMP_NUM_THREADS=1`, `cp2k.psmp -i X.inp -o X.out`) of 8-atom conventional cubic
diamond silicon, Gamma point, `DZVP-MOLOPT-SR-GTH`/`GTH-PBE-q4`, cutoff 100 Ry.

| File | What it is |
| --- | --- |
| `si.inp`, `si.out` | converged energy: `*** SCF run converged in 12 steps ***`, `ENERGY\| Total FORCE_EVAL ( QS ) energy [hartree] -31.115927819707686`, `PROGRAM ENDED AT` |
| `si_noconv.inp`, `si_noconv.out` | `MAX_SCF 2`, `EPS_SCF 1.0E-10`: CP2K aborts with the `[ABORT]` box `SCF run NOT converged. To continue the calculation regardless, please set the keyword IGNORE_CONVERGENCE_FAILURE.` (`qs_scf.F:702`), exit status 1 |
| `si_noconv_ignored.inp`, `si_noconv_ignored.out` | as `si_noconv` with `IGNORE_CONVERGENCE_FAILURE`: `*** WARNING in qs_scf.F:700 :: SCF run NOT converged ***`, an `ENERGY\|` line nonetheless, `PROGRAM ENDED AT`, exit status 0 |
| `si_abort.inp`, `si_abort.out` | `RUN_TYPO` for `RUN_TYPE`: the `[ABORT]` box `found an unknown keyword RUN_TYPO in section GLOBAL` (`input/input_parsing.F:253`), exit status 1 |

All inputs set `PREFERRED_DIAG_LIBRARY SL`: this build's ELPA segfaults on a
single rank. The outputs are program output of those runs, with the run and data
directory paths in their headers replaced by `/scratch/cp2k`.
