# -*- coding: utf-8 -*-

"""Non-graphical part of the TorchANI step in a SEAMM flowchart
"""

import json
import logging
from pathlib import Path
import pkg_resources
import pprint  # noqa: F401
import sys

import torchani_step
import molsystem
import seamm
import seamm_util
from seamm_util import ureg, Q_, CompactJSONEncoder  # noqa: F401
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


class TorchANI(seamm.Node):
    """
    The non-graphical part of a TorchANI step in a flowchart.

    Attributes
    ----------
    parser : configargparse.ArgParser
        The parser object.

    options : tuple
        It contains a two item tuple containing the populated namespace and the
        list of remaining argument strings.

    subflowchart : seamm.Flowchart
        A SEAMM Flowchart object that represents a subflowchart, if needed.

    parameters : TorchANIParameters
        The control parameters for TorchANI.

    See Also
    --------
    TkTorchANI,
    TorchANI, TorchANIParameters
    """

    def __init__(
        self,
        flowchart=None,
        title="TorchANI",
        namespace="org.molssi.seamm.torchani",
        extension=None,
        logger=logger,
    ):
        """A step for TorchANI in a SEAMM flowchart.

        You may wish to change the title above, which is the string displayed
        in the box representing the step in the flowchart.

        Parameters
        ----------
        flowchart: seamm.Flowchart
            The non-graphical flowchart that contains this step.

        title: str
            The name displayed in the flowchart.
        namespace : str
            The namespace for the plug-ins of the subflowchart
        extension: None
            Not yet implemented
        logger : Logger = logger
            The logger to use and pass to parent classes

        Returns
        -------
        None
        """
        logger.debug(f"Creating TorchANI {self}")
        self.subflowchart = seamm.Flowchart(
            parent=self, name="TorchANI", namespace=namespace
        )  # yapf: disable

        super().__init__(
            flowchart=flowchart,
            title="TorchANI",
            extension=extension,
            module=__name__,
            logger=logger,
        )  # yapf: disable

        self._metadata = torchani_step.metadata
        self.parameters = torchani_step.TorchANIParameters()

    @property
    def version(self):
        """The semantic version of this module."""
        return torchani_step.__version__

    @property
    def git_revision(self):
        """The git version of this module."""
        return torchani_step.__git_revision__

    def set_id(self, node_id):
        """Set the id for node to a given tuple"""
        self._id = node_id

        # and set our subnodes
        self.subflowchart.set_ids(self._id)

        return self.next()

    def create_parser(self):
        """Setup the command-line / config file parser"""
        parser_name = self.step_type
        parser = seamm_util.getParser(name="SEAMM")

        # Remember if the parser exists ... this type of step may have been
        # found before
        parser_exists = parser.exists(parser_name)

        # Create the standard options, e.g. log-level
        result = super().create_parser(name=parser_name)

        if parser_exists:
            return result

        # Options for TorchANI
        parser.add_argument(
            parser_name,
            "--torchani-path",
            default="",
            help="the path to the DFTB+ executable",
        )
        parser.add_argument(
            parser_name,
            "--torchani-exe",
            default="SEAMM_TorchANI.py",
            help="the name of the TorchANI executable of script",
        )

        return result

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
        self.subflowchart.root_directory = self.flowchart.root_directory

        # Get the first real node
        node = self.subflowchart.get_node("1").next()

        text = self.header + "\n\n"
        while node is not None:
            try:
                text += __(node.description_text(), indent=3 * " ").__str__()
            except Exception as e:
                print(f"Error describing torchani flowchart: {e} in {node}")
                logger.critical(f"Error describing torchani flowchart: {e} in {node}")
                raise
            except:  # noqa: E722
                print(
                    "Unexpected error describing torchani flowchart: {} in {}".format(
                        sys.exc_info()[0], str(node)
                    )
                )
                logger.critical(
                    "Unexpected error describing torchani flowchart: {} in {}".format(
                        sys.exc_info()[0], str(node)
                    )
                )
                raise
            text += "\n"
            node = node.next()

        return text

    def run(self):
        """Run a TorchANI step.

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

        # Print our header to the main output
        printer.important(self.header)
        printer.important("")

        # Access the options and find the executable
        options = self.options

        if options["torchani_path"] == "":
            torchani_exe = seamm_util.check_executable(options["torchani_exe"])
        else:
            torchani_exe = (
                Path(options["torchani_path"]).expanduser().resolve()
                / options["torchani_exe"]
            )

        next_node = super().run(printer)

        # Get the first real node
        node1 = self.subflowchart.get_node("1").next()

        # Print what we will do as we get the input
        schema = {}
        node = node1
        nodes = []
        while node is not None:
            nodes.append(node)
            schema = node.get_input(schema)
            for value in node.description:
                printer.important(value)
                printer.important(" ")
            node = node.next()

        schema_name = schema["schema name"]
        schema_version = schema["schema version"]
        input_data = f"!MolSSI {schema_name} {schema_version}\n"
        input_data += json.dumps(
            schema, indent=4, cls=CompactJSONEncoder, sort_keys=True
        )
        files = {"input.json": input_data}
        logger.info("input.json:\n" + files["input.json"])

        # Output files locally
        for filename, data in files.items():
            path = directory / filename
            mode = "wb" if type(data) is bytes else "w"
            with open(path, mode) as fd:
                fd.write(data)

        local = seamm.ExecLocal()
        result = local.run(
            cmd=f"{torchani_exe} input.json",
            files=files,
            return_files=["output.json"],
            shell=True,
            in_situ=True,
            directory=directory,
        )

        if result is None:
            logger.error("There was an error running TorchANI")
            return None

        logger.debug("\n" + pprint.pformat(result))

        logger.info("stdout:\n" + result["stdout"])
        if result["stderr"] != "":
            lines = result["stderr"].splitlines()
            tmp = []
            for line in lines:
                if "cuaev not installed" in line:
                    continue
                if "Creating a tensor from a list of numpy" in line:
                    continue
                if "cell = torch.tensor(self.atoms.get_cell(complete=True)" in line:
                    continue
                tmp.append(line)
            if len(tmp) > 0:
                logger.warning("stderr:\n" + "\n".join(tmp))

        lines = result["output.json"]["data"].splitlines()
        line = lines[0]
        if line[0:7] != "!MolSSI":
            raise RuntimeError(
                "Output file is not a MolSSI schema file, organization is not MolSSI: "
                f"'{line}'"
            )
        tmp = line.split()
        if len(tmp) < 3:
            raise RuntimeError(f"Output file is not a MolSSI schema file: '{line}'")
        if tmp[1] != "cms_schema":
            raise RuntimeError(f"Output file is not a CMS schema file: '{line}'")

        schema = json.loads("\n".join(lines[1:]))

        # Check that the job ran OK
        for step_no, step in enumerate(schema["workflow"]):
            if "success" not in step:
                self.logger.warning(f"Step {step_no} did not run")
                continue
            if step["success"]:
                nodes[step_no].analyze(schema=schema, step_no=step_no)
            else:
                if "error" in step:
                    self.logger.error("TorchANI had an error:\n\n" + step["error"])
                    raise RuntimeError("TorchANI had an error:\n\n" + step["error"])

        # Add other citations here or in the appropriate place in the code.
        # Add the bibtex to data/references.bib, and add a self.reference.cite
        # similar to the above to actually add the citation to the references.
        self.references.cite(
            raw=self._bibliography["TorchANI"],
            alias="TorchANI",
            module="torchani_step",
            level=1,
            note="The citation for the TorchANI software.",
        )
        self.references.cite(
            raw=self._bibliography["ANI"],
            alias="ANI",
            module="torchani_step",
            level=1,
            note="The citation for the ANI ML.",
        )
        self.references.cite(
            raw=self._bibliography["ANI_dataset"],
            alias="ANI_dataset",
            module="torchani_step",
            level=2,
            note="The citation for the ANI dataset.",
        )

        return next_node
