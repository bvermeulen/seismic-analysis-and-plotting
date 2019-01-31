import numpy as np
from datetime import date
'''
module for general purpose utility functions
'''


def string_to_value_or_nan(string_value, type):
    '''  convert string value to a value of type type which can be int, float or date
         if string cannot be converted the value will be a np.NaN
         Date format is a string with following format: YYYYMMDD (for example 20181118)
         :input: string_value - string to be converted
         :input: type ['int', 'float', 'date']
         :output: value of type type

    '''
    try:
        value = str(string_value)
        if type == 'date':
            value = date(int(value[0:4]),
                         int(value[4:6]), 
                         int(value[6:8]))
                                                
        elif type == 'int':
            value = int(value)

        elif type == 'float':
            value = float(value)

        else:
            assert False, 'invalid input, must be either int, float or date'
    
    except ValueError:
        value = np.NaN
    
    return value
