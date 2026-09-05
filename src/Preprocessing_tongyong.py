# VERSION: Tongyong 31-channel preprocessing
# This is the MNE PLOT VERSION of preprocessing for Tongyong dataset
import matplotlib.pyplot as plt
import mne
import numpy as np
import os
from scipy.signal.windows import hann
from scipy import stats
from mne.viz.topomap import _add_colorbar, plot_topomap, _hide_frame
from mne.preprocessing import ICA
import pickle as pkl
import re
import math
from collections import Counter

# The data put into preprocessing based on 30s
class Preprocessing():

    def __init__(self, raw):
        # Modify the montage
        self.nchns = raw.info['nchan']
        self.freq = raw.info['sfreq']

        # For Tongyong dataset, channels are already correctly named
        # No need to rename like in the original code
        chn_names = raw.info['ch_names']

        # Set standard montage
        montage = mne.channels.make_standard_montage('standard_1020')
        raw.set_montage(montage)

        # Match the corresponding montage to their index
        self.montage_index = dict(zip(np.arange(self.nchns), chn_names))

        # split out the data matrix
        self.raw = raw
        # Ptr operation
        self.data = self.raw.get_data()


    def plot_eeg(self, second):
        self.raw.plot(duration=second, n_channels=self.nchns, clipping=None)

    def plot_sensors(self):
        self.raw.plot_sensors(ch_type='eeg', show_names=True)

    def band_pass_filter(self, l_freq, h_freq):
        # The default filter is a FIR filter,
        # therefore,  the input [l_freq,h_freq] is
        # [lower pass-band edge, higher pass-band edge]
        self.raw.filter(l_freq, h_freq)

    def down_sample(self, n_freq):
        self.raw.resample(n_freq)

    # Should cut the data into pieces than do the interpolation
    def bad_channels_interpolate(self, thresh1=None, thresh2=None, proportion=0.3):
        data = self.raw.get_data()
        # We found that the data shape of epochs is 3 dims
        if len(data.shape) > 2:
            data = np.squeeze(data)
        Bad_chns = []
        value = 0
        # Delete the much larger point
        if thresh1 != None:
            md = np.median(np.abs(data))
            value = np.where(np.abs(data) > (thresh1 * md), 0, 1)[0]
        if thresh2 != None:
            value = np.where((np.abs(data)) > thresh2, 0, 1)[0]
        # Use the standard to pick out the bad channels
        Bad_chns = np.argwhere((np.mean((1-value), axis=0) > proportion))
        if Bad_chns.size > 0:
            self.raw.info['bads'].extend([self.montage_index[str(bad)] for bad in Bad_chns])
            print('Bad channels: ', self.raw.info['bads'])
            self.raw = self.raw.interpolate_bads()
        else:
            print('No bad channel currently')

    # You can manually exclude the ICA elements
    # Our auto preprocessing method is more effective for eye blink removal
    def eeg_ica(self, check_ica=None):
        ica = ICA(max_iter='auto', method='fastica')
        raw_ = self.raw.copy()
        ica.fit(self.raw)
        # Plot different elements of the signals
        eog_indices1, eog_score1 = ica.find_bads_eog(self.raw, ch_name='Fp1')
        eog_indices2, eog_score2 = ica.find_bads_eog(self.raw, ch_name='Fp2')
        eog_indices = list(set(eog_indices1 + eog_indices2))
        ica.exclude = eog_indices

        if check_ica == True:
            print('Already use:', eog_indices)
            ica.plot_sources(raw_)
            ica.plot_components()
            eog_indices = input("Exclude ?")
            eog_indices = eog_indices.split(" ")
            eog_indices = list(map(int, eog_indices))
            ica.exclude = eog_indices

        # Exclude the elements you don't want
        ica.apply(self.raw)

    def average_ref(self):
        self.raw.set_eeg_reference(ref_channels='average')

    def _get_average_psd(self, energy_graph, freq_bands, sample_freq, stft_n=256):
        start_index = int(np.floor(freq_bands[0] / sample_freq * stft_n))
        end_index = int(np.floor(freq_bands[1] / sample_freq * stft_n))
        ave_psd = np.mean(energy_graph[:, start_index - 1:end_index] ** 2, axis=1)
        return ave_psd

    def extract_psd_feature(self, window_size, freq_bands, stft_n=256):
        sample_freq = self.raw.info['sfreq']
        # Ptr operation
        self.data = self.raw.get_data()
        if len(self.data.shape) > 2:
            self.data = np.squeeze(self.data)
        n_channels, n_samples = self.data.shape
        point_per_window = int(sample_freq * window_size)
        window_num = int(n_samples // point_per_window)
        psd_feature = np.zeros((window_num, len(freq_bands), n_channels))

        for window_index in range(window_num):
            start_index, end_index = point_per_window * window_index, point_per_window * (window_index + 1)
            window_data = self.data[:, start_index:end_index]
            hdata = window_data * hann(point_per_window)
            fft_data = np.fft.fft(hdata, n=stft_n)
            energy_graph = np.abs(fft_data[:, 0: int(stft_n / 2)])

            for band_index, band in enumerate(freq_bands):
                band_ave_psd = self._get_average_psd(energy_graph, band, sample_freq, stft_n)
                psd_feature[window_index, band_index, :] = band_ave_psd
        return psd_feature


def data_concat(eegData, videoData: np.array, video: int):
    """
    Concatenate video data with trigger information
    For Tongyong dataset: 31 channels, 250Hz, 30s
    """
    fs = 250
    secs = 30
    n_channels = 31  # Tongyong has 31 channels

    if len(videoData.shape) > 2:
        videoData = np.squeeze(videoData)

    trigger = np.zeros((1, fs * secs))
    trigger[0][0] = video

    print('The shape of current epoch:', videoData.shape)

    # Ensure we have 31 channels
    if videoData.shape[0] != n_channels:
        print(f"Warning: Expected {n_channels} channels, got {videoData.shape[0]}")

    if videoData.shape[1] > fs * secs:
        videoData = videoData[:, -fs*secs:]
    elif videoData.shape[1] < fs * secs:
        raise RuntimeError("The length of epoch is wrong")

    videoData = np.vstack((videoData, trigger))

    if eegData is None:
        eegData = videoData
    else:
        eegData = np.hstack((eegData, videoData))

    return eegData


def eeg_save(subject: str, eegData_trigger: np.array, filepath):
    if len(subject) == 1:
        subject = '00' + subject
    elif len(subject) == 2:
        subject = '0' + subject
    f = open(filepath + '/' + subject + '.pkl', 'wb')
    pkl.dump(eegData_trigger, f)
    f.close()


# DATA INSPECTION
def unit_check(rawdata):
    # The first batch and the second batch have different unit (uV and V)
    original_raw = rawdata.copy()
    # Here can use np.log to make sure the level of unit, V or uV
    data_mean = np.mean(np.abs(original_raw._data))
    unit = 'uV'
    if math.log(np.mean(np.abs(original_raw._data))) < 0:
        print('Unit change :', data_mean)
        original_raw._data = original_raw._data * 1000 * 1000
        unit = 'V'
    return original_raw, unit


def inter_impedance_inspect(trigger, onset, duration):
    """
    阻抗检查。若存在 Start/Stop Impedance：
    - 若仅在末尾：删除后继续
    - 若在中间（如多 BDF 合并时文件分界处）：删除阻抗事件后继续，不直接拒绝
      多 BDF 合并时 evt.bdf 在两文件分界处常有阻抗标记，删除后 21-22 仍可正确对应
    """
    if 'Start Impedance' in [str(t) for t in trigger]:
        # 兼容 trigger 为 str 或 numeric
        is_imp_start = np.array([str(t) == 'Start Impedance' for t in trigger])
        is_imp_stop = np.array([str(t) == 'Stop Impedance' for t in trigger])
        pos = np.where(is_imp_start | is_imp_stop)[0]
        trigger_left = np.delete(trigger[pos[0]:].copy(), [0, 1])
        if trigger_left.size == 0:
            trigger = np.delete(trigger, pos)
            onset = np.delete(onset, pos)
            duration = np.delete(duration, pos)
            print("There is an Impedance in the dataset but at the end")
            impedance = 0
        else:
            # 多 BDF 合并时，阻抗常在分界处，删除后继续（下游会校验 21-22 数量）
            trigger = np.delete(trigger, pos)
            onset = np.delete(onset, pos)
            duration = np.delete(duration, pos)
            print("Impedance in the middle (e.g. multi-BDF boundary), removed and continuing")
            impedance = 0
    else:
        impedance = 1
    return trigger, onset, duration, impedance


# TY 通道重排序：1对1 映射到 FACED 顺序（近似位置算一个，不重复）
# 输出 31 通道，顺序与 FACED 对齐；合并时取 FACED 的对应槽位即可对齐
# 精确: Fp1,Fp2,Fz,F3,F4,F7,F8,Cz,C3,C4,T3,T4,A1,A2,Pz,P3,P4,T5,T6,Oz,O1,O2
# 近似: FCz->FC1, FC3->FC5, FC4->FC6, CP3->CP5, CP4->CP6, TP7->PO3, TP8->PO4, FT8->FC2, FT7->CP1
# 跳过 FACED 槽 30(CP2)，无 TY 近似
# TY_REORDER: 输出位置 i <- TY 原始通道 [reorder[i]]
TY_CHANNEL_REORDER = [
    0, 1, 2, 3, 4, 5, 6, 25, 10, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 27, 28, 23, 24, 26, 29, 30, 9
]
# 合并时 FACED 取这些槽位即可与 TY 对齐: faced_data[:, FACED_ALIGN_INDEX, :]
FACED_ALIGN_INDEX = (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,31)


def channel_modify(data, first_or_second):
    """
    Modify channel order and extract final data.
    TY 输出 31 通道，按 FACED 顺序重排（1对1 近似映射），便于合并时对应。

    Input: data shape (32, N) where last row is trigger
    Output: eegdata shape (n_vids, 31, fs*sec)
    """
    chns = 31
    fs = 250
    sec = 30

    eeg_rows = data[:-1, :]  # (31, N)
    eeg_reordered = eeg_rows[TY_CHANNEL_REORDER, :]  # (31, N)

    video_index = np.where(data[-1, :].T > 0)[0]
    n_vids = len(video_index)

    print(f"  channel_modify: {n_vids} videos, 31 ch (FACED-aligned)")

    eegdata = np.zeros((n_vids, chns, fs * sec))
    video_arange = np.argsort(data[-1, video_index])
    video_arange_index = video_index[video_arange]

    for idx, vid in enumerate(video_arange_index):
        eegdata[idx, :, :] = eeg_reordered[:, vid : vid + fs * sec]

    return eegdata
