# -*- coding: utf-8 -*-

"""The graphical part of a Optimization step"""

import pprint  # noqa: F401
import tkinter as tk
import tkinter.ttk as ttk

import torchani_step  # noqa: F401
from seamm_util import ureg, Q_, units_class  # noqa: F401
import seamm_widgets as sw


class TkOptimization(torchani_step.TkEnergy):
    """
    The graphical part of a Optimization step in a flowchart.

    Attributes
    ----------
    tk_flowchart : TkFlowchart = None
        The flowchart that we belong to.
    node : Node = None
        The corresponding node of the non-graphical flowchart
    canvas: tkCanvas = None
        The Tk Canvas to draw on
    dialog : Dialog
        The Pmw dialog object
    x : int = None
        The x-coordinate of the center of the picture of the node
    y : int = None
        The y-coordinate of the center of the picture of the node
    w : int = 200
        The width in pixels of the picture of the node
    h : int = 50
        The height in pixels of the picture of the node
    self[widget] : dict
        A dictionary of tk widgets built using the information
        contained in Optimization_parameters.py

    See Also
    --------
    Optimization, TkOptimization,
    OptimizationParameters,
    """

    def __init__(
        self,
        tk_flowchart=None,
        node=None,
        canvas=None,
        x=None,
        y=None,
        w=200,
        h=50,
    ):
        """
        Initialize a graphical node.

        Parameters
        ----------
        tk_flowchart: Tk_Flowchart
            The graphical flowchart that we are in.
        node: Node
            The non-graphical node for this step.
        namespace: str
            The stevedore namespace for finding sub-nodes.
        canvas: Canvas
           The Tk canvas to draw on.
        x: float
            The x position of the nodes center on the canvas.
        y: float
            The y position of the nodes cetner on the canvas.
        w: float
            The nodes graphical width, in pixels.
        h: float
            The nodes graphical height, in pixels.

        Returns
        -------
        None
        """
        self.dialog = None

        super().__init__(
            tk_flowchart=tk_flowchart,
            node=node,
            canvas=canvas,
            x=x,
            y=y,
            w=w,
            h=h,
        )

    def create_dialog(self, title="TorchANI Optimization"):
        """
        Create the dialog. A set of widgets will be chosen by default
        based on what is specified in the Optimization_parameters
        module.

        Parameters
        ----------
        None

        Returns
        -------
        None

        See Also
        --------
        TkOptimization.reset_dialog
        """

        super().create_dialog(title=title)

        # Shortcut for parameters
        P = self.node.parameters

        # Frame to isolate widgets
        opt_frame = self["optimization frame"] = ttk.LabelFrame(
            self["frame"],
            borderwidth=4,
            relief="sunken",
            text="Optimization Parameters",
            labelanchor="n",
            padding=10,
        )

        for key in torchani_step.OptimizationParameters.parameters:
            if key not in ("structure handling", "configuration name"):
                self[key] = P[key].widget(opt_frame)

        for key in ("minimizer",):
            self[key].bind("<<ComboboxSelected>>", self.reset_dialog)
            self[key].bind("<Return>", self.reset_dialog)
            self[key].bind("<FocusOut>", self.reset_dialog)

        # Create the structure-handling widgets
        sframe = self["structure frame"] = ttk.LabelFrame(
            self["frame"], text="Configuration Handling", labelanchor=tk.N
        )
        row = 0
        widgets = []
        for key in ("structure handling", "system name", "configuration name"):
            self[key] = P[key].widget(sframe)
            self[key].grid(row=row, column=0, sticky=tk.EW)
            widgets.append(self[key])
            row += 1
        sw.align_labels(widgets, sticky=tk.E)

        opt_frame.grid(row=0, column=1)
        sframe.grid(row=1, column=0, columnspan=2)

    def reset_dialog(self, widget=None):
        super().reset_dialog()

        row = 0
        self["optimization frame"].grid(row=row, column=1, sticky=tk.EW)
        row += 1
        self["structure frame"].grid(row=row, column=0, columnspan=2)
        row += 1

        # And the widgets in our frame
        self.reset_optimization_frame()

        return row

    def reset_optimization_frame(self):
        """Layout the optimization frame according to the current values."""
        frame = self["optimization frame"]
        for slave in frame.grid_slaves():
            slave.grid_forget()

        widgets = []

        row = 0

        for key in ("minimizer", "max steps", "convergence"):
            self[key].grid(row=row, column=0, columnspan=3, sticky=tk.W)
            widgets.append(self[key])
            row += 1

        sw.align_labels(widgets, sticky=tk.E)

        frame.columnconfigure(0, minsize=50)

        return row

    def right_click(self, event):
        """
        Handles the right click event on the node.

        Parameters
        ----------
        event : Tk Event

        Returns
        -------
        None

        See Also
        --------
        TkOptimization.edit
        """

        super().right_click(event)
        self.popup_menu.add_command(label="Edit..", command=self.edit)

        self.popup_menu.tk_popup(event.x_root, event.y_root, 0)
