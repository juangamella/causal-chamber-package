# MIT License

# Copyright (c) 2025 Juan L. Gamella, Causal Chamber GmbH

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


import matplotlib.pyplot as plt

colors = ["#ffb000", "#fe6100", "#dc267f", "#785ef0", "#648fff"]

def plot_wt(df):
    """
    Make a plot of the fan loads, speeds, currents and barometer readings of the wind tunnel.
    """
    # Create figure with 3 subplots, adjust height ratios
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 6), 
                                          gridspec_kw={'height_ratios': [1, 1, 1]},
                                          sharex=True)
    
    # Time
    t = df.timestamp - df.timestamp.iloc[0]
    
    # First plot
    ax1.plot(t, df.load_in, color=colors[4], label='load_in')
    # ax1.plot(df.load_out, color='gray', label='load_out', linestyle='--')
    ax1.plot(t, df.rpm_in / 3000, color = colors[1], label="rpm_in (normalized)")
    ax1.plot(t, df.rpm_out / 3000, color = colors[0], label="rpm_out (normalized)")
    ax1.set_ylabel("load / RPM\n(normalized)", rotation=0, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Second plot
    ax2.plot(t, df.current_in, label="current_in", color = colors[1])
    ax2.plot(t, df.current_out, label="current_out", color = colors[0])
    ax2.legend(title='Fan current')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylabel('Drawn current\n(amperes)', rotation=0, ha='right')
    
    # Third plot
    pressure_vars = ['pressure_upwind', 'pressure_downwind', 'pressure_intake', 'pressure_ambient']
    [ax3.plot(t, df[var], label=var, color=colors[i]) for i,var in enumerate(pressure_vars)]
    ax3.legend(title='Barometer')
    ax3.grid(True, alpha=0.3)
    ax3.set_ylabel('Air pressure\n(pascals)', rotation=0, ha='right')
    
    # Only label x-axis on bottom plot
    ax3.set_xlabel('Time (seconds)')
    
    plt.savefig('examples/package_queue_plots.png', bbox_inches='tight', dpi=200)

