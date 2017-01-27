import matplotlib.pyplot as plt
import numpy as np
from itertools import product
import pandas as pd

import sys
sys.path.insert(0, "../../../Modules/") # generate-categories/Modules
import gc


from gc import utils
import models.CopyTweak
from gc import CopyTweak
from gc.models import CopyTweak, Packer, ConjugateJK13
import gc.utils as utils

pd.set_option('precision', 3)
np.set_printoptions(precision = 3)

 # 72 73 74 75 76 77 78 79 80
 # 63 64 65 66 67 68 69 70 71
 # 54 55 56 57 58 59 60 61 62
 # 45 46 47 48 49 50 51 52 53
 # 36 37 38 39 40 41 42 43 44
 # 27 28 29 30 31 32 33 34 35
 # 18 19 20 21 22 23 24 25 26
 #  9 10 11 12 13 14 15 16 17
 #  0  1  2  3  4  5  6  7  8
vals = np.linspace(-1, 1, 9).tolist()
stimuli = np.fliplr(np.array(list(product(vals, vals))))


alphas =  [30, 32, 48, 50]
alphas =  [12, 30, 14, 32]
betas = []

models = [
    [CopyTweak, dict(
        specificity = 9.4486327043,
        within_pref = 17.0316650379,
        tolerance = 0.403108523886,
        determinism = 10.07038770338,
        )],
    [Packer, dict(
        specificity = 0.562922970884,
        between = 1.76500997943,
        within = 1.55628620461,
        determinism = 1.99990124401,
        )],
    [ConjugateJK13, dict(
        category_mean_bias = 0.0167065365661,
        category_variance_bias = 1.00003245067,
        domain_variance_bias = 0.163495499745,
        determinism = 18.10276377982,
        )],
]
