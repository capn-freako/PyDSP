#! /usr/bin/env python

"""
a tool for exploring DSP concepts

David Banas <capn.freako@gmail.com>
11 June 2011

This Python script provides a means for exploring DSP concepts, using the
GUI and modeling tools available in the Enthought Tool Suite.

Copyright (c) 2011 by David Banas; All rights reserved World wide.
"""

from enthought.traits.api \
    import HasTraits, Array, Range, Float, Enum, Property, String, List, cached_property
from enthought.traits.ui.api import View, Item, VSplit, Group, VGroup, HGroup, Label, Action, Handler, DefaultOverride
from enthought.chaco.chaco_plot_editor import ChacoPlotItem
from numpy import arange, real, concatenate, angle, sign, sin, pi, array, float, zeros
from numpy.fft import ifft
from numpy.random import random
from scipy.signal import lfilter, firwin, iirdesign, iirfilter, freqz
import re

# Model Parameters - Modify these to customize the simulation.
Npts = 1024    # number of vector points
Ntaps_max = 6

# Model Proper - Don't change anything below this line.
class MyHandler(Handler):

    def do_copy_coeffs(self, info):
        a = info.object.a
        b = info.object.b
        usr_a = zeros((1, Ntaps_max))
        usr_b = zeros((1, Ntaps_max))
        for i in range(len(a)):
            usr_a[0][i] = a[i]
        for i in range(len(b)):
            usr_b[0][i] = b[i]
        info.object.usr_a = usr_a
        info.object.usr_b = usr_b

class PyDSP (HasTraits):
    sample_rate_value = Enum("1", "2", "5", "10", "20", "50", "100", "200", "500")
    sample_rate_units = Enum("Hz", "kHz", "MHz", "GHz")
    sample_rate = Property(Float, depends_on=['sample_rate_value', 'sample_rate_units'])
    t = Property(Array, depends_on=['sample_rate'])
    input_type = Enum("sine", "square", "triangle", "chirp", "noise", "impulse")
    input_freq = Range(low=1, high=1000, value=1)
    input_freq_units = Enum("Hz", "kHz", "MHz", "GHz")
    input_span = Range(low=1, high=1000, value=500)
    input_span_units = Enum("Hz", "kHz", "MHz", "GHz")
    x = Property(Array, depends_on=['sample_rate', 'input_type', 'input_freq', 'input_freq_units', 'input_span', 'input_span_units', 't'])
    Ntaps = Range(low=1, high=Ntaps_max, value=3)
    filter_type = Enum("FIR", "IIR", "custom")
    filter_cutoff = Range(low=1, high=1000, value=500)
    filter_cutoff_units = Enum("Hz", "kHz", "MHz", "GHz")
    a = Property(Array, depends_on=['Ntaps', 'filter_type', 'filter_cutoff', 'filter_cutoff_units', 'sample_rate', 'usr_a', 'usr_b'])
    b = array([1]) # Will be set by 'a' handler, upon change in dependencies.
    a_str = String("1", font='Courier')
    b_str = String("1")
    usr_a = Array(float, (1,Ntaps_max), [[1] + [0 for i in range(Ntaps_max-1)]])
    usr_b = Array(float, (1,Ntaps_max), [[1] + [0 for i in range(Ntaps_max-1)]])
    H = Property(Array, depends_on=['a'])
    H_mag = Property(Array, depends_on=['H'])
    H_phase = Property(Array, depends_on=['H'])
    h = Property(Array, depends_on=['H'])
    f = Property(Array, depends_on=['sample_rate'])
    y = Property(Array, depends_on=['a', 'x'])
    plot_type = Enum("line", "scatter")
    plot_type2 = Enum("line", "scatter")
    ident = String('PyDSP v0.2 - a digital filter design tool, written in Python\n\n \
    David Banas\n \
    July 9, 2011\n\n \
    Copyright (c) 2011 David Banas; All rights reserved World wide.')

    # Set the default values of the independent variables.
    def _sample_rate_units_default(self):
        """ Default handler for angular frequency Trait Array. """
        return "MHz"

    def _input_freq_units_default(self):
        return "kHz"

    def _filter_cutoff_default(self):
        return 100

    def _filter_cutoff_units_default(self):
        return "kHz"

    # Define dependent variables.
    @cached_property
    def _get_sample_rate(self):
        """Recalculate when a trait the property depends on changes."""
        val = float(self.sample_rate_value)
        units = self.sample_rate_units
        if (units == "Hz"):
            return val
        elif (units == "kHz"):
            return val * 1e3
        elif (units == "MHz"):
            return val * 1e6
        else:
            return val * 1e9

    @cached_property
    def _get_t(self):
        t = arange(Npts) / self.sample_rate
        return t

    @cached_property
    def _get_f(self):
        f = arange(Npts) * (self.sample_rate/(2*Npts))
        return f

    @cached_property
    def _get_x(self):
        # Combine value/units from GUI to form actual frequency.
        val = self.input_freq
        units = self.input_freq_units
        if (units == "Hz"):
            sig_freq = val
        elif (units == "kHz"):
            sig_freq = val * 1e3
        elif (units == "MHz"):
            sig_freq = val * 1e6
        else:
            sig_freq = val * 1e9

        # Combine value/units from GUI to form actual span (chirp only).
        val = self.input_span
        units = self.input_span_units
        if (units == "Hz"):
            sig_span = val
        elif (units == "kHz"):
            sig_span = val * 1e3
        elif (units == "MHz"):
            sig_span = val * 1e6
        else:
            sig_span = val * 1e9

        # Generate the signal.
        square_wave = sign(sin(2*pi*sig_freq*self.t))
        sig_type = self.input_type
        if (sig_type == "sine"):
            return sin(2*pi*sig_freq*self.t)
        elif (sig_type == "square"):
            return square_wave
        elif (sig_type == "triangle"):
            triangle_wave = array([sum(square_wave[0:i+1]) for i in range(Npts)])
            triangle_wave = triangle_wave * 2 / (max(triangle_wave)-min(triangle_wave))
            return triangle_wave + (1 - max(triangle_wave))
        elif (sig_type == "chirp"):
            freqs = array([sig_freq-sig_span/2+i*sig_span/Npts for i in range(Npts)])
            return sin(self.t*(2*pi*freqs))
        elif (sig_type == "noise"):
            return array([random()*2-1 for i in range(Npts)])
        else: # "impulse"
            return array([0, 1] + [0 for i in range(Npts-2)])

    @cached_property
    def _get_a(self):
        # Combine value/units from GUI to form actual cutoff frequency.
        val = self.filter_cutoff
        units = self.filter_cutoff_units
        if (units == "Hz"):
            fc = val
        elif (units == "kHz"):
            fc = val * 1e3
        elif (units == "MHz"):
            fc = val * 1e6
        else:
            fc = val * 1e9

        # Generate the filter coefficients.
        if (self.filter_type == "FIR"):
            w = fc/(self.sample_rate/2)
            b = firwin(self.Ntaps, w)
            a = [1]
        elif (self.filter_type == "IIR"):
            (b, a) = iirfilter(self.Ntaps - 1, fc/(self.sample_rate/2), btype='lowpass')
        else:
            a = self.usr_a[0]
            b = self.usr_b[0]
        if (self.filter_type != "custom"):
            self.a_str = reduce(lambda string, item: string + "%+06.3f  "%item, a, "")
            self.b_str = reduce(lambda string, item: string + "%+06.3f  "%item, b, "")
        self.b = b
        return a

    @cached_property
    def _get_h(self):
        x = array([0, 1] + [0 for i in range(Npts-2)])
        a = self.a
        b = self.b
        return lfilter(b, a, x)

    @cached_property
    def _get_H(self):
        (w, H) = freqz(self.b, self.a, worN=Npts)
        return H

    @cached_property
    def _get_H_mag(self):
        H = self.H
        H[0] = 0      # Kill the d.c. component, or it will swamp everything.
        return abs(H)

    @cached_property
    def _get_H_phase(self):
        H = self.H
        return angle(H, deg=True)

    @cached_property
    def _get_y(self):
        x = self.x
        a = self.a
        b = self.b
        return lfilter(b, a, x)

copy_coeffs = Action(name="CopyCoefficients", action="do_copy_coeffs")
    
# Main window definition
view1 = View(
  HGroup(
    VGroup(
      HGroup(
          Item(name='sample_rate_value', label='Sample rate'),
          Item(name='sample_rate_units', show_label=False),
          Item(name='input_type'),
      ),
      HGroup(
          Item(name='input_freq', enabled_when="input_type != 'impulse'"),
          Item(name='input_freq_units', show_label=False, enabled_when="input_type != 'impulse'"),
          Item(name='input_span', enabled_when="input_type == 'chirp'"),
          Item(name='input_span_units', show_label=False, enabled_when="input_type == 'chirp'"),
      ),
#          Item(name='plot_type', show_label=False),
      ChacoPlotItem("t", "x",
        type_trait="plot_type",
        resizable=True,
        x_label="time (s)",
        y_label="x",
        x_bounds=(0,float(Npts)),
        x_auto=True,
        y_bounds=(-1.1, 1.1),
        y_auto=False,
        color="blue",
        bgcolor="white",
        border_visible=True,
        border_width=1,
        title='Input Signal vs. Time',
        padding_bg_color="lightgray", show_label=False
      ),
      ChacoPlotItem("t", "y",
        type_trait="plot_type",
        resizable=True,
        x_label="time (s)",
        y_label="y",
        x_bounds=(0,float(Npts)),
        x_auto=True,
        y_bounds=(-1.1, 1.1),
        y_auto=True,
        color="blue",
        bgcolor="white",
        border_visible=True,
        border_width=1,
        title='Output Signal vs. Time',
        padding_bg_color="lightgray", show_label=False
      ),
      Item('ident', style='readonly', show_label=False),
    ),
    VGroup(
      HGroup(
          Item(name='Ntaps', editor=DefaultOverride(mode='spinner')),
          Item(name='filter_type'),
          Item(name='filter_cutoff'),
          Item(name='filter_cutoff_units', show_label=False),
      ),
#         Item(label='Filter Response Functions'),
      Item(name='a_str', label='a', width=0.5, style='readonly'),
      Item(name='b_str', label='b', width=0.5, style='readonly'),
      Item(name='usr_a', format_str="%+06.3f"),
      Item(name='usr_b', format_str="%+06.3f"),
#          Item(name='plot_type2', show_label=False),
      ChacoPlotItem("t", "h",
        type_trait="plot_type2",
        resizable=True,
        x_label="time (s)",
        y_label="h",
        x_bounds=(0,0.5),
        x_auto=True,
        y_bounds=(-2000,4000),
        y_auto=True,
        color="blue",
        bgcolor="white",
        border_visible=True,
        border_width=1,
        title='Impulse Response vs. Time',
        padding_bg_color="lightgray", show_label=False
      ),
      ChacoPlotItem("f", "H_mag",
        type_trait="plot_type2",
        resizable=True,
        x_label="frequency (Hz)",
        y_label="|H|",
        x_bounds=(0,0.5),
        x_auto=True,
        y_bounds=(-2000,4000),
        y_auto=True,
        color="blue",
        bgcolor="white",
        border_visible=True,
        border_width=1,
        title='Transfer Function Magnitude vs. Frequency',
        padding_bg_color="lightgray", show_label=False
      ),
      ChacoPlotItem("f", "H_phase",
        type_trait="plot_type2",
        resizable=True,
        x_label="frequency (Hz)",
        y_label="<H (deg.)",
        x_bounds=(0,0.5),
        x_auto=True,
        y_bounds=(-2000,4000),
        y_auto=True,
        color="blue",
        bgcolor="white",
        border_visible=True,
        border_width=1,
        title='Transfer Function Phase vs. Frequency',
        padding_bg_color="lightgray", show_label=False
      ),
    ),
  ),
  resizable = True,
  handler = MyHandler(),
#  buttons = ["CopyCoefficients", "OK"],
  buttons = [copy_coeffs, "OK"],
  title='DSP Filter Tool',
  width=1200, height=900
)

if __name__ == '__main__':
    viewer = PyDSP()
    viewer.configure_traits(view=view1)
