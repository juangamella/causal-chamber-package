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

from causalchamber.simulators import Simulator
import numpy as np

# --------------------------------------------------------------
# Simulators


class ModelF1(Simulator):
    """Simulator of the images produced by the light tunnel.

    The derivation of the simulator, including inputs, outputs and
    parameters, is described under Model F1 in Appendix IV.2.2 of the
    paper "Causal chambers as a real-world physical testbed for AI
    Methodology" (2025) by Gamella et al.

    Link for direct access:
    https://arxiv.org/pdf/2404.11341#page=32&zoom=100,57,670

    """

    inputs_names = [
        "red",
        "green",
        "blue",
        "pol_1",
        "pol_2",
    ]
    outputs_names = ["image"]

    def __init__(
        self,
        center_x,
        center_y,
        radius,
        offset,
        image_size,
    ):
        """
        Initialize the simulator by storing its parameters.
        """
        super(ModelF1, self).__init__()
        # Store the simulator's parameters
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.offset = offset
        self.image_size = image_size

    def parameters(self):
        """
        Return a dictionary with the simulator parameters and their values.
        """
        params = {
            "center_x": self.center_x,
            "center_y": self.center_y,
            "radius": self.radius,
            "offset": self.offset,
            "image_size": self.image_size,
        }
        return params

    def _simulate(
        self,
        red,
        green,
        blue,
        pol_1,
        pol_2,
        center_x,
        center_y,
        radius,
        offset,
        image_size,
    ):
        """Simulates a synthetic image using model_f1, generating a colored
        hexagon over a black background.

        Parameters
        ----------
        red : np.ndarray
            Brightness of the red LEDs of the light source.
        green : np.ndarray
            Brightness of the green LEDs of the light source.
        blue : np.ndarray
            Brightness of the blue LEDs of the light source.
        pol_1 : np.ndarray
            Angle of the first polarizer.
        pol_2 : np.ndarray
            Angle of the second polarizer.
        center_x : float
            X-coordinate of the hexagon's center in the image.
        center_y : float
            Y-coordinate of the hexagon's center in the image.
        radius : float
            Radius of the circumference encompassing the hexagon.
        offset : float
            Rotation of the hexagon in degrees.
        image_size : int
            Size of the synthetic image in pixels (i.e., image_size x image_size pixels).

        Returns
        -------
        np.ndarray
            Generated synthetic images with dimensions [n_images,
            image_size, image_size, 3], where n_images is the length of
            the inputs (i.e., red, green, blue, pol_1, pol_2).

        """
        N = len(red)
        images = np.ones((N, image_size, image_size, 3))
        pol_1, pol_2 = np.deg2rad(pol_1), np.deg2rad(pol_2)
        # Color
        malus_factor = np.cos(pol_1 - pol_2) ** 2
        red = red / 255 * malus_factor
        green = green / 255 * malus_factor
        blue = blue / 255 * malus_factor
        images[:, :, :, 0] *= red[:, np.newaxis, np.newaxis]
        images[:, :, :, 1] *= green[:, np.newaxis, np.newaxis]
        images[:, :, :, 2] *= blue[:, np.newaxis, np.newaxis]

        # Apply hexagon mask
        mask = hexagon_mask(center_x, center_y, radius, offset, image_size)
        images *= mask[np.newaxis, :, :, np.newaxis]
        return clip(images)


class ModelF2(Simulator):
    """
    Simulator of the images produced by the light tunnel.

    The derivation of the simulator, including inputs, outputs and
    parameters, is described under Model F2 in Appendix IV.2.2 of the
    paper "Causal chambers as a real-world physical testbed for AI
    Methodology" (2025) by Gamella et al.

    Link for direct access:
    https://arxiv.org/pdf/2404.11341#page=32&zoom=100,57,670
    """

    inputs_names = [
        "red",
        "green",
        "blue",
        "pol_1",
        "pol_2",
    ]
    outputs_names = ["image"]

    def __init__(
        self,
        S,
        w_r,
        w_g,
        w_b,
        exposure,
        center_x,
        center_y,
        radius,
        offset,
        image_size,
    ):
        """
        Initialize the simulator by storing its parameters.
        """
        super(ModelF2, self).__init__()
        # Store the simulator's parameters
        self.S = S
        self.w_r = w_r
        self.w_g = w_g
        self.w_b = w_b
        self.exposure = exposure
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.offset = offset
        self.image_size = image_size

    def parameters(self):
        """
        Return a dictionary with the simulator parameters and their values.
        """
        params = {
            "S": self.S,
            "w_r": self.w_r,
            "w_g": self.w_g,
            "w_b": self.w_b,
            "exposure": self.exposure,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "radius": self.radius,
            "offset": self.offset,
            "image_size": self.image_size,
        }
        return params

    def _simulate(
        self,
        red,
        green,
        blue,
        pol_1,
        pol_2,
        S,
        w_r,
        w_g,
        w_b,
        exposure,
        center_x,
        center_y,
        radius,
        offset,
        image_size,
    ):
        """Simulates a synthetic image using model_f2, generating a colored
        hexagon over a black background.

        Parameters
        ----------
        red : np.ndarray
            Brightness of the red LEDs of the light source.
        green : np.ndarray
            Brightness of the green LEDs of the light source.
        blue : np.ndarray
            Brightness of the blue LEDs of the light source.
        pol_1 : np.ndarray
            Angle of the first polarizer.
        pol_2 : np.ndarray
            Angle of the second polarizer.
        S : np.ndarray
            3x3 matrix modeling the sensor response to light of each color.
        w_r : float
            White-balance correction factor for the red channel.
        w_g : float
            White-balance correction factor for the green channel.
        w_b : float
            White-balance correction factor for the blue channel.
        exposure : float
            Exposure parameter affected by camera settings (aperture, shutter speed, ISO).
        center_x : float
            X-coordinate of the hexagon's center in the image.
        center_y : float
            Y-coordinate of the hexagon's center in the image.
        radius : float
            Radius of the circumference encompassing the hexagon.
        offset : float
            Rotation of the hexagon in degrees.
        image_size : int
            Size of the synthetic image in pixels (i.e., image_size x image_size pixels).

        Returns
        -------
        np.ndarray
            Generated synthetic images with dimensions [n_images,
            image_size, image_size, 3], where n_images is the length of
            the inputs (i.e., red, green, blue, pol_1, pol_2).

        """
        N = len(red)
        images = np.ones((N, image_size, image_size, 3))
        # Transform parameters
        pol_1, pol_2 = np.deg2rad(pol_1), np.deg2rad(pol_2)
        r = np.atleast_1d(red / 255)
        g = np.atleast_1d(green / 255)
        b = np.atleast_1d(blue / 255)

        # Ccalculate color
        malus_factor = np.cos(pol_1 - pol_2) ** 2
        W = np.diag([w_r, w_g, w_b])
        color = exposure * W @ S @ np.array([r, g, b]) * malus_factor

        # Produce the image
        images[:, :, :, 0] *= color[0, :, np.newaxis, np.newaxis]
        images[:, :, :, 1] *= color[1, :, np.newaxis, np.newaxis]
        images[:, :, :, 2] *= color[2, :, np.newaxis, np.newaxis]

        # Apply hexagon mask
        mask = hexagon_mask(center_x, center_y, radius, offset, image_size)
        images *= mask[np.newaxis, :, :, np.newaxis]
        return clip(images)



class ModelF3(Simulator):
    """
    Simulator of the images produced by the light tunnel.

    The derivation of the simulator, including inputs, outputs and
    parameters, is described under Model F1 in Appendix IV.2.2 of the
    paper "Causal chambers as a real-world physical testbed for AI
    Methodology" (2025) by Gamella et al.

    Link for direct access:
    https://arxiv.org/pdf/2404.11341#page=32&zoom=100,57,670
    """

    inputs_names = [
        "red",
        "green",
        "blue",
        "pol_1",
        "pol_2",
    ]
    outputs_names = ["image"]

    def __init__(
        self,
        S,
        w_r,
        w_g,
        w_b,
        exposure,
        Tp,
        Tc,
        center_x,
        center_y,
        radius,
        offset,
        image_size,
    ):
        """
        Initialize the simulator by storing its parameters.
        """
        super(ModelF3, self).__init__()
        # Store the simulator's parameters
        self.S = S
        self.w_r = w_r
        self.w_g = w_g
        self.w_b = w_b
        self.exposure = exposure
        self.Tp = Tp
        self.Tc = Tc
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.offset = offset
        self.image_size = image_size

    def parameters(self):
        """
        Return a dictionary with the simulator parameters and their values.
        """
        params = {
            "S": self.S,
            "w_r": self.w_r,
            "w_g": self.w_g,
            "w_b": self.w_b,
            "exposure": self.exposure,
            "Tp": self.Tp,
            "Tc": self.Tc,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "radius": self.radius,
            "offset": self.offset,
            "image_size": self.image_size,
        }
        return params

    def _simulate(
        self,
        red,
        green,
        blue,
        pol_1,
        pol_2,
        S,
        w_r,
        w_g,
        w_b,
        exposure,
        Tp,
        Tc,
        center_x,
        center_y,
        radius,
        offset,
        image_size,
    ):
        """Simulates a synthetic image using model_f3, generating a colored
        hexagon over a black background.

        Parameters
        ----------
        red : np.ndarray
            Brightness of the red LEDs of the light source.
        green : np.ndarray
            Brightness of the green LEDs of the light source.
        blue : np.ndarray
            Brightness of the blue LEDs of the light source.
        pol_1 : np.ndarray
            Angle of the first polarizer.
        pol_2 : np.ndarray
            Angle of the second polarizer.
        S : np.ndarray
            3x3 matrix modeling the sensor response to light of each color.
        w_r : float
            White-balance correction factor for the red channel.
        w_g : float
            White-balance correction factor for the green channel.
        w_b : float
            White-balance correction factor for the blue channel.
        exposure : float
            Exposure parameter affected by camera settings (aperture, shutter speed, ISO).
        Tp : np.ndarray
            Transmission rates for each color when the polarizers are aligned.
        Tc : np.ndarray
            Transmission rates for each color when the polarizers are perpendicular.
        center_x : float
            X-coordinate of the hexagon's center in the image.
        center_y : float
            Y-coordinate of the hexagon's center in the image.
        radius : float
            Radius of the circumference encompassing the hexagon.
        offset : float
            Rotation of the hexagon in degrees.
        image_size : int
            Size of the synthetic image in pixels (i.e., image_size x image_size pixels).

        Returns
        -------
        np.ndarray
            Generated synthetic images with dimensions [n_images,
            image_size, image_size, 3], where n_images is the length of
            the inputs (i.e., red, green, blue, pol_1, pol_2).

        """
        N = len(red)
        images = np.ones((N, image_size, image_size, 3))
        # Transform parameters
        pol_1, pol_2 = np.deg2rad(pol_1), np.deg2rad(pol_2)
        r = np.atleast_1d(red / 255)
        g = np.atleast_1d(green / 255)
        b = np.atleast_1d(blue / 255)

        # Ccalculate color
        malus_factor = (Tp - Tc) * np.cos(pol_1 - pol_2) ** 2 + Tc
        W = np.diag([w_r, w_g, w_b])
        color = exposure * W @ S @ np.array([r, g, b]) * malus_factor

        # Produce the image
        images[:, :, :, 0] *= color[0, :, np.newaxis, np.newaxis]
        images[:, :, :, 1] *= color[1, :, np.newaxis, np.newaxis]
        images[:, :, :, 2] *= color[2, :, np.newaxis, np.newaxis]

        # Apply hexagon mask
        mask = hexagon_mask(center_x, center_y, radius, offset, image_size)
        images *= mask[np.newaxis, :, :, np.newaxis]
        return clip(images)


# --------------------------------------------------------------------
# Auxiliary functions


def clip(images):
    """Clip the pixels of the image so they are always in the range [0,1],
    e.g., 1.2 becomes 1, and -0.1 becomes 0.

    """
    images = np.maximum(images, 0)
    images = np.minimum(images, 1)
    return images


def hexagon_mask(center_x, center_y, radius, offset, image_size):
    """Produce the hexagon mask given its center, radius, (angle) offset
    and the size (in pixels) of the image.

    """
    mask = np.zeros((image_size, image_size))
    image_points = coord_grid(image_size)
    vertices = hexagon_vertices(center_x, center_y, radius, offset) * image_size
    # Compute cross products for a segment and all points
    cross_prods = []
    for i, vertex in enumerate(vertices):
        segment = vertex - vertices[(i + 1) % len(vertices)]
        vertex_to_points = image_points - vertex
        cross = np.cross(vertex_to_points, segment)
        cross_prods.append(cross)
    cross_prods = np.array(cross_prods)
    all_neg = (cross_prods <= 0).all(axis=0)
    all_pos = (cross_prods > 0).all(axis=0)
    mask = np.logical_or(all_neg, all_pos)
    return mask


def hexagon_vertices(center_x, center_y, radius, offset):
    """Given the center, radius and (angle) offset of the hexagon,
    compute the location of its six vertices.

    """
    vertices = []
    for angle in np.arange(0, 2 * np.pi, np.pi / 3):
        x = center_x + radius * np.cos(angle + offset)
        y = center_y + radius * np.sin(angle + offset)
        vertices.append([x, y])
    return np.array(vertices)


def coord_grid(image_size):
    """
    Make a coordinate grid (in pixels) given the image size
    """
    X = np.tile(np.arange(image_size), (image_size, 1))
    Y = X.T[::-1, :]
    grid = np.array([X, Y])
    return np.transpose(grid, (1, 2, 0))
