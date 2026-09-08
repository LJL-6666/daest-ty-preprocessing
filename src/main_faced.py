#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FACED 预处理主流程（Python/MNE 链路 —— DAEST 主线正确版）

与本仓库归档时的唯一改动：把三处硬编码相对路径改为 DAEST_DATA_ROOT / DAEST_PREP_ROOT
环境变量。信号处理逻辑逐字未动，见 docs/04_版本溯源.md。

链路：
  Data/subXXX/{data.bdf, evt.bdf, After_remarks.mat}
    -> 本脚本 + Preprocessing.py（MNE：250 Hz 重采样 / 0.05-47 Hz / 坏道插值 / ICA / 平均参考）
    -> 按播放顺序 data_concat 拼接 -> subXXX.pkl
    -> src/convert_pkl_to_mat.py -> 0.05-47 Hz_mat/processed_data/subXXX.mat（DAEST 输入）
"""
import os
import numpy as np
import math
import matplotlib.pyplot as plt
from glob import glob

import pandas as pd
import scipy.io as sio
from Preprocessing import *
import hdf5storage
import argparse
import copy

parser = argparse.ArgumentParser(description='whether to implement clisa')
parser.add_argument('--clisa-or-not', default='no', type=str,
                    help='implement the clisa preprocessing step, yes or no')
args = parser.parse_args()
clisa_or_not = args.clisa_or_not


if __name__ == '__main__':

    DAEST_DATA_ROOT = os.environ.get('DAEST_DATA_ROOT', '')
    FACED_ROOT = os.path.join(DAEST_DATA_ROOT, 'data-faced')
    PREP_ROOT = os.environ.get('DAEST_PREP_ROOT', FACED_ROOT)

    foldPaths = os.path.join(FACED_ROOT, '一些背景', 'Recording_info.csv')
    data_dir = os.path.join(FACED_ROOT, 'Data')
    save_dir = os.path.join(PREP_ROOT, '0.05–47 Hz', 'Processed_data')
    os.makedirs(save_dir, exist_ok=True)
    if clisa_or_not == 'yes':
        clisa_save_dir = os.path.join(PREP_ROOT, '4–47 Hz', 'Clisa_data')
        os.makedirs(clisa_save_dir, exist_ok=True)
        print('Also do the preprocess for CLISA.')

    pd_data = pd.read_csv(foldPaths,low_memory=False)
    sub_info = pd_data['sub']
    sub_batch = pd_data['Cohort']
    print(sub_info)

    # Read the data
    for idx, sub in enumerate(sub_info):

        sub_path = os.path.join(data_dir,sub)
        print("Current processing subject:", sub)
        trigger, onset, duration, rawdata, [unit, impedance, experiments] = read_data(sub_path)

        # read_the_remark_data
        remark_data = hdf5storage.loadmat(os.path.join(sub_path, 'After_remarks.mat'))['After_remark']
        vids = np.squeeze(remark_data['vid'])

        frequency = rawdata.info['sfreq']

        events = np.transpose(np.vstack((np.vstack((onset, duration)), trigger)))

        # The first batch and the second batch have different unit (uV and V)
        original_raw = rawdata.copy()

        # Epochs cutting
        cut_seconds = -30; event_id = 102;
        epochs = mne.Epochs(original_raw, events, event_id=event_id, tmin=cut_seconds, tmax=0, preload=True)

        # Trigger segmentation
        video_trigger_index = np.where((trigger!=0)&(trigger<29))[0]

        eeg_Data_saved = None
        if clisa_or_not == 'yes':
            eeg_clisa = None

        for index,pos in enumerate(video_trigger_index):

            video = trigger[pos]

            # The final 30s trial

            processed_epoch_ = Preprocessing(epochs[index])
            processed_epoch_.down_sample(250)
            # processed_epoch_.band_pass_filter(0.5, 47)
            processed_epoch_.band_pass_filter(0.05, 47)
            processed_epoch_.bad_channels_interpolate(thresh1=3, proportion=0.3)
            processed_epoch_.eeg_ica()

            if clisa_or_not == 'yes':
                processed_epoch_clisa = copy.deepcopy(processed_epoch_)
                processed_epoch_clisa.band_pass_filter(4, 47)
                processed_epoch_clisa.average_ref()
                eeg_clisa = data_concat(eeg_clisa, processed_epoch_clisa.raw.get_data(),video)

            processed_epoch_.average_ref()

            # Save the data
            eeg_Data_saved = data_concat(eeg_Data_saved, processed_epoch_.raw.get_data(), video)

        # Modify the channels
        if int(sub_batch[idx]==1):
            batch = 1
            eeg_Data_saved = channel_modify(eeg_Data_saved, batch)
        elif int(sub_batch[idx]==2):
            batch = 2
            eeg_Data_saved = channel_modify(eeg_Data_saved, batch)
        if clisa_or_not == 'yes':
            eeg_clisa = channel_modify(eeg_clisa, batch)

        # Saved as pkl
        eeg_save(sub, eeg_Data_saved, save_dir)
        if clisa_or_not == 'yes':
            eeg_save(sub, eeg_clisa, clisa_save_dir)

