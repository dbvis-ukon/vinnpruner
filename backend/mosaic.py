
import io
import matplotlib
matplotlib.use('SVG')   # generate postscript output by default
import matplotlib.pyplot as plt
import numpy as np
import uuid
import math
import base64
from functools import partial
from multiprocessing import Pool
from time import time
from PIL import Image

class Settings:
    def __init__(self):
        self.maxwidth = 750
        self.maxHeight = 100
        self.hspacing = 1
        self.vspacing = 0
        self.scale = 1
        self.zeroed_color = [196, 64, 64, 255]
        self.nonzeroed_color = [225, 225, 225, 255]
        self.filler_color = [225, 225, 255, 0]
    

def transform_mt(data, settings, layer_type, requested_width, threads=8):
    start_time = time()
    mosaics = []
    img_height = 0
    img_width = 0
    if len(data) > threads * 15:
        print(f"using multiprocessing to generate mosaic with {threads} processes")
        splits = np.array_split(data, threads)
        with Pool(processes=threads) as pool:
            result = pool.map(partial(transform_range, settings, layer_type, requested_width), splits)
            end_time = time()
            seconds_elapsed = end_time - start_time
            print(f"done rendering, took {round(seconds_elapsed, 3)} seconds")
        for (split, height, width) in result:
            mosaics += split
        (_, height, width) = result[0]
        img_width = width
        img_height = height
    else:
        print("using single threading to generate mosaic")
        mosaics, img_height, img_width = transform_range(settings, layer_type, requested_width, data)
        end_time = time()
        seconds_elapsed = end_time - start_time
        print(f"done rendering, took {round(seconds_elapsed, 3)} seconds")
    
    chunks_per_slice = None
    if layer_type == "conv2d":
        chunk_width = data.shape[len(data.shape) - 1] + settings.vspacing
        chunks_per_slice = data.shape[1]
    elif layer_type == "linear":
        chunk_width = 1
        chunks_per_slice = data.shape[1]
    return mosaics, img_height, img_width, chunk_width, chunks_per_slice


def transform_range(settings, layer_type, requested_width, data):
    imgs = []
    colors = [settings.zeroed_color, settings.nonzeroed_color]
    img_height = 0
    for data_row in data:
        if layer_type == "conv2d":
            buf = transform_conv2d(data_row, settings, colors)
            (img, height) = generate_image_pil(buf, 1, 1, requested_width, debug=False, debugFileName=f"debug/{uuid.uuid4()}.png")
            if img_height == 0:
                img_height = height
            imgs.append(base64.encodebytes(img.getvalue()).decode('ascii'))
        elif layer_type == "linear":
            buf = transform_linear(data_row, settings, colors)
            (img, height) = generate_image_pil(buf, 1, 1, requested_width, debug=False, debugFileName=f"debug/{uuid.uuid4()}.png")
            if img_height == 0:
                img_height = height
            imgs.append(base64.encodebytes(img.getvalue()).decode('ascii'))
    img_width = 0
    if len(buf) > 0:
        img_width = len(buf[0])
    return imgs, img_height, img_width


def transform(data_row, settings, layer_type, requested_width):
    img = io.BytesIO()
    colors = [settings.zeroed_color, settings.nonzeroed_color]
    if layer_type == "conv2d":
        buf = transform_conv2d(data_row, settings, colors)
        img = generate_image_pil(buf, 1, 1, requested_width, debug=False, debugFileName=f"debug/{uuid.uuid4()}.png")
        #img = generate_image(buf, data_row.shape[0], settings.scale, debug=False, debugFileName=f"debug/{uuid.uuid4()}.png")
    elif layer_type == "linear":
        buf = transform_linear(data_row, settings, colors)
        img = generate_image_pil(buf, 1, 1, requested_width, debug=False, debugFileName=f"debug/{uuid.uuid4()}.png")
    return img


def transform_linear(data_row, settings, colors):
    buf = []
    for pixel in data_row:
        for _ in range (0, settings.scale):
            if pixel == 0:
                buf.append(colors[0])
            else:
                buf.append(colors[1])
    out = []
    for _ in range(0, settings.scale):
        out.append(buf)

    if settings.vspacing > 0:
        for _ in range(settings.vspacing):
            buf.append(np.tile(np.array(settings.filler_color), (len(buf[0]),1)).tolist())
    return out


def transform_conv2d(data_row, settings, colors):
    buf = []
    img_dimensions = data_row.shape[1]
    for imd in range(0, img_dimensions):
        img_row = []
        for col in data_row:
            for pixel in col[imd]:
                for _ in range(0, settings.scale):
                    if pixel == 0:
                        img_row.append(colors[0])
                    else:
                        img_row.append(colors[1])
            for _ in range(0, settings.hspacing):
                #img_row.append([0, 0, 0, 0])
                img_row.append(settings.filler_color)
        for _ in range(0, settings.scale):
            if settings.hspacing > 0:
                buf.append(img_row[:-settings.hspacing])
            else:
                buf.append(img_row)
    if settings.vspacing > 0:
        for _ in range(settings.vspacing):
            buf.append(np.tile(np.array(settings.filler_color), (len(buf[0]),1)).tolist())
    return buf


def generate_image(buf, size_w, size_h, debug=False, debugFileName="debug/test.svg"):
    print("generating image")        
    fig, ax = plt.subplots()
    ax.axis('off')
    fig.set_size_inches(size_w, size_h)
    #plt.figure(figsize=(40, 2))
    plt.axis('off')
    plt.imshow(buf)
    plt.tight_layout(w_pad=0, h_pad=0)
    in_mem = io.BytesIO()
    plt.savefig(in_mem, format="png", bbox_inches='tight', pad_inches=0, transparent="True")
    if debug:
        plt.savefig(debugFileName, bbox_inches='tight', pad_inches=0, transparent="True")
    plt.close()
    in_mem.seek(0)
    return in_mem


def generate_image_pil(buf, scale_w, scale_h, requested_width=None, debug=False, debugFileName="debug/test.png"):
    npa = np.array(buf).astype(np.uint8)
    im = Image.fromarray(npa)

    # scale image to reqwuested width
    if requested_width != None:
        scale_ratio = requested_width / im.width
        im = im.resize((math.ceil(im.width * scale_ratio), math.ceil(im.height * scale_ratio)), resample=Image.NEAREST)

    # upscale image if requested
    if scale_w > 1 or scale_h > 1:
      (width, height) = (im.width * scale_w, im.height * scale_h)
      im = im.resize((width, height), resample=Image.NEAREST)
    if debug:
        im.save(debugFileName)

    # render as png to support transparency for spacers
    img_bytes = io.BytesIO()
    im.save(img_bytes, format="png")
    img_bytes.seek(0)
    return (img_bytes, im.height)


def transform_linear_full(data, settings, colors, requested_width=None):
    buf = []
    for data_row in data:
        buf = buf + transform_linear(data_row, settings, colors)
        #buf.append(np.tile(np.array([255, 255, 255, 0]), (len(buf[0]),1)).tolist())
    return generate_image_pil(buf, 2, 2, requested_width, debug=True)

def transform_conv2d_full(data, settings, colors, requested_width=None):
    buf = []
    start_time = time()
    for data_row in data:
        buf = buf + transform_conv2d(data_row, settings, colors)
        #buf.append(np.tile(np.array([255, 255, 255, 0]), (len(buf[0]),1)).tolist())
    #generate_image_pil(buf, data[0].shape[0], settings.scale * data.shape[0])
    end_time = time()
    seconds_elapsed = end_time - start_time
    print(f"done transforming, took {round(seconds_elapsed, 3)} seconds")
    return generate_image_pil(buf, 2, 2, requested_width, debug=True)