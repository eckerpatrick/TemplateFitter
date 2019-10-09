"""
Class which defines the fit model by combining templates and handles the computation.
"""

import logging
import numpy as np
from numba import jit
from scipy.linalg import block_diag
from abc import ABC, abstractmethod

from typing import List, Tuple, NamedTuple

from templatefitter.utility import xlogyx
from templatefitter.plotter import old_plotting

from templatefitter.fit_model.channel import ChannelContainer
from templatefitter.binned_distributions.binning import Binning
from templatefitter.fit_model.parameter_handler import ParameterHandler

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = ["ModelBuilder"]


class FractionConversionInfo(NamedTuple):
    needed: bool
    conversion_matrix: np.ndarray
    conversion_vector: np.ndarray


class ModelBuilder:
    def __init__(
            self,
            data,  # TODO: Type hint
            parameter_handler: ParameterHandler,
    ):
        self._data = data
        self._params = parameter_handler

        self._channels = None

        self._fraction_conversion = None

        self._is_checked = False

        # TODO:
        # self.yield_indices = []

        # self.subfraction_indices = []
        # self.num_fractions = 0

        # self.constrain_indices = []
        # self.constrain_value = np.array([])
        # self.constrain_sigma = np.array([])

        # self.x_obs = data.bin_counts.flatten()
        # self.x_obs_errors = data.bin_errors.flatten()

        # self._inv_corr = np.array([])
        # self.bin_par_slice = (0, 0)

        # self._dim = None
        # self.shape = ()

    # TODO: Check that every template of a model uses the same ParameterHandler instance!
    # TODO: Possible Check: For first call of expected_events_per_bin: Check if template indices are ordered correctly.

    def setup_model(self, channels: ChannelContainer):
        if not all(c.params is self._params for c in channels):
            raise RuntimeError("The used ParameterHandler instances are not the same!")

        if self._channels is not None:
            raise RuntimeError("Model already has channels defined!")

        self._channels = channels

        # TODO: Initialize parameters...
        #           - set indices,
        #           - identify floating parameters and fixed ones,
        #           - differentiate between different parameter types in ParameterHandler? -> would probably be better,

        self._initialize_fraction_conversion()

        # TODO: Complete Model setup

    def get_yields_vector(self):
        # TODO: Yields are provided by parameter handler...
        # TODO: number of yields = number of components
        # TODO: Vector or matrix? <-> Use additional dimension for channels?
        pass

    def get_fractions_vector(self):
        # TODO: Fractions are provided by parameter handler...
        # TODO: Number of fractions = number of templates - number of multi template components
        # TODO: Are NOT DIFFERENT for different channels
        pass

    def _initialize_fraction_conversion(self):
        # Fraction conversion matrix and vector should be equal in all channels.
        # The matrices and vectors are generated for each channel, tested for equality and then stored once.

        conversion_matrices = []
        conversion_vectors = []
        for channel in self._channels:
            matrices_for_channel = []
            vectors_for_channel = []
            for component in channel:
                n_sub = component.number_of_subcomponents
                # TODO: What about component.share_yield ? Maybe remove has_fractions and only use shared_yield...
                if component.has_fractions:
                    matrix_part1 = np.diag(np.ones(n_sub - 1))
                    matrix_part2 = -1 * np.ones(n_sub - 1)
                    matrix = np.vstack([matrix_part1, matrix_part2])
                    matrices_for_channel.append(matrix)
                    vector = np.zeros((n_sub, 1))
                    vector[-1][0] = 1.
                    vectors_for_channel.append(vector)
                else:
                    matrices_for_channel.append(np.zeros((n_sub, n_sub)))
                    vectors_for_channel.append(np.ones((n_sub, 1)))

            conversion_matrices.append(block_diag(*matrices_for_channel))
            conversion_vectors.append(np.vstack(vectors_for_channel))

        assert all(m.shape[0] == v.shape[0] for m, v in zip(conversion_matrices, conversion_vectors))
        assert all(m.shape[0] == n_f for m, n_f in zip(conversion_matrices, self.number_of_fraction_parameters))
        assert all(np.array_equal(m, conversion_matrices[0]) for m in conversion_matrices)
        assert all(np.array_equal(v, conversion_vectors[0]) for v in conversion_vectors)

        self._fraction_conversion = FractionConversionInfo(
            needed=(not all(conversion_vectors[0] == 1)),
            conversion_matrix=conversion_matrices[0],
            conversion_vector=conversion_vectors[0]
        )

    def get_efficiency_vector(self):
        # TODO: Efficiencies are provided by parameter handler...
        # TODO: Number of efficiencies = number of templates
        # TODO: Are DIFFERENT for different channels
        # TODO: Might be fixed (extracted from simulation) or floating
        # TODO: Should be normalized to 1 over all channels? Can not be done when set to be floating
        # TODO: Would benefit from allowing constrains, e.g. let them float around MC expectation
        pass

    def get_template_bin_counts(self):
        # TODO: Get initial (not normed) shapes from templates
        pass

    def create_templates(self):
        # TODO: Are normed after application of corrections, but this should be done in calculate_bin_count!
        # TODO: Based on template bin counts
        pass

    def calculate_bin_count(self):
        if not self._is_checked:
            assert self._fraction_conversion is not None
            assert isinstance(self._fraction_conversion, FractionConversionInfo), type(self._fraction_conversion)
            # TODO: Check shapes!

        if self._fraction_conversion.needed:
            bin_count = yield_parameters * (
                    self._fraction_conversion.conversion_matrix * fraction_parameters
                    + self._fraction_conversion.conversion_vector
            ) * normed_efficiency_parameters * normed_templates
        else:
            bin_count = yield_parameters * (
                    self._fraction_conversion.conversion_matrix * fraction_parameters
                    + self._fraction_conversion.conversion_vector
            ) * normed_efficiency_parameters * normed_templates

        if not self._is_checked:
            assert bin_count is not None
            # TODO: Check output shape!

            self._is_checked = True

        return bin_count

    @property
    def number_of_channels(self) -> int:
        return len(self._channels)

    @property
    def binning(self) -> Tuple[Binning, ...]:
        return tuple(channel.binning for channel in self._channels)

    @property
    def number_of_components(self) -> Tuple[int, ...]:
        return tuple(len(channel) for channel in self._channels)

    @property
    def number_of_templates(self) -> Tuple[int, ...]:
        return tuple(sum([comp.number_of_subcomponents for comp in ch.components]) for ch in self._channels)

    @property
    def number_of_independent_templates(self) -> Tuple[int, ...]:
        return tuple(
            sum([1 if comp.shared_yield else comp.number_of_subcomponents for comp in ch.components])
            for ch in self._channels
        )

    @property
    def number_of_fraction_parameters(self) -> Tuple[int, ...]:
        return tuple(
            sum([comp.number_of_subcomponents - 1 if comp.shared_yield
                 else comp.number_of_subcomponents for comp in ch.components])
            for ch in self._channels
        )

    # TODO: The following stuff is not adapted, yet...

    def template_matrix(self):
        """ Creates the fixed template stack """
        fractions_per_template = [template._flat_bin_counts for template in self.templates.values()]

        self.template_fractions = np.stack(fractions_per_template)
        self.shape = self.template_fractions.shape

    def relative_error_matrix(self):
        errors_per_template = [template.errors() for template
                               in self.templates.values()]

        self.template_errors = np.stack(errors_per_template)

    def initialise_bin_pars(self):
        """ Add parameters for the template """

        bin_pars = np.zeros((self.num_bins * len(self.templates), 1))
        bin_par_names = []
        for template in self.templates.values():
            bin_par_names += ["{}_binpar_{}".format(template.name, i) for i in range(0, self.num_bins)]
        bin_par_indices = self._params.add_parameters(bin_pars, bin_par_names)
        self.bin_par_slice = (bin_par_indices[0], bin_par_indices[-1] + 1)

    @jit
    def expected_events_per_bin(self, bin_pars: np.ndarray, yields: np.ndarray, sub_pars: np.ndarray) -> np.ndarray:
        sys_pars = self._params.get_parameters_by_index(self.sys_pars)
        # compute the up and down errors for single par variations
        up_corr = np.prod(1 + sys_pars * (sys_pars > 0) * self.up_errors, 0)
        down_corr = np.prod(1 + sys_pars * (sys_pars < 0) * self.down_errors, 0)
        corrections = (1 + self.template_errors * bin_pars) * (up_corr + down_corr)
        sub_fractions = np.matmul(self.converter_matrix, sub_pars) + self.converter_vector
        fractions = self.template_fractions * corrections
        norm_fractions = fractions / np.sum(fractions, 1)[:, np.newaxis]
        expected_per_bin = np.sum(norm_fractions * yields * sub_fractions, axis=0)
        return expected_per_bin
        # compute overall correction terms
        # get sub template fractions into the correct form with the converter and additive part
        # normalised expected corrected fractions
        # determine expected amount of events in each bin

    def fraction_converter(self) -> None:
        """
        Determines the matrices required to transform the sub-template parameters
        """
        arrays = []
        additive = []
        count = 0
        for template in self.packed_templates.values():
            if template._num_templates == 1:
                arrays.append(np.zeros((1, self.num_fractions)))
                additive.append(np.ones((1, 1)))
            else:
                n_fractions = template._num_templates - 1
                array = np.identity(n_fractions)
                array = np.vstack([array, np.full((1, n_fractions), -1.)])
                count += n_fractions
                array = np.pad(array, ((0, 0), (count - n_fractions, self.num_fractions - count)), mode='constant')
                arrays.append(array)
                additive.append(np.vstack([np.zeros((n_fractions, 1)), np.ones((1, 1))]))
        print(arrays)
        print(additive)
        self.converter_matrix = np.vstack(arrays)
        self.converter_vector = np.vstack(additive)

    def add_constraint(self, name: str, value: float, sigma: float) -> None:
        self.constrain_indices.append(self._params.get_index(name))
        self.constrain_value = np.append(self.constrain_value, value)
        self.constrain_sigma = np.append(self.constrain_sigma, sigma)

    def x_expected(self) -> np.ndarray:
        yields = self._params.get_parameters_by_index(self.yield_indices)
        fractions_per_template = np.array([template.fractions() for template in self.templates.values()])
        return yields @ fractions_per_template

    def bin_pars(self) -> np.ndarray:
        return np.concatenate([template.get_bin_pars() for template in self.templates.values()])

    def _create_block_diag_inv_corr_mat(self) -> None:
        inv_corr_mats = [template.inv_corr_mat() for template in self.templates.values()]
        self._inv_corr = block_diag(*inv_corr_mats)

    def _constrain_term(self) -> float:
        constrain_pars = self._params.get_parameters_by_index(self.constrain_indices)
        chi2constrain = np.sum(((self.constrain_value - constrain_pars) / self.constrain_sigma) ** 2)
        assert isinstance(chi2constrain, float), type(chi2constrain)  # TODO: Remove this assertion for speed-up!
        return chi2constrain

    @jit
    def _gauss_term(self, bin_pars: np.ndarray) -> float:
        return bin_pars @ self._inv_corr @ bin_pars

    @jit
    def chi2(self, pars: np.ndarray) -> float:
        self._params.set_parameters(pars)

        yields = self._params.get_parameters_by_index(self.yield_indices).reshape(self.num_templates, 1)
        sub_pars = self._params.get_parameters_by_index(self.subfraction_indices).reshape(self.num_fractions, 1)
        bin_pars = self._params.get_parameters_by_slice(self.bin_par_slice)

        chi2 = self.chi2_compute(bin_pars, yields, sub_pars)
        return chi2

    @jit
    def chi2_compute(self, bin_pars: np.ndarray, yields: np.ndarray, sub_pars: np.ndarray) -> float:
        chi2data = np.sum(
            (self.expected_events_per_bin(bin_pars.reshape(self.shape), yields, sub_pars) - self.x_obs) ** 2
            / (2 * self.x_obs_errors ** 2)
        )

        assert isinstance(chi2data, float), type(chi2data)  # TODO: Remove this assertion for speed-up!

        chi2 = chi2data + self._gauss_term(bin_pars)  # + self._constrain_term()  # TODO: Check this
        return chi2

    def nll(self, pars: np.ndarray) -> float:
        self._params.set_parameters(pars)

        exp_evts_per_bin = self.x_expected()
        poisson_term = np.sum(exp_evts_per_bin - self.x_obs - xlogyx(self.x_obs, exp_evts_per_bin))
        assert isinstance(poisson_term, float), type(poisson_term)  # TODO: Remove this assertion for speed-up!

        nll = poisson_term + (self._gauss_term() + self._constrain_term()) / 2.
        return nll

    @staticmethod
    def _get_projection(ax: str, bc: np.ndarray) -> np.ndarray:
        # TODO: Is the mapping for x and y defined the wrong way around?
        x_to_i = {
            "x": 1,
            "y": 0
        }

        # TODO: use method provided by BinnedDistribution!
        return np.sum(bc, axis=x_to_i[ax])

    # TODO: Use histogram for plotting!
    def plot_stacked_on(self, ax, plot_all=False, **kwargs):
        plot_info = old_plotting.PlottingInfo(
            templates=self.templates,
            params=self._params,
            yield_indices=self.yield_indices,
            dimension=self._dim,
            projection_fct=self._get_projection,
            data=self.data,
            has_data=self.has_data
        )
        return old_plotting.plot_stacked_on(plot_info=plot_info, ax=ax, plot_all=plot_all, **kwargs)

    # TODO: Problematic; At the moment some sort of forward declaration is necessary for type hint...
    def create_nll(self) -> "CostFunction":
        return CostFunction(self, parameter_handler=self._params)


# TODO: Maybe relocate cost functions into separate sub-package;
#  however: CostFunction depends on ModelBuilder and vice versa ...
class AbstractTemplateCostFunction(ABC):
    """
    Abstract base class for all cost function to estimate yields using the template method.
    """

    def __init__(self, model: ModelBuilder, parameter_handler: ParameterHandler) -> None:
        self._model = model
        self._params = parameter_handler

    def x0(self) -> np.ndarray:
        """ Returns initial parameters of the model """
        return self._params.get_parameters()

    def param_names(self) -> List[str]:
        return self._params.get_parameter_names()

    @abstractmethod
    def __call__(self, x: np.ndarray) -> float:
        raise NotImplementedError(f"{self.__class__.__name__} is an abstract base class.")


class CostFunction(AbstractTemplateCostFunction):
    def __init__(self, model: ModelBuilder, parameter_handler: ParameterHandler) -> None:
        super().__init__(model=model, parameter_handler=parameter_handler)

    def __call__(self, x) -> float:
        return self._model.chi2(x)