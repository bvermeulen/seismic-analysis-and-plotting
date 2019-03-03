''' a little parser program to get weather information from dailies '''
import csv
import re

file_name_input = 'daily diary - seismic qc - 3D skn+dns.txt'
file_name_output = 'weather.csv'

with open(file_name_input, 'r') as diary:
    lines = diary.readlines()

lines = [line.strip() for line in lines]

weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

parsed_lines = []
parsed_line = []
first_date = True
for line in lines:
    if line[0:3] in weekdays:
        if first_date:
            first_date = False
        
        else:
            parsed_lines.append(parsed_line)
            print(parsed_line)

        parsed_line = [line]

    if parsed_line:
        line = re.sub('^- ', '', line)
        weather_related = re.search('[wW]eat', line)
        if weather_related :
            parsed_line.append(f'{line}')

        weather_related = re.search('[sS]unrise', line)
        if weather_related:
            parsed_line.append(f'{line}')

parsed_lines.append(parsed_line)

# write csv file
with open(file_name_output, 'w', newline='') as csvfile:
    weather_writer = csv.writer(csvfile, delimiter=',')
    for line in parsed_lines:
        weather_writer.writerow(line)
