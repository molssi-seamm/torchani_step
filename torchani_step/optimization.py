# -*- coding: utf-8 -*-

"""Non-graphical part of the Optimization step in a TorchANI flowchart
"""

import logging
import math
from pathlib import Path
import pkg_resources
import pprint  # noqa: F401
import textwrap

from tabulate import tabulate

import torchani_step
import molsystem
import seamm
from seamm_util import ureg, Q_  # noqa: F401
import seamm_util.printing as printing
from seamm_util.printing import FormattedText as __

# In addition to the normal logger, two logger-like printing facilities are
# defined: "job" and "printer". "job" send output to the main job.out file for
# the job, and should be used very sparingly, typically to echo what this step
# will do in the initial summary of the job.
#
# "printer" sends output to the file "step.out" in this steps working
# directory, and is used for all normal output from this step.

logger = logging.getLogger(__name__)
job = printing.getPrinter()
printer = printing.getPrinter("TorchANI")

# Add this module's properties to the standard properties
path = Path(pkg_resources.resource_filename(__name__, "data/"))
csv_file = path / "properties.csv"
if path.exists():
    molsystem.add_properties_from_file(csv_file)


class Optimization(torchani_step.Energy):
    """
    The non-graphical part of a Optimization step in a flowchart.

    Attributes
    ----------
    parser : configargparse.ArgParser
        The parser object.

    options : tuple
        It contains a two item tuple containing the populated namespace and the
        list of remaining argument strings.

    subflowchart : seamm.Flowchart
        A SEAMM Flowchart object that represents a subflowchart, if needed.

    parameters : OptimizationParameters
        The control parameters for Optimization.

    See Also
    --------
    TkOptimization,
    Optimization, OptimizationParameters
    """

    def __init__(
        self, flowchart=None, title="Optimization", extension=None, logger=logger
    ):
        """A substep for Optimization in a subflowchart for TorchANI.

        You may wish to change the title above, which is the string displayed
        in the box representing the step in the flowchart.

        Parameters
        ----------
        flowchart: seamm.Flowchart
            The non-graphical flowchart that contains this step.

        title: str
            The name displayed in the flowchart.
        extension: None
            Not yet implemented
        logger : Logger = logger
            The logger to use and pass to parent classes

        Returns
        -------
        None
        """
        logger.debug(f"Creating Optimization {self}")

        super().__init__(
            flowchart=flowchart,
            title=title,
            extension=extension,
            logger=logger,
        )

        self._calculation = "optimization"
        self._model = None
        self._metadata = torchani_step.metadata
        self.parameters = torchani_step.OptimizationParameters()

    @property
    def header(self):
        """A printable header for this section of output"""
        return "Step {}: {}".format(".".join(str(e) for e in self._id), self.title)

    @property
    def version(self):
        """The semantic version of this module."""
        return torchani_step.__version__

    @property
    def git_revision(self):
        """The git version of this module."""
        return torchani_step.__git_revision__

    def description_text(self, P=None):
        """Create the text description of what this step will do.
        The dictionary of control values is passed in as P so that
        the code can test values, etc.

        Parameters
        ----------
        P: dict
            An optional dictionary of the current values of the control
            parameters.
        Returns
        -------
        str
            A description of the current step.
        """
        if not P:
            P = self.parameters.values_to_dict()

        text = "Optimizing the structure using the ANI machine learning model {model}."
        submodels = P["submodel"]
        if submodels == "all":
            text += (
                " All the parameterizations of the model will be used, and the "
                "results averaged."
            )
        else:
            if "," in submodels or "-" in submodels or self.is_expr(submodels):
                text += " These parameterizations of the model will be used: "
                "{submodels}, and the results will be averaged."
            else:
                text += " The {submodels} parameterization of the model will be used."

        text += "\n\nThe optimization will use the {minimizer}"
        if "minimizer" not in P["minimizer"]:
            text += " minimizer"
        text += (
            " with a convergence criterion of {convergence} and a limit of {max steps}"
            " steps."
        )

        text += "\n"
        text += seamm.standard_parameters.structure_handling_description(P)

        return self.header + "\n" + __(text, **P, indent=4 * " ").__str__()

    def get_input(self, schema):
        """Get the input for the optimization in TorchANI.

        Parameters
        ----------
        None

        Returns
        -------
        seamm.Node
            The next node object in the flowchart.
        """
        # Create the directory
        directory = Path(self.directory)
        directory.mkdir(parents=True, exist_ok=True)

        # Get the values of the parameters, dereferencing any variables
        P = self.parameters.current_values_to_dict(
            context=seamm.flowchart_variables._data
        )

        # Get the schema for the energy of the structure
        schema = super().get_input(schema)

        results = schema["workflow"][0]["required results"]
        if "gradients" not in results:
            results.append("gradients")
        results.append("optimized structure")

        schema["control parameters"] = {
            "optimization": {
                "minimizer": P["minimizer"],
                "maximum steps": P["max steps"],
                "convergence": P["convergence"].magnitude,
                "convergence units": str(P["convergence"].units),
            }
        }

        # Set up the description, overwriting that of the energy.
        self.description = []
        self.description.append(__(self.description_text(P), **P, indent=self.indent))

        return schema

    def analyze(self, indent="", schema=None, table=None, step_no=None, **kwargs):
        """Do any analysis of the output from this step.

        Also print important results to the local step.out file using
        "printer".

        Parameters
        ----------
        indent: str
            An extra indentation for the output
        """
        if schema is None:
            printer.normal(
                __(
                    "The Optimization step failed. There is no output at all!",
                    indent=4 * " ",
                    wrap=True,
                    dedent=False,
                )
            )
            return

        if "workflow" not in schema or len(schema["workflow"]) == 0:
            printer.normal(
                __(
                    "The Optimization step failed because there was no workflow!?!",
                    indent=4 * " ",
                    wrap=True,
                    dedent=False,
                )
            )
            return

        if not schema["workflow"][0]["success"]:
            text = "The Optimization step failed. There is no output at all!"
            printer.normal(__(text, indent=4 * " ", wrap=True, dedent=False))
            text = schema["workflow"][0]["error"]
            printer.normal(__(text, indent=4 * " ", wrap=False, dedent=False))
            raise RuntimeError(f"The TorchANI optimization failed:\n{text}")
            return

        P = self.parameters.current_values_to_dict(
            context=seamm.flowchart_variables._data
        )

        results = schema["systems"][0]["configurations"][0]["results"]["data"][step_no]

        results["energy,units"] = "eV"
        results["gradients,units"] = "eV/Å"

        energy = Q_(results["energy"], "eV").to("Eh")
        n_steps = results["number of optimization steps"]

        force_units = P["convergence"].units

        gradients = results["gradients"]
        max_derivative = 0
        rms = 0.0
        for row in gradients:
            sum = 0.0
            for v in row:
                sum += v**2
            dE = math.sqrt(sum)
            rms += sum
            if abs(dE) > max_derivative:
                max_derivative = abs(dE)
        rms = Q_(math.sqrt(rms / len(gradients)), "eV/Å").to(force_units)
        max_derivative = Q_(max_derivative, "eV/Å").to(force_units)

        text = ""
        if table is None:
            table = {
                "Property": [],
                "Value": [],
                "Units": [],
            }

        text = "The optimization converged."

        table["Property"].append("Steps")
        table["Value"].append(n_steps)
        table["Units"].append("")

        table["Property"].append("Total Energy")
        table["Value"].append(f"{energy.magnitude:.6f}")
        table["Units"].append("E_h")

        table["Property"].append("Maximum Force")
        table["Value"].append(f"{max_derivative.magnitude:.4f}")
        table["Units"].append(str(max_derivative.units))

        table["Property"].append("RMS Force")
        table["Value"].append(f"{rms.magnitude:.4f}")
        table["Units"].append(str(rms.units))

        tmp = tabulate(
            table,
            headers="keys",
            tablefmt="rounded_outline",
            colalign=("center", "decimal", "left"),
            disable_numparse=True,
        )
        length = len(tmp.splitlines()[0])
        text_lines = []
        text_lines.append("Results".center(length))
        text_lines.append(tmp)

        if text != "":
            text = str(__(text, indent=self.indent + 4 * " "))
            text += "\n\n"
        text += textwrap.indent("\n".join(text_lines), self.indent + 7 * " ")
        printer.normal(text)

        # Get the appropriate system/configuration for the new coordinates
        system, configuration = self.get_system_configuration(P)

        if P["system name"] == "optimized with <Hamiltonian>":
            system.name = f"optimized with {P['model']}"
        if P["configuration name"] == "optimized with <Hamiltonian>":
            configuration.name = f"optimized with {P['model']}"

        configuration.atoms.set_coordinates(results["coordinates"])

        text = (
            f"\nThe optimized structure has been placed in {system.name}/"
            f"{configuration.name}"
        )

        printer.normal(__(text, indent=self.indent + 4 * " "))

        # Citation for the specific method
        self.references.cite(
            raw=self._bibliography[P["model"]],
            alias="P['model']",
            module="torchani_step",
            level=2,
            note=f"The citation for the {P['model']} ML model.",
        )
        self.references.cite(
            raw=self._bibliography["ase"],
            alias="ase",
            module="torchani_step",
            level=2,
            note="The citation for ASE.",
        )
