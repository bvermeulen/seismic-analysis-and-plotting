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


def average_with_outlier_removed(input_list, allowed_range):
    '''  calculates average of elements in a list with values within an 
         allowed range. One outlier (i.e. an element with a value that exceeds
         the allowed range) will be removed. If there is a choice between
         valid ranges then choose the one with smallest range. If there are 
         no allowed ranges then the funcion returns None

         Parameter:
         :input_list: list with values to be averaged
         :allowed_range: range that is allowed for values to deviate

         Return:
         :average: average value of list or None if there are more than one value
                   exceeding the allowed_range
    '''
    input_list.sort()
    elements = len(input_list)

    #check if input_list is not empty to avoid index errors
    if elements == 0:
        return None

    # if there is only one element then return this value
    elif elements == 1:
        return input_list[0]

    # if there are 2 elements they must be within allowed_range
    elif elements == 2:
        if abs(input_list[1] - input_list[0]) < allowed_range:
            return sum(input_list)/ 2
        else:
            return None

    # if all elements are within the allowed_range calculate average
    elif abs(input_list[-1] - input_list[0]) < allowed_range:
        return sum(input_list)/ elements

    # if there is a choice between the two ranges choose the smallest
    elif abs(input_list[0] - input_list[-2]) < abs(input_list[1] - input_list[-1]):
        if abs(input_list[0] - input_list[-2]) < allowed_range:
            return sum(input_list[0:-1])/(elements - 1)
        else:
            return None
    
    else:
        if abs(input_list[1] - input_list[-1]) < allowed_range:
            return sum(input_list[1:])/ (elements - 1)
        else:
            return None