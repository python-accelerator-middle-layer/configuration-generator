# dependencies: 
# pip install pytango
# pip install tango-pyaml
# pip install accelerator-middle-layer
# pip install accelerator-toolbox
# pip install pyyaml
# pip install git+https://github.com/python-accelerator-middle-layer/pyaml-test-lattice.git@main
# pip install git+https://github.com/python-accelerator-middle-layer/pyaml-cs-oa.git@main

import os
import at
import yaml
import numpy as np
from os.path import exists

__authors__ = 'S.Liuzzo, J.-L. Pons, ESRF'

def assign_uuid(r, name, extens):
    for i, el in enumerate(r):
        el.UniqueID = el.FamName + f'{i:03d}'
    modified_AT_file = name + '_unique' + extens
    at.save_lattice(r, modified_AT_file) # save to the same format of the initial file
    return r, modified_AT_file

def generate_configuration(latticefile, 
                           wizard=False,
                           uuid=None, 
                           control_system='TangoOphydAsynch', 
                           hcors='', 
                           vcors='',
                           bpms='',
                           qds='',
                           qfs=''):

    print('DISCLAIMER: This function creates a configuration file that allows to test pyAML features. For a fully operational file, for CTRM, some more work will be needed with insigth from the specific facility.')

    r = at.load_lattice(latticefile)

    n = str(latticefile).split("/")

    name, extens = os.path.splitext(n[-1])
    
    config_file = name + '_wizard.yml'

    if wizard:
        ans = input('The elements in your lattice file have a unique name attribute (y/n)?')

        modified_AT_file = str(latticefile) # default AT file to input file

        if ans=='y':
            uuid = input('What is the name of the unique name attribute (Device, UUID, UniqueName, FamName, etc ..)?')
        elif ans=='n':
            # add UUID with unique names and save a new file
            r, modified_AT_file = assign_uuid(r, name, extens)
            uuid = 'UniqueID'
        else:
            print('please answer y or n')
            exit()
    else:
        if uuid==None:
            r, modified_AT_file = assign_uuid(r, name, extens)
            uuid = 'UniqueID'

    # control system
    if wizard:
        control_system = input('Which control system do you use (Epics / Tango / TangoOphydAsynch)?')
    else:
        if control_system not in ['Epics', 'Tango', 'TangoOphydAsynch']:
            raise ValueError('Either Epics or Tango or TangoOphydAsynch')

    print(control_system)
    
    if control_system =='Epics':
            contr = {
                'class': f'pyaml_cs_oa.controlsystem.OphydAsyncControlSystem',
                'name' : 'live',
                'backend': 'Epics',
                'prefix': 'your-epics-prefix:'
            }
    elif control_system=='TangoOphydAsynch':
            contr = {
                'class': f'pyaml_cs_oa.controlsystem.OphydAsyncControlSystem',
                'name': 'live',
                'backend': 'tango',
                'prefix':'//your-host-name:10000/',
            }
    elif control_system=='Tango':
            # data = [{'type': 'tango.pyaml.static_catalog_entry', 
            #          'key': 'your-key',
            #          'device': {
            #                 'type': 'tango.pyaml.attribute_read_only',
            #                 'attribute': 'your/attribute/name',
            #                 'unit': 'm'}
            #             }
            #         ]
            # with open(f'./catalog.yml', 'w') as cata:
            #         yaml.dump(data, cata, default_flow_style=False, sort_keys=False)
            
            contr = dict(
                type = f'tango.pyaml.controlsystem',
                name = 'live',
                tango_host = 'your.tango.host:10000',
                catalog = {'type': 'tango.pyaml.tango_catalog',
                #           'entries': './catalog.yml'
                }
                )
    else:
        raise ValueError('Either Epics or Tango or TangoOphydAsynch')

            
    # Devices

    cal_dir = './calibrations'
    if not os.path.exists(cal_dir):
        os.makedirs(cal_dir)

    devs = []
    inds = np.sort(np.concatenate((r.get_uint32_index(at.Quadrupole), r.get_uint32_index(at.Sextupole), r.get_uint32_index(at.Bend), r.get_uint32_index(at.Monitor), r.get_uint32_index(at.RFCavity))))
    for el in r[inds[0:20]]:

        devname = f'/your/device/name/{el.__getattribute__(uuid)}'
        d = dict()

        if type(el)==at.Quadrupole:

            quad_cal_file = './calibrations/your_quadrupole_curve.csv'
            if not(exists(quad_cal_file)):
                kl=el.PolynomB[1]*el.Length  # 1/m
                curve = np.array([np.linspace(0,100,11),np.linspace(0, kl*2, 11)]).T
                np.savetxt(quad_cal_file, curve, delimiter=',') # A vs 1/m
            

            d = dict(type = f'pyaml.magnet.quadrupole',
                    name = el.__getattribute__(uuid),
                    model = dict(
                        type= 'pyaml.magnet.linear_model',
                        calibration_factor= 1.00054,
                        crosstalk= 1.0,
                        curve= dict(
                            type= 'pyaml.magnet.csvcurve',
                            file= quad_cal_file,
                            ),
                        unit= '1/m',
                        hardware_unit= 'A',
                        powerconverter= devname
                    )
                    ) 
            
        elif type(el)==at.Sextupole:

            sext_cal_file = './calibrations/your_sextupole_curve.csv'
            if not(exists(sext_cal_file)):
                kl=el.PolynomB[1]*el.Length  # 1/m2
                curve = np.array([np.linspace(0,100,11),np.linspace(0, kl*2, 11)]).T
                np.savetxt(sext_cal_file, curve, delimiter=',') # A vs 1/m2

            d = dict(type = f'pyaml.magnet.sextupole',
                    name = el.__getattribute__(uuid),
                    model = dict(
                        type= 'pyaml.magnet.linear_model',
                        curve= dict(
                            type= 'pyaml.magnet.csvcurve',
                            file= sext_cal_file,
                            ),
                        unit= '1/m2',
                        hardware_unit= 'A',
                        powerconverter= devname
                    )
                    ) 
            
        elif type(el)==at.Monitor:
            t = 'monitor'
            d = dict(type = 'pyaml.bpm.bpm',
                    name= el.__getattribute__(uuid),
                    x_pos= devname,
                    y_pos= devname
                    )

        elif type(el)==at.RFCavity:
            t = 'rf.rf_transmitter'
            d = dict(type= 'pyaml.rf.rf_plant',
                    name= 'DEFAULT_RF_PLANT',
                    masterclock = 'your/master/clock/device',
                    transmitters= [dict(
                        type= 'pyaml.rf.rf_transmitter',
                        name= 'RFTRA',
                        cavities= [el.__getattribute__(uuid),],
                        harmonic= 1,
                        distribution= 1,
                        voltage= 'your/voltage/device/name')],
                        )

        if d != dict():
            devs.append(d)
    
    d=dict(type= 'pyaml.diagnostics.tune_monitor',
            name= 'BETATRON_TUNE',
            tune_h= 'your/beam-tune/main/Qh',
            tune_v= 'your/beam-tune/main/Qv')
    devs.append(d)
    
    d=dict(type= 'pyaml.tuning_tools.chromaticity_monitor',
        name= 'CHROMATICITY_MONITOR',
        betatron_tune_name= 'BETATRON_TUNE',
        rf_plant_name= 'DEFAULT_RF_PLANT',
        bpm_array_name= 'BPM',
        n_step= 5)
    devs.append(d)

    d=dict( type= 'pyaml.tuning_tools.tune',
        name= 'DEFAULT_TUNE_CORRECTION',
        quad_array_name= 'QForTune',
        betatron_tune_name= 'BETATRON_TUNE',
        response_matrix= 'path/to/your/tune_response_matrix.csv')
    devs.append(d)

    # arrays

    # create an array with some quadrupoles
    ind = r.get_uint32_index(at.Quadrupole)
    arr_q = []
    for i in ind[0:6]:
        arr_q.append(r[i].__getattribute__(uuid))
    
    # create an array with some magnets (quad/sext)
    ind = np.sort(np.concatenate((r.get_uint32_index(at.Quadrupole), 
                                  r.get_uint32_index(at.Sextupole))))
    arr_c = []
    for i in ind[0:6]:
        arr_c.append(r[i].__getattribute__(uuid))
    
    # create and array with some bpms
    ind = r.get_uint32_index(at.Monitor)
    arr_b = []
    for i in ind[0:6]:
        arr_b.append(r[i].__getattribute__(uuid))


    arrs=[]
    arrs.append(dict(
            type = 'pyaml.arrays.magnet',
            name = 'some_quads',
            elements = arr_q
        ))
    
    arrs.append(dict(
            type = 'pyaml.arrays.magnet',
            name = 'some_mags',
            elements = arr_c
        ))
    # arrs.append(dict(
    #         type = 'pyaml.arrays.magnet',
    #         name = 'some_bpms',
    #         elements = arr_b
    #     ))
    if wizard:
        hcors = input('Could you provide a wildcard (*) string for Hor. correctors (ex: HCOR*)? Press enter to use the default.')
    if hcors == '':
        hcors = 'COR*'

    d = dict(type= 'pyaml.arrays.magnet',
            name= 'HCorr',
            elements= [hcors])
    arrs.append(d)

    if wizard:
        vcors = input('Could you provide a wildcard (*) string for Ver. correctors (ex: VCOR*)? Press enter to use the default.')
    if vcors == '':
        vcors = 'COR*'

    d = dict(type= 'pyaml.arrays.magnet',
            name= 'VCorr',
            elements= [vcors])
    arrs.append(d)
    if wizard:
        bpms = input('Could you provide a wildcard (*) string for bpms (ex: BPM*)? Press enter to use the default.')
    if bpms == '':
        bpms = 'BPM*'
    
    d = dict(type= 'pyaml.arrays.bpm',
            name= 'BPM',
            elements= [bpms])
    arrs.append(d)

    if wizard:
        qfs = input('Could you provide a wildcard (*) string for focussing quadrupole used for tune correction (ex: QF*)? Press enter to use the default.')
    if qfs == '':
        qfs = 'QF1*'
    if wizard:
        qds = input('Could you provide a wildcard (*) string for defocussing quadrupole used for tune correction (ex: QD*)? Press enter to use the default.')
    if qds == '':
        qds = 'QD2*'

    d = dict(type= 'pyaml.arrays.magnet',
            name= 'QForTune',
            elements= [qfs, qds])
    arrs.append(d)
    
    if extens=='json':
        print('.json extension, avoid file extension')
        modified_AT_file = f'${{path:{modified_AT_file}}}'

    
    # create config files
    data = dict(
        type = 'pyaml.accelerator',
        facility = 'my facility',
        machine = 'sr',
        data_folder = '.',
        energy = r.energy,
        simulators = [dict(
            type = 'pyaml.lattice.simulator',
            lattice = modified_AT_file,
            name = 'design',
            linker = dict(
                type = 'pyaml.lattice.attribute_linker',
                attribute_name = uuid
            )
        )],
        controls = [contr],
        arrays = arrs,
        devices = devs
        )

    # write files
    with open(f'./{config_file}', 'w') as config:
        yaml.dump(data, config, default_flow_style=False, sort_keys=False)

    print(f'The file {config_file} is created and can be used by pyAML in ''design'' mode.\n ' \
    'Some information still needs to be updated by hand.\n' \
    ' Look for "your" in the file and replace with the correct values.\n')

    return config_file


if __name__ == '__main__':

    # get a lattice file
    from pyaml_test_lattice import lattices

    lattice_file = lattices["fodo_1gev_6d.m"]

    # create the configuration
    config_file = generate_configuration(lattice_file)

    print(f'created test config file: {os.path.abspath(config_file)}')

    # instantiate pyaml object based on the configuration 
    from pyaml.accelerator import Accelerator
        
    accelerator = Accelerator.load(config_file)

    # Get the quadrupole
    quad = accelerator.design.magnet.get('QF_001001')

    # Use the quadrupole in the same way as before
    k = quad.strength.get()
    print(f'{quad.name} strength = {k} 1/m')



