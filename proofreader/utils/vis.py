import numpy as np
from skimage.transform import resize
from skimage import color
import matplotlib.pyplot as plt
import IPython
import math


def scale_data(vol, seg, size=180):
    length = vol.shape[0]
    vol = resize(vol, (length, size, size))
    seg = resize(seg, (length, size, size), order=0,
                 preserve_range=True, anti_aliasing=False)

    return (vol, seg)


def label_data(vol, seg):
    length = vol.shape[0]
    size = vol.shape[1]
    # reshape for labeling
    seg = np.reshape(seg, (size, length*size))
    vol = np.reshape(vol, (size, length*size))
    # label
    labeled = color.label2rgb(seg, vol, alpha=0.1, bg_label=-1)
    # shape back
    labeled = np.reshape(labeled, (length, size, size, 3))

    return labeled


def view_volume(volume, display, fig_size=6.5):
    length = volume.shape[0]

    # set up
    fig = plt.figure()
    fig.set_size_inches(fig_size, fig_size)
    axes = fig.add_subplot()
    hfig = display(fig, display_id=True)

    # display
    for i in range(length):
        axes.imshow(volume[i], cmap='gray', interpolation='none',
                    filternorm=False, resample=False)
        fig.canvas.draw()
        hfig.update(fig)
        if i != length-1:
            plt.cla()
    # clean up
    IPython.display.clear_output()


def view_affinity(affinity, i=0, fig_size=20):
    plt.rcParams['image.interpolation'] = 'nearest'
    num_aff = affinity.shape[0]
    fig, axarr = plt.subplots(1, num_aff)
    fig.set_size_inches(fig_size*num_aff, fig_size)
    for a in range(num_aff):
        axarr[a].imshow(affinity[a][i], cmap='gray')
        axarr[a].imshow(affinity[a][i], cmap='gray')
        axarr[a].imshow(affinity[a][i], cmap='gray')
    plt.show()


def view_segmentation(seg, i=0, fig_size=10):
    fig = plt.figure()
    fig.set_size_inches(fig_size, fig_size)
    colored = color.label2rgb(seg[i], alpha=1, bg_label=0)
    plt.imshow(colored)
    plt.show()


def grid_volume(vol, sz=100):
    num_sl = vol.shape[0]
    r = math.ceil(math.sqrt(num_sl))
    fig, axarr = plt.subplots(r, r)
    fig.set_size_inches(sz, sz)
    for i in range(r):
        for j in range(r):
            cur = (i*r)+j
            if cur < num_sl:
                axarr[i, j].imshow(vol[cur], cmap='gray')
                axarr[i, j].set_title(cur)
    plt.axis('off')
    plt.show()