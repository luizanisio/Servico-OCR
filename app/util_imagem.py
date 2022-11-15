# -*- coding: utf-8 -*-
#!/usr/bin/env python3

from PIL import Image
import numpy as np

# 0 = PB, 1 Cinza, 2 Colorido
def cor_imagem(imagem, converter = True):
  # 12/11/2022 - inspirado em:  
  # https://stackoverflow.com/questions/68352065/how-to-check-whether-a-jpeg-image-is-color-or-grayscale-using-only-python-pil  
  ### splitting b,g,r channels
  r,g,b=imagem.split()

  ### PIL to numpy conversion:
  r = np.array(r)
  g = np.array(g)
  b = np.array(b)

  ### getting differences between (b,g), (r,g), (b,r) channel pixels
  r_g=np.count_nonzero(abs(r-g))
  r_b=np.count_nonzero(abs(r-b))
  g_b=np.count_nonzero(abs(g-b))

  ### sum of differences
  diff_sum=float(r_g+r_b+g_b)

  ### get image size:
  width, height = imagem.size

  ### get total pixels on image:
  totalPixels = width * height

  ### finding ratio of diff_sum with respect to size of image
  ratio = diff_sum/totalPixels

  msg = f"Image RGB Ratio is: {ratio} ==>"
  
  if ratio>0.005:
     print(f"{msg} image is color", flush = True)
     if converter:
        return imagem
     return 2
  elif ratio>0:
     print(f"{msg} image is greyscale", flush = True)
     if converter:
        return imagem.convert('LA')
     return 1
  else:
     print(f"{msg} image is black and white", flush = True)
     if converter:
        return imagem.convert('LA', colors = 2)
     return 0



