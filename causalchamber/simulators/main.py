# MIT License

# Copyright (c) 2025 Juan L. Gamella

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


class Simulator:
    """The base class for the causal chamber simulators.

    Inheriting classes redefine the class attributes `inputs_names`
    and `outputs_names`, and the functions `__init__` and `_simulate`.

    """

    inputs_names = []
    outputs_names = []

    def __init__(self):
        """
        Initializes the Simulator instance. Re-defined by inheriting classes.
        """
        pass

    def simulate_from_inputs(self, df):
        """Runs the simulation using inputs from a given DataFrame. Passing a
        dataframe that doesn't define all inputs as columns will raise
        an error. Additional columns are ignored.

        Parameters
        ----------
        df : pandas.DataFrameA
            A pandas DataFrame containing the inputs in columns named
            as in `self.inputs_names`.

        Returns
        -------
            The result of the `_simulate` method, which should be
            implemented by subclasses.

        """
        # Take inputs from dataframe
        inputs = dict((k, v.values) for k, v in dict(df[self.inputs_names]).items())
        return self._simulate(**inputs, **self.parameters())

    def parameters(self):
        """
        Returns a dictionary with the simulator's parameters and their values.
        """
        return {}

    def _simulate(self):
        """
        A placeholder method for the simulation logic, to be implemented in subclasses.

        Raises
        ------
        NotImplementedError
            If not implemented in a subclass.
        """
        raise NotImplementedError()
