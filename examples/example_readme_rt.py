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

"""
README example code for real-time connections:
"""

import causalchamber.lab as lab

# Open a real-time connection
chamber = lab.Chamber(chamber_id = 'lt-demo-x81a',
                      config='camera_fast',
                      credentials_file = '.credentials')

# Turn on red light source and take one measurement + image
chamber.set('red', 255)
df, images = chamber.measure(n=1)

# Plot the image
import matplotlib.pyplot as plt
plt.imshow(images[0])

# Start a new batch
batch = chamber.new_batch()

# Add instructions
batch.set('red', 128)
batch.measure(n=1)
batch.set('blue', 128)
batch.measure(n=1)
batch.set('pol_1', 90)
batch.measure(n=1)

# Submit them and receive the data
df, images = batch.submit()

# Plot the images
plt.figure(figsize=(9,3))
for i,im in enumerate(images):
    plt.subplot(1,3,i+1)
    plt.imshow(im)
