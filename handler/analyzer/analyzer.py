# !/usr/bin/env python3
"""
Created on Fri Jun 26 08:37:56 2020

Analyzer code that attempts to determine BIDS
from dcm2niix NIFTI/JSON output

@author: dlevitas
"""

from __future__ import division
import os, sys, re, json, warnings
import pandas as pd
import numpy as np
import nibabel as nib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.style.use('dark_background')
from operator import itemgetter
from math import floor

warnings.filterwarnings("ignore")
os.environ[ 'MPLCONFIGDIR' ] = '/tmp/'

# data_dir = sys.argv[1]
data_dir = '/media/data/ezbids/dicoms/WML/session_test'
os.chdir(data_dir)


######## Functions ######## 

def select_unique_data(dir_list):
    '''
    Takes list of nifti, json, and bval/bvec files generated frm dcm2niix to find the 
        unique data within the entire list. The contents of the list can be data
        from an entire dataset, a single subject, etc

    Parameters
    ----------
    dir_list : pd.DataFrame()
        List of nifti, json, and bval/bvec files generated from dcm2niix

    Returns
    -------
    data_list_unique_series: list
        List of dictionaries containing pertinent and unique information about the
            data, primarily coming from the metadata in the json files
            
    subjectIDs_info: list
        List of dictionaries containing subject identification info, such as
        PatientID, PatientName, PatientBirthDatge
    
    acquisition_dates: list    
        List of dictionaries containing the AcquisitionDate and session #  (if applicable)
    '''
    
    # Load list generated from dcm2niix, and organize the nifti/json files by their SeriesNumber   
    dir_list.columns = ['path']
    
    # Remove Philips proprietary files in dir_list if they exist
    dir_list = dir_list[~dir_list.path.str.contains('PARREC|Parrec|parrec')].reset_index(drop=True)    
    
    # Get separate nifti and json (i.e. sidecar) lists
    json_list = [x for x in dir_list['path'] if '.json' in x and 'ezbids' not in x]
    nifti_list = [x for x in dir_list['path'] if '.nii.gz' in x or '.bval' in x or '.bvec' in x]
        
    # Create list for appending dictionaries to
    data_list = []
    
    # Parse through nifti and json data for pertinent information
    print('Determining unique acquisitions in list')
    print('------------------------------------------')
    for j in range(len(json_list)):
        json_data = open(json_list[j])
        json_data = json.load(json_data, strict=False)
        
        # Select SeriesNumbers
        SN = json_data['SeriesNumber']
            
        # Specify direction based on PhaseEncodingDirection (PED)
        # May not be as straight forward, see: https://github.com/rordenlab/dcm2niix/issues/412
        try:
            phase_encoding_direction = json_data['PhaseEncodingDirection']
            if phase_encoding_direction == 'j-':
                PED = 'AP'
            elif phase_encoding_direction == 'j':
                PED = 'PA'
            elif phase_encoding_direction == 'i':
                PED = 'RL'
            elif phase_encoding_direction == 'i-':
                PED = 'LR'
            else:
                PED = ''
        except:
            PED = ''
        
            
        # Nifti (and bval/bvec) file(s) associated with specific json file
        nifti_paths_for_json = [x for x in nifti_list if json_list[j][:-4] in x]
        nifti_paths_for_json = [x for x in nifti_paths_for_json if '.json' not in x]
            
        # Find nifti file size
        filesize = os.stat(nifti_paths_for_json[0]).st_size
        
        # Find StudyID from json
        if 'StudyID' in json_data:
            studyID = json_data['StudyID']
        else:
            studyID = ''
        
        # Find subjectID from json (some files contain neither PatientName nor PatientID)
        if 'PatientName' in json_data:
            PatientName = json_data['PatientName']
        else:
            PatientName = None
            
        if 'PatientID' in json_data:
            PatientID = json_data['PatientID']
        else:
            PatientID = None
            
        # Find PatientBirthDate
        if 'PatientBirthDate' in json_data:
            PatientBirthDate = json_data['PatientBirthDate'].replace('-','')
        else:
            PatientBirthDate = None
            
        # Find PatientSex
        if 'PatientSex' in json_data:
            PatientSex = json_data['PatientSex']
            if PatientSex not in ['M','F']:
                PatientSex = 'N/A'
        else:
            PatientSex = 'N/A'
        
        # Select subjectID to display to ezBIDS users
        # Order of importance is: PatientName > PatientID > PatientBirthDate
        if PatientName:
            subject = PatientName
        elif PatientID:
            subject = PatientID
        else:
            subject = PatientBirthDate
        subject = re.sub('[^A-Za-z0-9]+', '', subject)
        
        # Find Acquisition Date & Time
        if 'AcquisitionDateTime' in json_data:
            AcquisitionDate = json_data['AcquisitionDateTime'].split('T')[0]
            AcquisitionTime = json_data['AcquisitionDateTime'].split('T')[-1]
        else:
            AcquisitionDate = '0000-00-00'
            AcquisitionTime = None
            
        # Find RepetitionTime
        if 'RepetitionTime' in json_data:
            RepetitionTime = json_data['RepetitionTime']
        else:
            RepetitionTime = 'N/A'
        
        # Find EchoNumber
        if 'EchoNumber' in json_data:
            EchoNumber = json_data['EchoNumber']
        else:
            EchoNumber = None
        
        # Find EchoTime
        if 'EchoTime' in json_data:
            EchoTime = json_data['EchoTime']*1000
        else:
            EchoTime = 0
        
        # Find MultibandAccerationFactor
        if 'MultibandAccelerationFactor' in json_data:
            MultibandAccelerationFactor = json_data['MultibandAccelerationFactor']
        else:
            MultibandAccelerationFactor = 'N/A'
            
        # Find how many volumes are in jsons's corresponding nifti file
        try:
            volume_count = nib.load(json_list[j][:-4] + 'nii.gz').shape[3]
        except:
            volume_count = 1
           
        # Relative paths of json and nifti files (per SeriesNumber)
        paths = sorted(nifti_paths_for_json + [json_list[j]])
            
        # Organize all from individual SeriesNumber in dictionary
        mapping_dic = {'StudyID': studyID,
                       'PatientName': PatientName,
                       'PatientID': PatientID,
                       'PatientBirthDate': PatientBirthDate,
                       'PatientSex': PatientSex,
                       'PatientAge': 'N/A',
                       'subject': subject,
                       'session': '',
                       'SeriesNumber': json_data['SeriesNumber'],
                       'AcquisitionDate': AcquisitionDate,
                       'AcquisitionTime': AcquisitionTime,
                       'SeriesDescription': json_data['SeriesDescription'],
                       'ProtocolName': json_data['ProtocolName'], 
                       'ImageType': json_data['ImageType'],
                       'SeriesNumber': json_data['SeriesNumber'],
                       'RepetitionTime': RepetitionTime,
                       'EchoNumber': EchoNumber,
                       'EchoTime': EchoTime,
                       'MultibandAccelerationFactor': MultibandAccelerationFactor,
                       'DataType': '',
                       'ModalityLabel': '',
                       'series_id': 0,
                       'direction': PED,
                       'forType': '',
                       'TaskName': '',
                       "exclude": False,
                       'filesize': filesize,
                       "NumVolumes": volume_count,
                       'error': None,
                       'section_ID': 1,
                       'message': '',
                       'br_type': '',
                       'nifti_path': [x for x in nifti_paths_for_json if '.nii.gz' in x][0],
                       'json_path': json_list[j],
                       'paths': paths,
                       'pngPath': '',
                       'headers': '',
                       'sidecar':json_data
                       }
        data_list.append(mapping_dic)
        
    # Curate subjectID and acquisition date info to display in UI
    subjectIDs_info = list({x['subject']:{'subject':x['subject'], 'PatientID':x['PatientID'], 'PatientName':x['PatientName'], 'PatientBirthDate':x['PatientBirthDate'], 'phenotype':{'sex':x['PatientSex'], 'age':x['PatientAge']}, 'exclude': False, 'sessions': []} for x in data_list}.values())

                 
    subjectIDs_info = sorted(subjectIDs_info, key = lambda i: i['subject'])
    
    acquisition_dates = list({(x['subject'], x['AcquisitionDate']):{'subject':x['subject'], 'AcquisitionDate':x['AcquisitionDate'], 'session': ''} for x in data_list}.values())
    acquisition_dates = sorted(acquisition_dates, key = lambda i: i['AcquisitionDate'])
    
    # Insert sessions info if applicable
    subject_session = [[x['subject'], x['AcquisitionDate'], x['session']] for x in data_list]
    subject_session = sorted([list(x) for x in set(tuple(x) for x in subject_session)], key = lambda i: i[1])
    
    for i in np.unique(np.array([x[0] for x in subject_session])):
        subject_indices = [x for x,y in enumerate(subject_session) if y[0] == i]
        if len(subject_indices) > 1:
            for j, k in enumerate(subject_indices):
                subject_session[k][-1] = str(j+1)
    
    subject_session = sorted([list(x) for x in set(tuple(x) for x in subject_session)], key = lambda i: i[1])
    
    for x,y in enumerate(acquisition_dates):
        y['session'] = subject_session[x][-1]
        
    
    for si in range(len(subjectIDs_info)):
        for ss in subject_session:
            if ss[0] == subjectIDs_info[si]['subject']:
                subjectIDs_info[si]['sessions'].append({'AcquisitionDate': ss[1], 'session': ss[2], 'exclude': False})
        subjectIDs_info[si].update({'validationErrors': []})
        

    # Sort list of dictionaries by subject, AcquisitionDate, SeriesNumber, and json_path
    data_list = sorted(data_list, key=itemgetter('subject', 'AcquisitionDate', 'SeriesNumber', 'json_path'))
    
    # Add session info to data_list, if applicable
    for i in range(len(acquisition_dates)):
        for j in range(len(data_list)):
            if data_list[j]['subject'] == acquisition_dates[i]['subject'] and data_list[j]['AcquisitionDate'] == acquisition_dates[i]['AcquisitionDate']:
                data_list[j]['session'] = acquisition_dates[i]['session']
        
    # Unique data is determined from four values: SeriesDescription, EchoTime, ImageType, MultibandAccelerationFactor
    # If EchoTime values differ slightly (>< 1) and other values are the same, don't give new unique series ID
    data_list_unique_series = []
    series_tuples = []
    series_id = 0      
    
    for x in range(len(data_list)):
        unique_items = [data_list[x]['EchoTime'], data_list[x]['SeriesDescription'], data_list[x]['ImageType'], data_list[x]['MultibandAccelerationFactor'], 1]
        if x == 0:
            data_list[x]['series_id'] = 0
            data_list_unique_series.append(data_list[x])
        
        elif tuple(unique_items) not in [y[:-1] for y in series_tuples]:
            echo_time = unique_items[0]
            rest = unique_items[1:]
            if tuple(rest) in [y[1:-1] for y in series_tuples]:
                common_series_index = [y[1:-1] for y in series_tuples].index(tuple(rest))

                if not series_tuples[common_series_index][0]-1 <= echo_time <= series_tuples[common_series_index][0]+1:
                    unique_items[-1] = 0
                    series_id += 1
                    data_list[x]['series_id'] = series_id
                    data_list_unique_series.append(data_list[x])
                else:
                    data_list[x]['series_id'] = series_tuples[common_series_index][-1]
            else:
                series_id += 1
                data_list[x]['series_id'] = series_id
                data_list_unique_series.append(data_list[x])
                
        else:
            common_index = [y[1:-1] for y in series_tuples].index(tuple(unique_items[1:]))
            data_list[x]['series_id'] = series_tuples[common_index][-1]
        
        
        tup = tuple(unique_items + [series_id])
        series_tuples.append(tup)
        
    
    return data_list, data_list_unique_series, subjectIDs_info, acquisition_dates
    

def identify_series_info(data_list_unique_series):
    '''
    Takes list of dictionaries with key and unique information, and uses it to 
        determine the DataType and Modality labels of the unique acquisitions. 
        Other information (e.g. run, acq, ce) will be determined if the data 
        follows the ReproIn naming convention for SeriesDescriptions.

    Parameters
    ----------
    data_list_unique_series : list
        List of dictionaries continaing key information about the data

    Returns
    -------
    series_list: list
        List of dictionaries containing pertinent about the unique acquisitions.
        This information is displayed to the user through the UI, which grabs 
        this information.
    '''
    
    
    # Determine DataType and ModalityLabel of series list acquisitions
    series_list = []
    for i in range(len(data_list_unique_series)):
        
        series_entities = {}
        SD = data_list_unique_series[i]['SeriesDescription']
        image_type = data_list_unique_series[i]['ImageType']
        EchoTime = data_list_unique_series[i]['EchoTime']
        TR = data_list_unique_series[i]['RepetitionTime']
        
        if 'SequenceName' in data_list_unique_series[i]['sidecar']:
            SequenceName = data_list_unique_series[i]['sidecar']['SequenceName']
        elif 'ScanningSequence' in data_list_unique_series[i]['sidecar']:
            SequenceName = data_list_unique_series[i]['sidecar']['ScanningSequence']
        else:
            SequenceName = 'N/A'
        
        # Populate some labels fields (based on ReproIn convention)
        if 'sub-' in SD:
            series_entities['subject'] = SD.split('sub-')[-1].split('_')[0]
        else:
            series_entities['subject'] = None
        
        if '_ses-' in SD:
            series_entities['session'] = SD.split('_ses-')[-1].split('_')[0]
        else:
            series_entities['session'] = None
            
        if '_run-' in SD:
            series_entities['run'] = SD.split('_run-')[-1].split('_')[0]
            if series_entities['run'][0] == '0':
                series_entities['run'] = series_entities['run'][1:]
        else:
            series_entities['run'] = ''
        
        if '_task-' in SD:
            series_entities['task'] = SD.split('_task-')[-1].split('_')[0]
        else:
            pass
        
        if '_dir-' in SD:
            series_entities['direction'] = SD.split('_dir-')[-1].split('_')[0]
        else:
            series_entities['direction'] = ''
    
        if '_acq-' in SD:
            series_entities['acquisition'] = SD.split('_acq-')[-1].split('_')[0]
        else:
            series_entities['acquisition'] = ''
            
        if '_ce-' in SD:
            series_entities['ceagent'] = SD.split('_ce-')[-1].split('_')[0]
        else:
            series_entities['ceagent'] = ''
            
        if '_echo-' in SD:
            series_entities['echo'] = SD.split('_echo-')[-1].split('_')[0]
            if series_entities['echo'][0] == '0':
                series_entities['echo'] = series_entities['echo'][1:]
        else:
            series_entities['echo'] = ''
        
        if '_fa-' in SD:
            series_entities['fa'] = SD.split('_fa-')[-1].split('_')[0]
        else:
            series_entities['fa'] = ''
            
        if '_inv-' in SD:
            series_entities['inversion'] = SD.split('_inv-')[-1].split('_')[0]
            if series_entities['inversion'][0] == '0':
                series_entities['inversion'] = series_entities['inversion'][1:]
        else:
            series_entities['inversion'] = ''
            
        if '_part-' in SD:
            series_entities['part'] = SD.split('_part-')[-1].split('_')[0]
        else:
            series_entities['part'] = ''
        
        
        # Make easier to find key characters/phrases in SD by removing non-alphanumeric characters and make everything lowercase
        SD = re.sub('[^A-Za-z0-9]+', '', SD).lower()
        
        # # #  Determine DataTypes and ModalityLabels # # # # # # # 
        
        # Localizers or other non-BIDS compatible acquisitions
        if any(x in SD for x in ['localizer','scout']):
            data_list_unique_series[i]['error'] = 'Acquisition appears to be a localizer or other non-compatible BIDS acquisition'
            data_list_unique_series[i]['message'] = 'Acquisition is believed to be some form of localizer because "localizer" or "scout" is in the SeriesDescription. Please modify if incorrect. ezBIDS does not convert locazliers to BIDS'
            data_list_unique_series[i]['br_type'] = 'exclude (localizer)'
            
        # Arterial Spin Labeling (ASL)
        elif any(x in SD for x in ['asl']):
            data_list_unique_series[i]['br_type'] = 'exclude'
            data_list_unique_series[i]['DataType'] = 'asl'
            data_list_unique_series[i]['ModalityLabel'] = 'asl'
            data_list_unique_series[i]['error'] = 'Acqusition appears to be ASL, which is currently not supported by ezBIDS at this time, but will be in the future'
            data_list_unique_series[i]['message'] = 'Acquisition is believed to be asl/asl because "asl" is in the SeriesDescription. Please modify if incorrect. Currently, ezBIDS does not support ASL conversion to BIDS'
            
        
        # Angiography
        elif any(x in SD for x in ['angio']):
            data_list_unique_series[i]['br_type'] = 'exclude'
            data_list_unique_series[i]['DataType'] = 'anat'
            data_list_unique_series[i]['ModalityLabel'] = 'angio'
            data_list_unique_series[i]['error'] = 'Acqusition appears to be an Angiography acquisition, which is currently not supported by ezBIDS at this time, but will be in the future'
            data_list_unique_series[i]['message'] = 'Acquisition is believed to be anat/angio because "angio" is in the SeriesDescription. Please modify if incorrect. Currently, ezBIDS does not support Angiography conversion to BIDS'
                    
        # Magnitude/Phase[diff] and Spin Echo (SE) field maps
        elif any(x in SD for x in ['fmap','fieldmap','spinecho','sefmri','semri']):
            data_list_unique_series[i]['DataType'] = 'fmap'
            data_list_unique_series[i]['forType'] = 'func/bold'
            
            # Magnitude/Phase[diff] field maps
            if 'EchoNumber' in data_list_unique_series[i]['sidecar']:
                if any(x in data_list_unique_series[i]['json_path'] for x in ['_real.','_imaginary.']):
                    data_list_unique_series[i]['error'] = 'Acquisition appears to be a real or imaginary field map that needs to be manually adjusted to magnitude and phase (ezBIDS currently does not have this functionality). This acqusition will not be converted'
                    data_list_unique_series[i]['message'] = data_list_unique_series[i]['error']
                    data_list_unique_series[i]['br_type'] = 'exclude'
                elif data_list_unique_series[i]['EchoNumber'] == 1 and '_e1_ph' not in data_list_unique_series[i]['json_path']:
                    data_list_unique_series[i]['ModalityLabel'] = 'magnitude1'
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be fmap/magnitude1 because "fmap" or "fieldmap" is in SeriesDescription, EchoNumber == 1 in metadata, and the subjectstring "_e1_ph" is not in the filename. Please modify if incorrect'
                elif data_list_unique_series[i]['EchoNumber'] == 1 and '_e1_ph' in data_list_unique_series[i]['json_path']:
                    data_list_unique_series[i]['ModalityLabel'] = 'phase1'
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be fmap/phase1 because "fmap" or "fieldmap" is in SeriesDescription, EchoNumber == 1 in metadata, and the subjectstring "_e1_ph" is in the filename. Please modify if incorrect'
                elif data_list_unique_series[i]['EchoNumber'] == 2 and '_e2_ph' not in data_list_unique_series[i]['json_path']:
                    data_list_unique_series[i]['ModalityLabel'] = 'magnitude2'
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be fmap/magnitude2 because "fmap" or "fieldmap" is in SeriesDescription, EchoNumber == 2 in metadata, and the subjectstring "_e2_ph" is not in the filename. Please modify if incorrect'
                elif data_list_unique_series[i]['EchoNumber'] == 2 and '_e2_ph' in data_list_unique_series[i]['json_path'] and '_e1_ph' in data_list_unique_series[i-2]['json_path']:
                    data_list_unique_series[i]['ModalityLabel'] = 'phase2'
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be fmap/phase2 because "fmap" or "fieldmap" is in SeriesDescription, EchoNumber == 2 in metadata, and the subjectstring "_e2_ph" is in the filename and "_e1_ph" the one two before. Please modify if incorrect'
                elif data_list_unique_series[i]['EchoNumber'] == 2 and '_e2_ph' in data_list_unique_series[i]['json_path'] and '_e1_ph' not in data_list_unique_series[i-2]['json_path']:
                    data_list_unique_series[i]['ModalityLabel'] = 'phasediff'
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be fmap/phasediff because "fmap" or "fieldmap" is in SeriesDescription, EchoNumber == 2 in metadata, and the subjectstring "_e2_ph" is in the filename but "_e1_ph" not in the one two before. Please modify if incorrect'
                else:
                    data_list_unique_series[i]['error'] = 'Acquisition appears to be some form of fieldmap with an EchoNumber, however, unable to determine if it is a magnitude, phase, or phasediff. Please modify if acquisition is desired for BIDS conversion, otherwise the acqusition will not be converted'
                    data_list_unique_series[i]['message'] = data_list_unique_series[i]['error']
                    data_list_unique_series[i]['br_type'] = 'exclude'
                    
            # Spin echo field maps
            else:
                data_list_unique_series[i]['ModalityLabel'] = 'epi'
                data_list_unique_series[i]['message'] = 'Acquisition is believed to be fmap/epi because "fmap" or "fieldmap" is in SeriesDescription, and does not contain metadata info associated with magnitude/phasediff acquisitions. Please modify if incorrect'
                series_entities['direction'] = data_list_unique_series[i]['direction']
            
        # DWI
        elif any('.bvec' in x for x in data_list_unique_series[i]['paths']):
            
            if any(x in SD for x in ['flair','t2spacedafl']):
                data_list_unique_series[i]['DataType'] = 'anat'
                data_list_unique_series[i]['ModalityLabel'] = 'FLAIR'
                data_list_unique_series[i]['message'] = 'Acquisition is believed to be anat/FLAIR because "flair" or "t2spacedafl" is in the SeriesDescription. Please modify if incorrect'

            elif 't2w' in SD:
                data_list_unique_series[i]['DataType'] = 'anat'
                data_list_unique_series[i]['ModalityLabel'] = 'T2w'
                data_list_unique_series[i]['message'] = 'Acquisition is believed to be anat/T2w because "t2w" is in the SeriesDescription. Please modify if incorrect'
            
            elif 'DIFFUSION' not in data_list_unique_series[i]['ImageType']:
                data_list_unique_series[i]['error'] = 'Acquisition has bval and bvec files but does not appear to be dwi/dwi or fmap/epi that work on dwi/dwi acquistions. Please modify if incorrect, otherwise will not convert to BIDS'
                data_list_unique_series[i]['message'] = data_list_unique_series[i]['error']
                data_list_unique_series[i]['br_type'] = 'exclude'
            
            else:    
                # Some "dwi" acquisitions are actually fmap/epi; check for this
                bval = np.loadtxt([x for x in data_list_unique_series[i]['paths'] if 'bval' in x][0])
                if np.max(bval) <= 50 and bval.size < 10:
                    data_list_unique_series[i]['DataType'] = 'fmap'
                    data_list_unique_series[i]['ModalityLabel'] = 'epi'
                    data_list_unique_series[i]['forType'] = 'dwi/dwi'
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be fmap/epi meant for dwi because there are bval & bvec files with the same SeriesNumber, but the max b-values are <= 50 and the number of b-values is less than 10. Please modify if incorrect'
                    series_entities['direction'] = data_list_unique_series[i]['direction']
                elif any(x in SD for x in ['trace','fa','adc']) and not any(x in SD for x in ['dti','dwi','dmri']):
                    data_list_unique_series[i]['error'] = 'Acquisition appears to be a TRACE, FA, or ADC, which are unsupported by ezBIDS and will therefore not be converted'
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be TRACE, FA, or ADC because there are bval & bvec files with the same SeriesNumber, and "trace", "fa", or "adc" are in the SeriesDescription. Please modify if incorrect'
                    data_list_unique_series[i]['br_type'] = 'exclude'
                else:
                    data_list_unique_series[i]['DataType'] = 'dwi'
                    data_list_unique_series[i]['ModalityLabel'] = 'dwi'
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be dwi/dwi because there are bval & bvec files with the same SeriesNumber, "dwi" or "dti" is in the SeriesDescription, and it does not appear to be dwi product data. Please modify if incorrect'
                    series_entities['direction'] = data_list_unique_series[i]['direction']
        
        # DWI derivatives or other non-BIDS diffusion offshoots
        elif any(x in SD for x in ['trace','fa','adc']) and any(x in SD for x in ['dti','dwi','dmri']):
            data_list_unique_series[i]['error'] = 'Acquisition appears to be a TRACE, FA, or ADC, which are unsupported by ezBIDS and will therefore not be converted'
            data_list_unique_series[i]['message'] = 'Acquisition is believed to be TRACE, FA, or ADC because there are bval & bvec files with the same SeriesNumber, and "trace", "fa", or "adc" are in the SeriesDescription. Please modify if incorrect'
            data_list_unique_series[i]['br_type'] = 'exclude'
        
        # Functional bold and phase
        elif any(x in SD for x in ['bold','func','fmri','epi','mri','task','rest']) and 'sbref' not in SD:
            if data_list_unique_series[i]['NumVolumes'] < 50: #ezBIDS uses 50 volumes for exclusion cutoff
                data_list_unique_series[i]['br_type'] = 'exclude'
                data_list_unique_series[i]['error'] = 'Acquisition appears to be func/bold; however, there are < 50 volumes, suggesting a failure/restart, or the acquisition has been misidentified. Please modify if incorrect'
                data_list_unique_series[i]['message'] = data_list_unique_series[i]['error']
            else:
                data_list_unique_series[i]['DataType'] = 'func'
                if any(x in SD for x in ['rest','rsfmri','fcmri']):
                    series_entities['task'] = 'rest'
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be func/bold because "bold","func","fmri","epi","mri", or"task" is in the SeriesDescription (but not "sbref"). Please modify if incorrect'
                if 'MOSAIC' and 'PHASE' in data_list_unique_series[i]['ImageType']:
                    data_list_unique_series[i]['ModalityLabel'] = 'phase'
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be func/phase because "bold","func","fmri","epi","mri", or"task" is in the SeriesDescription (but not "sbref"), and "MOSAIC" and "PHASE" are in the ImageType field of the metadata. Please modify if incorrect'
                else:
                    data_list_unique_series[i]['ModalityLabel'] = 'bold'
                    if data_list_unique_series[i]['EchoNumber']:
                        series_entities['echo'] = data_list_unique_series[i]['EchoNumber']
                        data_list_unique_series[i]['message'] = 'Acquisition is believed to be func/bold because "bold","func","fmri","epi","mri", or"task" is in the SeriesDescription (but not "sbref"). Please modify if incorrect'
                if data_list_unique_series[i]['EchoNumber']:
                    series_entities['echo'] = data_list_unique_series[i]['EchoNumber']
                    data_list_unique_series[i]['message'] = 'Acquisition is believed to be func/bold because "bold","func","fmri","epi","mri", or"task" is in the SeriesDescription (but not "sbref"). Please modify if incorrect'

        # Functional single band reference (sbref)
        elif 'sbref' in SD:
            data_list_unique_series[i]['DataType'] = 'func'
            data_list_unique_series[i]['ModalityLabel'] = 'sbref'
            if 'rest' in SD or 'rsfmri' in SD:
                series_entities['task'] = 'rest'
            if data_list_unique_series[i]['EchoNumber']:
                series_entities['echo'] = data_list_unique_series[i]['EchoNumber']
            data_list_unique_series[i]['message'] = 'Acquisition is believed to be func/sbref because "sbref" is in the SeriesDescription'
        
        # MP2RAGE/UNIT1
        elif 'mp2rage' in SD:
            data_list_unique_series[i]['DataType'] = 'anat'
            try:
                InversionTime = data_list_unique_series[i]['sidecar']['InversionTime']
            except:
                InversionTime = None
            
            if InversionTime:
                data_list_unique_series[i]['ModalityLabel'] = 'MP2RAGE'
                if InversionTime < 1.0:
                    series_entities['inversion'] = 1
                else:
                    series_entities['inversion'] = 2

                # Look for echo number
                if 'EchoNumber' in data_list_unique_series[i]['sidecar']:
                    series_entities['echo'] = data_list_unique_series[i]['sidecar']['EchoNumber']
                
                # Determine part value (mag/phase)
                if '_e2.json' in data_list_unique_series[i]['json_path']:
                    series_entities['part'] = 'phase'
                else:
                    series_entities['part'] = 'mag'

            else: 
                data_list_unique_series[i]['ModalityLabel'] = 'UNIT1'

        # T1w
        elif any(x in SD for x in ['t1w','tfl3d','mprage','spgr','tflmgh']):
            data_list_unique_series[i]['DataType'] = 'anat'
            data_list_unique_series[i]['ModalityLabel'] = 'T1w'
            if 'multiecho' in SD or 'echo' in SD:
                if 'MEAN' not in image_type:
                    series_entities['echo'] = data_list_unique_series[i]['EchoNumber']
            data_list_unique_series[i]['message'] = 'Acquisition is believed to be anat/T1w because "t1w","tfl3d","tfl","mprage", "spgr", or "tflmgh" is in the SeriesDescription. Please modify if incorrect'
        
        # FLAIR
        elif any(x in SD for x in ['flair','t2spacedafl']):
            data_list_unique_series[i]['DataType'] = 'anat'
            data_list_unique_series[i]['ModalityLabel'] = 'FLAIR'
            data_list_unique_series[i]['message'] = 'Acquisition is believed to be anat/FLAIR because "flair" or "t2spacedafl" is in the SeriesDescription. Please modify if incorrect'

        # T2w
        elif any (x in SD for x in ['t2w','t2']) and data_list_unique_series[i]['EchoTime'] > 100: #T2w acquisitions typically have EchoTime > 100ms
            data_list_unique_series[i]['DataType'] = 'anat'
            data_list_unique_series[i]['ModalityLabel'] = 'T2w'
            data_list_unique_series[i]['message'] = 'Acquisition is believed to be anat/T2w because "t2w" or "t2" is in the SeriesDescription and EchoTime > 100ms. Please modify if incorrect'
        
        # Can't discern from SeriesDescription, try using ndim and number of volumes to see if this is a func/bold
        else:
            test = nib.load(data_list_unique_series[i]['nifti_path'])
            if test.ndim == 4 and test.shape[3] >= 50 and not any(x in data_list_unique_series[i]['ImageType'] for x in ['DERIVED','PERFUSION','DIFFUSION','ASL']):
                data_list_unique_series[i]['DataType'] = 'func'
                data_list_unique_series[i]['ModalityLabel'] = 'bold'
                data_list_unique_series[i]['message'] = 'SeriesDescription did not provide hints regarding the type of acquisition; however, it is believed to be a func/bold because it contains >= 50 volumes. Please modify if incorrect'
            
            # Assume not BIDS-compliant acquisition unless user specifies so
            else: 
                data_list_unique_series[i]['error'] = 'Acquisition cannot be resolved. Please determine whether or not this acquisition should be converted to BIDS'
                data_list_unique_series[i]['message'] = 'Acquisition is unknown because there is not enough adequate information, primarily in the SeriesDescription. Please modify if acquisition is desired for BIDS conversion, otherwise the acqusition will not be converted'
                data_list_unique_series[i]['br_type'] = 'exclude'
            
        
        # Combine DataType and ModalityLabel to form br_type variable (needed for internal brainlife.io storage)
        if 'exclude' not in data_list_unique_series[i]['br_type']:
            data_list_unique_series[i]['br_type'] = data_list_unique_series[i]['DataType'] + '/' + data_list_unique_series[i]['ModalityLabel']
        elif 'exclude' in data_list_unique_series[i]['br_type'] and 'localizer' not in data_list_unique_series[i]['br_type']:
            data_list_unique_series[i]['br_type'] = 'exclude'
        else:
            pass
        
        # Set non-normalized anatomicals to exclude
        if 'anat' in data_list_unique_series[i]['br_type'] and not any(x in ['DERIVED','NORM'] for x in data_list_unique_series[i]['ImageType']):
            data_list_unique_series[i]['br_type'] = 'exclude'
            data_list_unique_series[i]['error'] = 'Acquisition is a poor resolution {} (non-normalized); Please check to see if this {} acquisition should be converted to BIDS. Otherwise, this object will not be included in the BIDS output'.format(data_list_unique_series[i]['br_type'], data_list_unique_series[i]['br_type'])
            data_list_unique_series[i]['message'] = data_list_unique_series[i]['error']
    
        # Combine info above into dictionary, which will be displayed to user through the UI
        series_info = {"SeriesDescription": data_list_unique_series[i]['SeriesDescription'],
                       "SeriesNumber": data_list_unique_series[i]['SeriesNumber'],
                       "series_id": data_list_unique_series[i]['series_id'],
                       "EchoTime": data_list_unique_series[i]['EchoTime'],
                       "ImageType": data_list_unique_series[i]['ImageType'],
                       "MultibandAccelerationFactor": data_list_unique_series[i]['MultibandAccelerationFactor'],
                       "entities": series_entities,
                       "type": data_list_unique_series[i]['br_type'],
                       "forType": data_list_unique_series[i]['forType'],
                       "error": data_list_unique_series[i]['error'],
                       "message": data_list_unique_series[i]['message'],
                       "object_indices": []
                        }
        series_list.append(series_info)
        print('Unique data acquisition file {}, Series Description {}, was determined to be {}'.format(data_list_unique_series[i]['nifti_path'], data_list_unique_series[i]['SeriesDescription'], data_list_unique_series[i]['br_type']))
        print('')
        print('')

    return series_list


def modify_objects_info(subject_protocol, series_list, series_seriesID_list):
    '''
    Takes list of dictionaries with key and unique information, and session it to 
    determine the DataType and Modality labels of the unique acquisitions. 
    Other information (e.g. run, acq, ce) will be determined if the data follows 
    the ReproIn naming convention for SeriesDescriptions.

    Parameters
    ----------
    subject_protocol: list
        List of dictionary, containing pertinent information needed 
        for the UI side of ezBIDS
        
    series_list: list
        List of dictionaries containing the series-level info for file naming, 
        such as "acq","run","dir","ce", etc.
        
    series_seriesID_list: list
        List of numeric values, each one linked to a unique acquiistion in the
        series list. This is different from SeriesNumber, and is used to port 
        info from the series-level down to the objects-level.

    Returns
    -------
    subject_protocol: list
        Same as above but with updated information
    '''
    
    # objects_entities_list = []
    section_ID = 0
    objects_data = []
    
    for p in range(len(subject_protocol)):
        
        # Update section_ID information
        if p == 0:
            section_ID += 1
            subject_protocol[p]['section_ID'] = section_ID
        
        elif any(x in subject_protocol[p]['SeriesDescription'] for x in ['localizer','scout']) and not any(x in subject_protocol[p-1]['SeriesDescription'] for x in ['localizer','scout']):
            section_ID += 1
            subject_protocol[p]['section_ID'] = section_ID
        else:
            subject_protocol[p]['section_ID'] = section_ID
            
        
        subject_protocol[p]['headers'] = str(nib.load(subject_protocol[p]['nifti_path']).header).splitlines()[1:]
                
        image = nib.load(subject_protocol[p]['nifti_path'])
        object_img_array = image.dataobj
        if object_img_array.dtype not in ['<i2', '<u2']: # Weird issue where data array is RGB instead of intger
            subject_protocol[p]['exclude'] = True
            subject_protocol[p]['error'] = 'The data array is for this acquisition is improper, likely suggesting some issue with the corresponding DICOMS'
            subject_protocol[p]['message'] = subject_protocol[p]['error']
            subject_protocol[p]['br_type'] = 'exclude'
        else:            
            if subject_protocol[p]['NumVolumes'] > 1:
                object_img_array = image.dataobj[..., 1]
            else:
                object_img_array = image.dataobj[:]
                    
            if not os.path.isfile('{}.png'.format(subject_protocol[p]['nifti_path'][:-7])):            
                
                slice_x = object_img_array[floor(object_img_array.shape[0]/2), :, :]
                slice_y = object_img_array[:, floor(object_img_array.shape[1]/2), :]
                slice_z = object_img_array[:, :, floor(object_img_array.shape[2]/2)]
            
                fig, axes = plt.subplots(1,3, figsize=(9,3))
                for i, slice in enumerate([slice_x, slice_y, slice_z]):
                    axes[i].imshow(slice.T, cmap="gray", origin="lower", aspect="auto")
                    axes[i].axis('off')
                plt.subplots_adjust(wspace=0, hspace=0)
                plt.savefig('{}.png'.format(subject_protocol[p]['nifti_path'][:-7]), bbox_inches='tight')

            
        index = series_seriesID_list.index(subject_protocol[p]['series_id'])
        objects_entities = {'subject': '', 'session': '', 'run': '', 'task': '', 'direction': '', 'acquisition': '', 'ceagent': '', 'echo': '', 'fa': '', 'inversion': '', 'part': ''}
        
        # Make items list (part of objects list)
        items = []
        for item in subject_protocol[p]['paths']:
            if '.bval' in item:
                items.append({'path':item, 'name':'bval'})
            elif '.bvec' in item:
                items.append({'path':item, 'name':'bvec'})
            elif '.json' in item:
                items.append({'path':item, 'name':'json', 'sidecar':subject_protocol[p]['sidecar']})
            elif '.nii.gz' in item:
                items.append({'path':item, 'name':'nii.gz', 'headers':subject_protocol[p]['headers']})

        
        # Remove identifying information from sidecars
        remove_fields = ['SeriesInstanceUID', 'StudyInstanceUID', 
                         'ReferringPhysicianName', 'StudyID', 'PatientName', 
                         'PatientID', 'AccessionNumber', 'PatientBirthDate', 
                         'PatientSex', 'PatientWeight']
        
        for remove in remove_fields:
            if remove in subject_protocol[p]['sidecar']:
                del subject_protocol[p]['sidecar'][remove]
                
        # Provide log output for acquisitions not deemed appropriate for BIDS conversion
        if subject_protocol[p]['exclude'] == True:
            print('')
            print('* {} (sn-{}) not recommended for BIDS conversion: {}'.format(subject_protocol[p]['SeriesDescription'], subject_protocol[p]['SeriesNumber'], subject_protocol[p]['error']))
        
        # Objects-level info for ezBIDS.json
        objects_info = {"series_id": subject_protocol[p]['series_id'],
                "PatientName": subject_protocol[p]['PatientName'],
                "PatientID": subject_protocol[p]['PatientID'],
                "PatientBirthDate": subject_protocol[p]['PatientBirthDate'],
                "AcquisitionDate": subject_protocol[p]['AcquisitionDate'],
                'SeriesNumber': subject_protocol[p]['sidecar']['SeriesNumber'],
                "pngPath": '{}.png'.format(subject_protocol[p]['nifti_path'][:-7]),
                "entities": objects_entities,
                "items": items,
                "analysisResults": {
                    "NumVolumes": subject_protocol[p]['NumVolumes'],
                    "errors": subject_protocol[p]['error'],
                    "filesize": subject_protocol[p]['filesize'],
                    "section_ID": subject_protocol[p]['section_ID']
                },
                "paths": subject_protocol[p]['paths']
              }
        objects_data.append(objects_info)
                            
    return subject_protocol, objects_data
    

##################### Begin ##################### 

print('########################################')
print('Beginning conversion process of dataset')
print('########################################')
print('')

# Load in list
dir_list = pd.read_csv('list', header=None, sep='\n')

# Determine variables data_list, data_list_unique_series, subjectIDs_info, and acquisition_dates
data_list, data_list_unique_series, subjectIDs_info, acquisition_dates = select_unique_data(dir_list)

# Determine series-level info
series_list = identify_series_info(data_list_unique_series)

# participantsColumn portion of ezBIDS.json
participantsColumn = {"sex": {"LongName": "gender", "Description": "generic gender field", "Levels": {"M": "male", "F": "female"}},
                      "age": {"LongName": "age", "Units": "years"}}
    
# Define a few variables that apply across the entire objects level
objects_list = []
# total_objects_indices = 0
subjects = [acquisition_dates[x]['subject'] for x in range(len(acquisition_dates))]
session = [acquisition_dates[x]['session'] for x in range(len(acquisition_dates))]
series_seriesID_list = [series_list[x]['series_id'] for x in range(len(series_list))]

# Loop through all unique subjectIDs
for s in range(len(acquisition_dates)):
    
    if acquisition_dates[s]['session'] == '':
        print('')
        print('')
        print('Beginning conversion process for subject {} protocol acquisitions'.format(acquisition_dates[s]['subject']))
        print('-------------------------------------------------------------------')
        print('')
     
    else:
        print('')
        print('')
        print('Beginning conversion process for subject {}, session {} protocol acquisitions'.format(acquisition_dates[s]['subject'], acquisition_dates[s]['session']))
        print('-------------------------------------------------------------------')
        print('')
    
    # Get initial subject_protocol list from subjectsetting by subject/sessions
    subject_protocol = [x for x in data_list if x['subject'] == acquisition_dates[s]['subject'] and x['session'] == acquisition_dates[s]['session']]

    # Update subject_protocol based on object-level checks
    subject_protocol, objects_data = modify_objects_info(subject_protocol, series_list, series_seriesID_list)
    
    objects_list.append(objects_data)    
    
objects_list = [x for y in objects_list for x in y]

# Rename ezBIDS localizer designators to "exclude"
for s in range(len(series_list)):
    if series_list[s]['type'] == 'exclude (localizer)':
        series_list[s]['type'] = 'exclude'
        
    series_list[s]['object_indices'] = [x for x in range(len(objects_list)) if objects_list[x]['series_id'] == series_list[s]['series_id']]

# Convert infor to dictionary
ezBIDS = {"subjects": subjectIDs_info,
          "participantsColumn": participantsColumn,
          "series": series_list,
          "objects": objects_list
          }

# Write dictionary to ezBIDS.json
ezBIDS_file_name = 'ezBIDS.json'
with open(ezBIDS_file_name, 'w') as fp: 
    json.dump(ezBIDS, fp, indent=3) 


                

            
                
    
    
    


    
    
    
    
    
    

    
