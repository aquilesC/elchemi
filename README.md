# Live-fft-Imaging
Scripts that use threading to simultaneously capture images, analyze images and plot analyzed images.

Extract dominant frequency live script:
Takes a set number of images, after 100 images the dominant frequency component in these images will be plotted live, based on the last 100 images.

Live projection of fft analyzed images script:
Takes a set number of images of a sample which is perturbed by a sinusoidal voltage. After 100 images, the dominant frequency present in the images of the sample is determined (should be the frequency of the perturbing sinusoidal voltage). Then, 6 cycles of images per sine are used to fft analyze the images and plot them. Complex array of fft analyzed images is saved.

dwfconstants_code script:
Is used in both scripts to import the DWF constants for the waveform generator.
