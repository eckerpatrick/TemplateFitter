"""
Provides some utility functions for matplotlib plots.
"""
import os
import logging
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.axes._axes as axes
import matplotlib.colors as mpl_colors

from matplotlib import figure
from typing import Union, Tuple

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "AxesType",
    "FigureType",
    "export",
    "color_fader"
]

AxesType = axes.Axes
FigureType = figure.Figure


def export(
        fig: plt.Figure,
        filename: Union[str, os.fspath],
        target_dir: str = "plots/",
        file_formats: Tuple[str] = (".pdf", ".png"),
        close_figure: bool = False
) -> None:
    """
    Convenience function for saving a matplotlib figure.

    :param fig: A matplotlib figure.
    :param filename: Filename of the plot without .pdf suffix.
    :param file_formats: Tuple of file formats specifying the format
                         figure will be saved as.
    :param target_dir: Directory where the plot will be saved in.
                       Default is './plots/'.
    :param close_figure: Whether to close the figure after saving it.
                         Default is False
    :return: None
    """
    os.makedirs(target_dir, exist_ok=True)

    for file_format in file_formats:
        fig.savefig(os.path.join(target_dir, f'{filename}{file_format}'), bbox_inches="tight")

    if close_figure:
        plt.close(fig)


def color_fader(color_1: str, color_2: str, mix: float = 0.) -> str:
    c1 = np.array(mpl_colors.to_rgb(color_1))
    c2 = np.array(mpl_colors.to_rgb(color_2))
    return mpl_colors.to_hex((1 - mix) * c1 + mix * c2)
