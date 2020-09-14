
from typing import List, Dict, Tuple
import pandas as pd

from templatefitter.fit_model.model_builder import FitModel
from templatefitter.plotter.fit_result_plots import FitResultPlot
from templatefitter.plotter.histogram_plots import SimpleHistogramPlot
from templatefitter.plotter.histogram_variable import HistVariable

class ShapePlotter:

    def __init__(
            self,
            fit_model: FitModel,
            variable: HistVariable
    ) -> None:
        self._fit_model = fit_model
        self._variable = variable

    def plot_shape_comparison(
            self,
            channel_name: str
    ) -> None:
        assert channel_name in [c.name for c in self._fit_model.mc_channels_to_plot]

        channel = self._fit_model.mc_channels_to_plot.get_channel_by_name(channel_name)
        shp = SimpleHistogramPlot(variable=self._variable)

        for template in channel.templates:
            template_bin_count = template.bin_counts

            shp.add_component(
                label=template.latex_label,
                data=template_bin_count
            )

        ax = shp.plot_on(normed=True)
