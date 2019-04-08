import set_gdal_pyproj_env_vars_and_logger
import glob
import numpy as np
from pss_io import pss_read_file 
import matplotlib.pyplot as plt
from scipy import stats
from geo_io import get_date
from Utils.plogger import Logger


def input_fleet(fleets):
    vibs = []
    correct_answer = False
    fleet = []
    while not correct_answer:
        for i, _fleet in enumerate(fleets):
            print(f'\nfleet {i+1}: ', end='')
            for vib in _fleet:
                vibs.append(vib)
                print(f'{vib} ', end='')

        answer = input('\nvibe fleet [0 - exit]: ')

        try:
            if answer in ['q', 'Q'] or int(answer) == 0:
                fleet.append(0)
            elif int(answer) < len(fleets)+1 and int(answer) > 0:
                fleet = list(fleets[int(answer)-1])
            else:
                raise ValueError
            correct_answer = True
        except ValueError:
            try:
                if answer[0] in ['v', 'V'] and int(answer[1:]) in vibs:
                    fleet.append(int(answer[1:]))
                elif all(x in vibs for x in map(int, answer.split())): 
                    fleet = list(map(int, answer.split()))
                else:
                    raise ValueError
                correct_answer = True
            except ValueError:
                print(f'incorrect answer')
    
    return fleet


class PssData:
    '''  method for handling PSS data '''
    def __init__(self, pss_input_data):
        self.pss_data = pss_input_data
        self.attr = {}
        self.attr['unit_id'] = int(pss_input_data[0].index('Unit ID'))
        self.attr['record_index'] = int(pss_input_data[0].index('File Num'))
        self.attr['phase_max'] = int(pss_input_data[0].index('Phase Max'))
        self.attr['phase_avg'] = int(pss_input_data[0].index('Phase Avg'))
        self.attr['thd_max'] = int(pss_input_data[0].index('THD Max'))
        self.attr['thd_avg'] = int(pss_input_data[0].index('THD Avg'))
        self.attr['force_max'] = int(pss_input_data[0].index('Force Max'))
        self.attr['force_avg'] = int(pss_input_data[0].index('Force Avg'))
        self.attr['void'] = int(pss_input_data[0].index('Void'))
        self.attr['comment'] = int(pss_input_data[0].index('Comment'))

        del self.pss_data[0]

        # clean PSS data
        delete_list = []
        for i, pss in enumerate(self.pss_data):
            if pss[self.attr['void']] == 'Void':
                delete_list.append(i)
            elif not pss[self.attr['record_index']]:
                delete_list.append(i)
            elif int(pss[self.attr['force_max']]) == 0:
                delete_list.append(i)
            try:
                if pss[self.attr['comment']][-10:] == 'been shot!': 
                    delete_list.append(i)
            except:
                pass
                
        for i in range(len(delete_list)-1, -1, -1):
            del self.pss_data[delete_list[i]]
            
        # determine fleets
        fleets = set()
        record = 0
        _fleet = set()
        for pss in self.pss_data:
            if int(pss[self.attr['record_index']]) == record:
                _fleet.add(int(pss[self.attr['unit_id']]))
            else:
                record = int(pss[self.attr['record_index']])
                if _fleet:
                    fleets.add(frozenset(_fleet))
                _fleet = set()
                _fleet.add(int(pss[self.attr['unit_id']]))
    
        fleets = list(fleets)
        fleets_copy = fleets[:]

        for i in range(len(fleets)):
            for j in range(0, len(fleets)):
                if fleets[j] > fleets[i]:
                    fleets_copy.remove(fleets[i])
                    break

        self.fleets = fleets_copy 

    def obtain_vib_data(self, attr_key, mask_value):
        '''  method to get the data for attr_key for the fleet. If there is no value the mask_value will 
             be assigned to mask the record from plotting
        '''
        logger = Logger.getlogger()
        # determine list of field records for all vibes in the fleet
        vib_axis = set()
        for pss in self.pss_data:
            try:
                if int(pss[self.attr['unit_id']]) in self.fleet:
                    vib_axis.add(int(pss[self.attr['record_index']]))
            except ValueError:
                pass

        vib_axis = list(vib_axis)
        vib_axis.sort()

        # create a vib_data_pairs list for each vib in the fleet
        vib_data_pairs = [[] for _ in self.fleet]
        unique_ids = []
        # loop reverse as we want to keep the last entry and not the first 
        for pss in reversed(self.pss_data):
            try:
                vib_id = int(pss[self.attr['unit_id']])
                record = int(pss[self.attr['record_index']])
                fleet_id = self.fleet.index(vib_id)
                # check if vibs have not been called again and tuple (record, vibe) is unique
                unique_id = (record, vib_id) 
                if unique_id not in unique_ids:
                    unique_ids.append(unique_id)
                    data_point = (record, int(pss[self.attr[attr_key]]))
                    vib_data_pairs[fleet_id].append(data_point)
                else:
                    logger.info(f'this record is not unique: {unique_id}')
            except ValueError:
                pass

        # check if there are records where there is no value for the vibe unit
        # - if not assign the mask value
        vib_data = [[] for _ in self.fleet]
        for i, _ in enumerate(self.fleet):
            _vib_axis, _ = zip(*vib_data_pairs[i])
            for x in vib_axis:
                if x not in _vib_axis:
                    vib_data_pairs[i].append((x, mask_value))

            vib_data_pairs[i].sort()
            _ , vib_data[i] = zip((*vib_data_pairs[i]))
            vib_data[i] = list(vib_data[i])

            assert len(vib_data[i]) == len(vib_axis), \
                   f'len(vib_data) = {len(vib_data[i])}, len(vib_exis) = {len(vib_axis)}'

        return vib_axis, vib_data

    def print_pss_data(self, vibes):
        '''  method to print the pss data '''
        logger = Logger.getlogger()
        self.fleet = list(vibes)
        for vib in self.fleet:
            for pss in self.pss_data:

                if pss[self.attr['unit_id']] and int(pss[self.attr['unit_id']]) == vib:
                    record = int(pss[self.attr['record_index']])
                    phase_max = int(pss[self.attr['phase_max']])
                    phase_avg = int(pss[self.attr['phase_avg']])
                    thd_max = int(pss[self.attr['thd_max']])
                    thd_avg = int(pss[self.attr['thd_avg']])
                    force_max = int(pss[self.attr['force_max']])
                    force_avg = int(pss[self.attr['force_avg']])
                    logger.info(f'record: {record}: '
                                 f'vibe: {vib} '
                                 f'phase: {phase_avg} {phase_max}; '
                                 f'distortion: {thd_avg} {thd_max}; '
                                 f'force: {force_avg} {force_max}')

    def plot_pss_data(self, vibes):
        '''  method to plot the pss data '''
        self.fleet = list(vibes)
        fig1, ((ax0, ax1), (ax2, ax3), (ax4, ax5),
              ) = plt.subplots(nrows=3, ncols=2, figsize=(8, 8))
        plt.subplots_adjust(hspace=10)
        ax0, ax1 = self.plot_thd_max(ax0, ax1)
        ax2, ax3 = self.plot_force_max(ax2, ax3)
        ax4, ax5 = self.plot_phase_max(ax4, ax5)
        fig1.tight_layout()

        fig2, ((ax6, ax7), (ax8, ax9), (ax10, ax11),
              ) = plt.subplots(nrows=3, ncols=2, figsize=(8, 8))
        ax6, ax7 = self.plot_thd_avg(ax6, ax7)
        ax8, ax9 = self.plot_force_avg(ax8, ax9)
        ax10, ax11 = self.plot_phase_avg(ax10, ax11)

        fig2.tight_layout()
        plt.show()

    def plot_thd_max(self, axis1, axis2):
        mask_value = -1
        vib_axis, vib_data = self.obtain_vib_data('thd_max', mask_value)

        axis1 = self.plot_attr(axis1, vib_axis, vib_data, mask_value)
        axis1.set_title('Peak THD')
        axis1.legend(loc='upper right')
        axis1.set_ylabel('Perc. distortion')
        axis1.set_xlabel('Record index')
        axis1.set_ylim(bottom=0, top=60)

        axis2 = self.plot_density(axis2, vib_data, mask_value, (0, 60, 1))
        axis2.set_title('Peak THD density')
        axis2.legend(loc='upper right')
        axis2.set_ylabel('Density')
        axis2.set_xlabel('Distortion')

        return axis1, axis2

    def plot_thd_avg(self, axis1, axis2):
        mask_value = -1
        vib_axis, vib_data = self.obtain_vib_data('thd_avg', mask_value)

        axis1 = self.plot_attr(axis1, vib_axis, vib_data, mask_value)
        axis1.set_title('Average THD')
        axis1.legend(loc='upper right')
        axis1.set_ylabel('Perc. distortion')
        # axis1.set_xlabel('Record index')
        axis1.set_ylim(bottom=0, top=40)

        axis2 = self.plot_density(axis2, vib_data, mask_value, (0, 40, 1))
        axis2.set_title('Average THD density')
        axis2.legend(loc='upper right')
        axis2.set_ylabel('Density')
        axis2.set_xlabel('Distortion')

        return axis1, axis2

    def plot_phase_max(self, axis1, axis2):
        mask_value = -10
        vib_axis, vib_data = self.obtain_vib_data('phase_max', mask_value)

        axis1 = self.plot_attr(axis1, vib_axis, vib_data, mask_value)
        axis1.set_title('Peak phase')
        axis1.legend(loc='upper right')
        axis1.set_ylabel('Degrees')
        # axis1.set_xlabel('Record index')
        axis1.set_ylim(bottom=0, top=20)

        axis2 = self.plot_density(axis2, vib_data, mask_value, (0, 20, 1))
        axis2.set_title('Peak phase density')
        axis2.legend(loc='upper right')
        axis2.set_ylabel('Density')
        axis2.set_xlabel('Degrees')

        return axis1, axis2

    def plot_phase_avg(self, axis1, axis2):
        mask_value = -10
        vib_axis, vib_data = self.obtain_vib_data('phase_avg', mask_value)

        axis1 = self.plot_attr(axis1, vib_axis, vib_data, mask_value)
        axis1.set_title('Average phase')
        axis1.legend(loc='upper right')
        axis1.set_ylabel('Degrees')
        # axis1.set_xlabel('Record index')
        axis1.set_ylim(bottom=0, top=10)

        axis2 = self.plot_density(axis2, vib_data, mask_value, (0, 10, .5))
        axis2.set_title('Average phase density')
        axis2.legend(loc='upper right')
        axis2.set_ylabel('Density')
        axis2.set_xlabel('Degrees')

        return axis1, axis2

    def plot_force_max(self, axis1, axis2):
        mask_value = -10
        vib_axis, vib_data = self.obtain_vib_data('force_max', mask_value)

        axis1 = self.plot_attr(axis1, vib_axis, vib_data, mask_value)
        axis1.set_title('Peak force')
        axis1.legend(loc='upper right')
        axis1.set_ylabel('Drive level')
        # axis1.set_xlabel('Record index')
        axis1.set_ylim(bottom=0, top=100)

        axis2 = self.plot_density(axis2, vib_data, mask_value, (0, 100, 1))
        axis2.set_title('Peak force density')
        axis2.legend(loc='upper right')
        axis2.set_ylabel('Density')
        axis2.set_xlabel('Drive level')

        return axis1, axis2

    def plot_force_avg(self, axis1, axis2):
        mask_value = -10
        vib_axis, vib_data = self.obtain_vib_data('force_avg', mask_value)

        axis1 = self.plot_attr(axis1, vib_axis, vib_data, mask_value)
        axis1.set_title('Average force')
        axis1.legend(loc='upper right')
        axis1.set_ylabel('Drive level')
        # axis1.set_xlabel('Record index')
        axis1.set_ylim(bottom=0, top=100)

        axis2 = self.plot_density(axis2, vib_data, mask_value, (0, 100, 1))
        axis2.set_title('Average force density')
        axis2.legend(loc='upper right')
        axis2.set_ylabel('Density')
        axis2.set_xlabel('Drive level')

        return axis1, axis2


    def plot_attr(self, axis, vib_axis, vib_data, mask_value):
        '''  method to plot the vib attribute versus record number
        '''
        for i, vib in enumerate(vib_data):
            vib = np.array(vib)
            vib = np.ma.masked_where(vib == mask_value, vib)
            axis.plot(vib_axis, vib, label=self.fleet[i])

        return axis

    def plot_density(self, axis, vib_data, mask_value, attr_range):
        '''  method to plot the attribute density function. If no density plot can be made then plot unity density
        '''
        attr_value = np.arange(attr_range[0], attr_range[1], attr_range[2])
        unit_function = lambda x: 1 if x==0 else 0
        for i, _vib in enumerate(vib_data):
            # remove mask value from list
            j = 0
            while mask_value in _vib:
                if _vib[j] == mask_value:
                    del _vib[j]
                    j -= 1
                j += 1

            try:
                vib = stats.kde.gaussian_kde(_vib)
                axis.plot(attr_value, vib(attr_value), label=self.fleet[i])
            except (np.linalg.LinAlgError):
                vib = [unit_function(x) for x in range(len(attr_value))]
                axis.plot(attr_value, vib, label=self.fleet[i])

        return axis


if __name__ == "__main__":
    logformat = '%(asctime)s - %(levelname)s - %(message)s'
    Logger.set_logger('pss_data.log', logformat, 'DEBUG')
    
    correct_file = False
    while True:

        pss_data = pss_read_file(get_date())

        if pss_data == -1:
            pass
        else:
            pss = PssData(pss_data)
            correct_file = True

        while correct_file:
            fleet = input_fleet(pss.fleets)
            if fleet[0] == 0:
                break

            pss.plot_pss_data(fleet)
