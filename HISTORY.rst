=======
History
=======
2026.9.25 -- Bugfix: the TorchANI step failed to load on Python 3.12 outside conda
    * The step used the deprecated ``pkg_resources`` module, which is only present
      when setuptools is installed. Conda installs setuptools into every
      environment, but a plain venv does not, so there the step failed to import
      with ``No module named 'pkg_resources'`` and was missing from the flowchart
      editor. It now uses ``importlib.resources``. (This change was made in March
      2026 but never released.)

2024.3.10 -- Added RMSD for optimization and timing information
    * Added the RMSD between the initial and final structure for optimization.
    * Generally improved the output.
    * Added more properti4es to results that can be saved.
    * Updated installation to work with latest SEAMM installer.
      
2024.2.7 -- Bugfix: handling of configurations and gradients
    * The code handled configurations incorrectly.This has been fixed.
    * The gradients were not output correctly, causing problems in e.g the Structure
      and Thermochemistry steps.
    * Changed logging at the INFO level to DEBUG to clean up the output of geomeTRIC.
	
2024.10.15 -- Bugfix: error if used in a loop and previous directories deleted.
   * The code crashed if called with a loop in the flowchart, and the last directory of
     a previous loop iteration was deleted before running the next iteration.

2024.5.12.1 -- Fixed problem with commandline in Docker
    * There was a problem in the commandline for running TorchANI in a Docker container.
      
2024.5.12 -- Added support for Docker and for Energy Scan
    * Creating images for Docker automatically on release
    * Added the energy and gradients for output to JSON for e.g. Energy Scan
      
2023.2.28 -- Initial version!
    * Handles energy and optimization.
    * ANI-1x, ANI-1ccx, and ANI-2x models
      
2023.1.17 (2023-01-17)
    * Plug-in created using the SEAMM plug-in cookiecutter.
