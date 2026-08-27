# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 23:00:04 2019

@author: Green
"""

#drawing head unit using mathmatics

import math

import seaborn as sns
import numpy as np

#%matplotlib inline

print (math.sin(45))


b = np.arange(0, 1, 0.01, np.float64)

sinB = np.sin(b)
print (sinB)

sns.distplot(sinB)
#sns.distplot(sinB, kde = False, bins = 2)
sns.distplot(b)

sns.jointplot(x = b, y = sinB,kind='hex')

