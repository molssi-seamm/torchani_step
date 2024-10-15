=======
History
=======
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
