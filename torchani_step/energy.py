# -*- coding: utf-8 -*-

"""Non-graphical part of the Energy step in a TorchANI flowchart
"""

import logging
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


class Energy(seamm.Node):
    """
    The non-graphical part of a Energy step in a flowchart.

    Attributes
    ----------
    parser : configargparse.ArgParser
        The parser object.

    options : tuple
        It contains a two item tuple containing the populated namespace and the
        list of remaining argument strings.

    subflowchart : seamm.Flowchart
        A SEAMM Flowchart object that represents a subflowchart, if needed.

    parameters : EnergyParameters
        The control parameters for Energy.

    See Also
    --------
    TkEnergy,
    Energy, EnergyParameters
    """

    def __init__(self, flowchart=None, title="Energy", extension=None, logger=logger):
        """A substep for Energy in a subflowchart for TorchANI.

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
        logger.debug(f"Creating Energy {self}")

        super().__init__(
            flowchart=flowchart,
            title=title,
            extension=extension,
            module=__name__,
            logger=logger,
        )  # yapf: disable

        self._calculation = "energy"
        self._model = None
        self._metadata = torchani_step.metadata
        self.parameters = torchani_step.EnergyParameters()

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

        if P["gradients"]:
            text = "Calculating the energy and gradients "
        else:
            text = "Calculating the energy "
        text += "using the ANI machine learning model {model}."
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

        return self.header + "\n" + __(text, **P, indent=4 * " ").__str__()

    def get_input(self, schema):
        """Get the input for the energy in TorchANI.

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

        # Get the current system and configuration (ignoring the system...)
        _, configuration = self.get_system_configuration(None)

        # Set up the description.
        self.description = []
        self.description.append(__(self.description_text(P), **P, indent=self.indent))

        # Check the elements
        parameterization = P["model"]
        if parameterization == "ANI-1x":
            covered_elements = {"C", "H", "N", "O"}
        elif parameterization == "ANI-1ccx":
            covered_elements = {"C", "H", "N", "O"}
        elif parameterization == "ANI-2x":
            covered_elements = {"C", "H", "N", "O", "F", "S", "Cl"}
        else:
            raise RuntimeError(f"Don't recognize ANI model '{parameterization}'.")

        elements = set(configuration.atoms.symbols)
        if not elements <= covered_elements:
            raise RuntimeError(
                f"The {parameterization} parameterization covers the "
                f" elements {sorted(covered_elements)}. The system has "
                f"{sorted(elements)}."
            )

        # Get the QCSchema structure for the molecule
        schema = configuration.to_cms_schema()

        # add workflow step to the schema
        step = {
            "model": {
                "method": "ML",
                "model": "ANI",
                "parameterization": P["model"],
            },
            "keywords": {"submodel": P["submodel"]},
            "provenance": {
                "creator": "SEAMM/torchani_step",
                "version": "1.1",
                "routine": "torchani_step.energy.get_input",
            },
            "required results": [
                "energy",
            ],
        }

        results = step["required results"]
        if P["gradients"]:
            results.append("gradients")

        schema["workflow"] = [step]

        # Add other citations here or in the appropriate place in the code.
        # Add the bibtex to data/references.bib, and add a self.reference.cite
        # similar to the above to actually add the citation to the references.

        return schema

    def analyze(self, indent="", **kwargs):
        """Do any analysis of the output from this step.

        Also print important results to the local step.out file using
        "printer".

        Parameters
        ----------
        indent: str
            An extra indentation for the output
        """
        P = self.parameters.current_values_to_dict(
            context=seamm.flowchart_variables._data
        )

        # Get the appropriate system/configuration for the new coordinates
        system, configuration = self.get_system_configuration(P)

        schema = kwargs["schema"]
        step_no = kwargs["step_no"]

        table = {
            "System": [],
            "Configuration": [],
            "Energy": [],
            "Std Dev": [],
        }

        # The model chemistry
        self.model = f"ANI/{P['model']}"

        # Get the appropriate system/configuration
        system, configuration = self.get_system_configuration(P)

        have_stdev = False
        for system in schema["systems"]:
            system_name = system["name"]
            for no, config_data in enumerate(system["configurations"]):
                if no == 0:
                    table["System"].append(system_name)
                else:
                    table["System"].append("")
                table["Configuration"].append(config_data["name"])
                results = config_data["results"]["data"][step_no]
                results["model"] = "TorchANI/" + self.model
                results["energy,units"] = "E_h"
                results["gradients,units"] = "E_h/Å"

                table["Energy"].append(f"{results['energy']:.6f}")
                if "energy, stdev" in results:
                    table["Std Dev"].append(f"{results['energy, stdev']:.6f}")
                    have_stdev = True
                else:
                    table["Std Dev"].append("")

                # And store results
                self.store_results(
                    configuration=configuration,
                    data=results,
                )

        if not have_stdev:
            del table["Std Dev"]

        text_lines = []
        text_lines.append("                     Results")
        text_lines.append(
            tabulate(
                table,
                headers="keys",
                tablefmt="rounded_outline",
                colalign=("left", "left", "decimal", "decimal"),
                disable_numparse=True,
            )
        )
        text_lines.append("\n")

        text = textwrap.indent("\n".join(text_lines), self.indent + 4 * " ")
        printer.normal(text)

        # Citation for the specific method
        self.references.cite(
            raw=self._bibliography[P["model"]],
            alias="P['model']",
            module="torchani_step",
            level=2,
            note=f"The citation for the {P['model']} ML model.",
        )
