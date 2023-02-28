# -*- coding: utf-8 -*-

"""
torchani_step
A SEAMM plug-in for TorchANI
"""

# Bring up the classes so that they appear to be directly in
# the torchani_step package.

from .torchani import TorchANI  # noqa: F401, E501
from .torchani_step import TorchANIStep  # noqa: F401, E501
from .torchani_parameters import TorchANIParameters  # noqa: F401
from .tk_torchani import TkTorchANI  # noqa: F401, E501

from .metadata import metadata  # noqa: F401

from .energy_step import EnergyStep  # noqa: F401
from .energy import Energy  # noqa: F401
from .energy_parameters import EnergyParameters  # noqa: F401
from .tk_energy import TkEnergy  # noqa: F401

from .optimization_step import OptimizationStep  # noqa: F401
from .optimization import Optimization  # noqa: F401
from .optimization_parameters import OptimizationParameters  # noqa: F401
from .tk_optimization import TkOptimization  # noqa: F401

# Handle versioneer
from ._version import get_versions

__author__ = "Paul Saxe"
__email__ = "psaxe@molssi.org"
versions = get_versions()
__version__ = versions["version"]
__git_revision__ = versions["full-revisionid"]
del get_versions, versions
