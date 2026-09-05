#!/usr/bin/env python3
"""
TY 标准脑电预处理
支持 data.bdf+evt.bdf 与 data_raw.fif 两种格式
输入: 原始脑电 .bdf 文件（通过 DAEST_DATA_ROOT 环境变量指定）
"""
import os
import argparse
import copy
from glob import glob

import numpy as np
import pandas as pd
import mne

from Preprocessing_tongyong import (
    Preprocessing,
    unit_check,
    inter_impedance_inspect,
    data_concat,
    eeg_save,
    channel_modify,
)

parser = argparse.ArgumentParser(description='whether to implement clisa')
parser.add_argument('--clisa-or-not', default='no', type=str,
                    help='implement the clisa preprocessing step, yes or no')
parser.add_argument('--task-type', default='both', type=str,
                    help='which task to process: communication, movie, or both')
parser.add_argument('--no-skip', action='store_true',
                    help='do not skip already processed subjects (reprocess all)')
args = parser.parse_args()
clisa_or_not = args.clisa_or_not
task_type = args.task_type
skip_processed = not args.no_skip


def _padded_id(subject_id):
    """与 eeg_save 一致的 ID 格式化"""
    s = str(subject_id)
    if len(s) == 1:
        return '00' + s
    if len(s) == 2:
        return '0' + s
    return s


def _output_exists(subject_id, save_dir, clisa_save_dir=None):
    """
    检查该任务是否已有输出（跳过已处理）
    如果 clisa_save_dir 不为 None，则同时检查 CLISA 输出是否存在
    """
    pkl_name = _padded_id(subject_id) + '.pkl'
    regular_exists = os.path.exists(os.path.join(save_dir, pkl_name))

    if clisa_save_dir is None:
        return regular_exists
    else:
        clisa_exists = os.path.exists(os.path.join(clisa_save_dir, pkl_name))
        return regular_exists and clisa_exists


def read_video_order_from_csv(questionnaire_dir, subject_id, task_name='exp1'):
    """
    从问卷CSV文件中读取视频播放顺序

    参数:
        questionnaire_dir: 问卷数据根目录
        subject_id: 受试者ID
        task_name: 任务名称 'exp1' (交流) 或 'exp0' (电影)

    返回:
        video_order: 视频播放顺序数组 (videoIndex列)
    """
    subject_questionnaire_dir = os.path.join(questionnaire_dir, str(subject_id))

    if not os.path.exists(subject_questionnaire_dir):
        raise FileNotFoundError(f"Questionnaire directory not found for subject {subject_id}")

    # 查找对应任务的rating.csv文件
    rating_files = glob(os.path.join(subject_questionnaire_dir, f'{task_name}_*_rating.csv'))

    if len(rating_files) == 0:
        raise FileNotFoundError(f"No {task_name} rating CSV file found for subject {subject_id}")

    rating_file = rating_files[0]

    # 读取CSV文件
    df = pd.read_csv(rating_file)

    # 获取videoIndex列（第一列）
    if 'videoIndex' not in df.columns:
        raise ValueError(f"videoIndex column not found in {rating_file}")

    video_order = df['videoIndex'].values
    video_order = video_order.astype(int)

    return video_order


def _get_data_files_in_folder(folder_path):
    """
    获取任务文件夹中的数据文件列表（支持多 BDF 合并）
    优先 data_raw.fif，否则收集 data*.bdf 按名字排序（data.bdf, data.1.bdf, ...）
    """
    fif_path = os.path.join(folder_path, 'data_raw.fif')
    if os.path.exists(fif_path):
        return ['fif', [fif_path]]

    bdf_files = glob(os.path.join(folder_path, 'data*.bdf'))
    bdf_files = [f for f in bdf_files if 'evt' not in os.path.basename(f).lower()]
    # 按 data.bdf, data.1.bdf, data.2.bdf 顺序
    def _bdf_sort_key(p):
        b = os.path.basename(p)
        if b == 'data.bdf':
            return (0,)
        if b.startswith('data.') and b.endswith('.bdf'):
            try:
                n = int(b[5:-4])
                return (1, n)
            except ValueError:
                return (2, b)
        return (2, b)
    bdf_files = sorted(bdf_files, key=_bdf_sort_key)
    if bdf_files:
        return ['bdf', bdf_files]
    return [None, []]


def _get_annotations_from_folder(folder_path, fmt='auto'):
    """从文件夹获取 annotations，支持 BDF 和 FIF 两种格式"""
    fif_path = os.path.join(folder_path, 'data_raw.fif')
    evt_path = os.path.join(folder_path, 'evt.bdf')

    if os.path.exists(fif_path):
        raw = mne.io.read_raw_fif(fif_path, preload=False, verbose=False)
        if raw.annotations is None or len(raw.annotations) == 0:
            raise RuntimeError(f"FIF 文件中无 annotations: {fif_path}")
        return raw.annotations
    if os.path.exists(evt_path):
        return mne.read_annotations(evt_path)
    raise FileNotFoundError(f"未找到事件文件: 需要 data_raw.fif 或 evt.bdf")


def read_data_new(folder_path):
    """
    读取数据，支持：
    - data_raw.fif（单文件）
    - data.bdf / data.1.bdf / ... 多个 BDF 合并 + evt.bdf
    使用事件标记 21(开始) 22(结束)
    """
    fmt, files = _get_data_files_in_folder(folder_path)
    if not files:
        raise FileNotFoundError(f"未找到数据: {folder_path}")

    if fmt == 'fif':
        rawdata = mne.io.read_raw_fif(files[0], preload=True, verbose=False)
    elif fmt == 'bdf':
        if len(files) == 1:
            rawdata = mne.io.read_raw_bdf(files[0], preload=True, verbose=False)
        else:
            raws = [mne.io.read_raw_bdf(f, preload=False, verbose=False) for f in files]
            rawdata = mne.concatenate_raws(raws, verbose=False)
            rawdata.load_data()
            print(f"  Merged {len(files)} BDF files: {[os.path.basename(f) for f in files]}")
    else:
        raise FileNotFoundError(f"未找到数据: {folder_path}")

    rawdata, unit = unit_check(rawdata)
    fs = rawdata.info['sfreq']

    ann = _get_annotations_from_folder(folder_path)
    onset_sec = np.array(ann.onset)
    duration_sec = np.array(ann.duration)
    trigger = np.array([str(x) for x in ann.description])
    print(f"  Original trigger events: {np.unique(trigger)}")

    onset = np.array([int(x * fs) for x in onset_sec])
    duration = np.array([int(x * fs) for x in duration_sec])

    trigger, onset, duration, impedance = inter_impedance_inspect(
        trigger, onset, duration
    )

    trigger_numeric = []
    for t in trigger:
        try:
            trigger_numeric.append(int(float(t)))
        except (ValueError, TypeError):
            trigger_numeric.append(-1)
    trigger = np.array(trigger_numeric)

    return trigger, onset, duration, rawdata, [unit, impedance]


def process_single_task(rawdata, trigger, onset, duration, video_order,
                       task_start_event=21, task_end_event=22,
                       task_index=0, clisa_or_not='no'):
    """
    处理单个任务的数据

    参数:
        rawdata: 原始EEG数据
        trigger: 事件触发器
        onset: 事件开始时间
        duration: 事件持续时间
        video_order: 视频播放顺序
        task_start_event: 任务开始事件 (21)
        task_end_event: 任务结束事件 (22)
        task_index: 任务索引 (0=第一个任务, 1=第二个任务)
        clisa_or_not: 是否处理CLISA数据

    返回:
        eeg_Data_saved: 处理后的EEG数据
        eeg_clisa: CLISA数据 (如果需要)
    """
    frequency = rawdata.info['sfreq']
    events = np.transpose(np.vstack((np.vstack((onset, duration)), trigger)))

    # 找到所有21和22的位置
    start_positions = np.where(trigger == task_start_event)[0]
    end_positions = np.where(trigger == task_end_event)[0]

    print(f"  Found {len(start_positions)} start events (21) and {len(end_positions)} end events (22)")

    # 以 event 22 为锚点创建 epoch（tmin=-30, tmax=0），故 21-22 不配对时仍可用 22
    # 如被试19：27个21、28个22（首个21缺失）→ 用28个22创建28个epoch
    if len(start_positions) != len(end_positions):
        print(f"  Warning: 21-22 mismatch, using event 22 as anchor ({len(end_positions)} trials)")

    n_end = len(end_positions)
    if n_end < 20:
        print(f"  Error: Too few end events ({n_end})")
        return None, None

    # 根据 task_index 选择对应的 22 事件范围
    # 双任务(≥50个22): task 0 = 前28, task 1 = 后28
    # 单任务: task 0 = 全部
    if n_end >= 50:
        if task_index == 0:
            pair_start, pair_end = 0, 28
        elif task_index == 1:
            pair_start, pair_end = 28, min(56, n_end)
        else:
            pair_start, pair_end = 0, min(28, n_end)
    else:
        if task_index == 0:
            pair_start, pair_end = 0, min(28, n_end)
        else:
            print(f"  Warning: Task {task_index} not found in single-task data")
            return None, None

    task_end_positions = end_positions[pair_start:pair_end]
    print(f"  Task {task_index}: using event 22 at indices {pair_start}-{pair_end-1} ({len(task_end_positions)} epochs)")

    # 为每个21-22对创建epochs
    # 方法：使用event 22，向前取30秒（因为原代码期望30秒数据）
    original_raw = rawdata.copy()

    # 构建只包含当前任务的22事件的events数组
    # MNE 格式: [sample_index, duration_in_samples, event_id]
    # onset 已在 read_data_new 中转为样本数
    task_events_list = []
    for end_pos_idx in task_end_positions:
        sample_idx = int(onset[end_pos_idx])
        duration_samples = int(duration[end_pos_idx])
        task_events_list.append([sample_idx, duration_samples, task_end_event])

    task_events = np.array(task_events_list, dtype=int)

    try:
        # 使用event 22，向前取30秒
        epochs = mne.Epochs(original_raw, task_events, event_id=task_end_event,
                           tmin=-30, tmax=0, preload=True)
        print(f"  Created {len(epochs)} epochs (30s each, ending at event 22)")
    except Exception as e:
        print(f"  Error creating epochs: {e}")
        return None, None

    # 检查视频数量和video_order的匹配
    n_epochs = len(epochs)

    if n_epochs == 0:
        print(f"  Error: All epochs were dropped due to data quality issues")
        print(f"  This subject's data cannot be processed (likely recording interrupted or extreme artifacts)")
        return None, None
    n_videos = min(n_epochs, len(video_order))

    if len(video_order) != n_epochs:
        print(f"  Warning: Video order length ({len(video_order)}) != epochs ({n_epochs})")
        print(f"  Will process {n_videos} videos")

    eeg_Data_saved = None
    eeg_clisa = None if clisa_or_not == 'no' else None

    for index in range(n_videos):
        video = video_order[index]

        print(f"    Processing video {index+1}/{n_videos}: videoIndex={video}")

        try:
            # The final 30s trial
            processed_epoch_ = Preprocessing(epochs[index])
            processed_epoch_.down_sample(250)
            processed_epoch_.band_pass_filter(0.05, 47)
            processed_epoch_.bad_channels_interpolate(thresh1=3, proportion=0.3)
            processed_epoch_.eeg_ica()

            if clisa_or_not == 'yes':
                processed_epoch_clisa = copy.deepcopy(processed_epoch_)
                processed_epoch_clisa.band_pass_filter(4, 47)
                processed_epoch_clisa.average_ref()
                eeg_clisa = data_concat(eeg_clisa, processed_epoch_clisa.raw.get_data(), video)

            processed_epoch_.average_ref()

            # Save the data
            eeg_Data_saved = data_concat(eeg_Data_saved, processed_epoch_.raw.get_data(), video)

        except Exception as e:
            print(f"    Error processing video {index}: {e}")
            continue

    return eeg_Data_saved, eeg_clisa


def _count_22_in_folder(folder_path):
    """统计文件夹内事件22数量，支持 BDF 和 FIF"""
    try:
        ann = _get_annotations_from_folder(folder_path)
        return int(np.sum(np.array([str(x) for x in ann.description]) == '22'))
    except Exception:
        return 0


def _has_data_in_folder(folder_path):
    """检查文件夹是否有数据文件（含多 BDF）"""
    if os.path.exists(os.path.join(folder_path, 'data_raw.fif')):
        return True
    bdf_files = [f for f in glob(os.path.join(folder_path, 'data*.bdf'))
                 if 'evt' not in os.path.basename(f).lower()]
    return len(bdf_files) > 0


if __name__ == '__main__':
    # 数据路径（标准脑电）
    DAEST_DATA_ROOT = os.environ.get("DAEST_DATA_ROOT", "")
    eeg_data_dir = os.path.join(DAEST_DATA_ROOT, 'data-tongyong/原始数据/脑电近红外/标准脑电')
    questionnaire_dir = os.path.join(DAEST_DATA_ROOT, 'data-tongyong/原始数据/问卷')
    save_dir_base = os.environ.get("DAEST_PREP_ROOT", "./output")

    save_dir_communication = os.path.join(save_dir_base, 'communication')
    save_dir_movie = os.path.join(save_dir_base, 'movie')
    os.makedirs(save_dir_communication, exist_ok=True)
    os.makedirs(save_dir_movie, exist_ok=True)

    if clisa_or_not == 'yes':
        clisa_save_dir_communication = os.path.join(save_dir_base, 'clisa_communication')
        clisa_save_dir_movie = os.path.join(save_dir_base, 'clisa_movie')
        os.makedirs(clisa_save_dir_communication, exist_ok=True)
        os.makedirs(clisa_save_dir_movie, exist_ok=True)
        print('Also do the preprocess for CLISA.')

    subject_dirs = glob(os.path.join(eeg_data_dir, '*'))
    subject_ids = sorted(
        [os.path.basename(d) for d in subject_dirs if os.path.isdir(d)],
        key=lambda x: int(x) if str(x).isdigit() else 9999,
    )
    print(f"找到 {len(subject_ids)} 个受试者")

    # 处理每个受试者
    processed_count = {'communication': 0, 'movie': 0}
    error_count = 0

    for idx, sub in enumerate(subject_ids):

        print(f"\n{'='*80}")
        print(f"[{idx+1}/{len(subject_ids)}] Processing subject: {sub}")
        print('='*80)

        try:
            sub_path = os.path.join(eeg_data_dir, sub)

            # 检查数据结构
            subdirs = [d for d in os.listdir(sub_path) if os.path.isdir(os.path.join(sub_path, d))]

            if '交流' in subdirs or '电影' in subdirs:
                # 分离文件夹结构
                print(f"  Structure: Separate folders")

                # 处理交流任务
                if '交流' in subdirs and (task_type in ['communication', 'both']):
                    clisa_dir = clisa_save_dir_communication if clisa_or_not == 'yes' else None
                    if skip_processed and _output_exists(sub, save_dir_communication, clisa_dir):
                        print(f"\n  Skip Communication (already processed)")
                    else:
                        print(f"\n  Processing Communication task...")
                        comm_path = os.path.join(sub_path, '交流')

                        try:
                            trigger, onset, duration, rawdata, [unit, impedance] = read_data_new(comm_path)
                            video_order = read_video_order_from_csv(questionnaire_dir, sub, 'exp1')

                            eeg_data, eeg_clisa = process_single_task(
                                rawdata, trigger, onset, duration, video_order,
                                task_start_event=21, task_end_event=22, task_index=0,
                                clisa_or_not=clisa_or_not
                            )

                            if eeg_data is not None:
                                try:
                                    sub_num = int(sub)
                                    batch = 1 if sub_num < 100 else 2
                                    eeg_data = channel_modify(eeg_data, batch)
                                    if eeg_clisa is not None:
                                        eeg_clisa = channel_modify(eeg_clisa, batch)
                                except:
                                    print(f"  Warning: Cannot determine batch, skipping channel_modify")

                                eeg_save(sub, eeg_data, save_dir_communication)
                                if eeg_clisa is not None:
                                    eeg_save(sub, eeg_clisa, clisa_save_dir_communication)
                                processed_count['communication'] += 1
                                print(f"  ✓ Communication task saved")

                        except Exception as e:
                            print(f"  ✗ Error processing communication task: {e}")

                # 处理电影任务
                if '电影' in subdirs and (task_type in ['movie', 'both']):
                    clisa_dir = clisa_save_dir_movie if clisa_or_not == 'yes' else None
                    if skip_processed and _output_exists(sub, save_dir_movie, clisa_dir):
                        print(f"\n  Skip Movie (already processed)")
                    else:
                        print(f"\n  Processing Movie task...")
                        movie_path = os.path.join(sub_path, '电影')

                        try:
                            trigger, onset, duration, rawdata, [unit, impedance] = read_data_new(movie_path)
                            video_order = read_video_order_from_csv(questionnaire_dir, sub, 'exp0')

                            eeg_data, eeg_clisa = process_single_task(
                                rawdata, trigger, onset, duration, video_order,
                                task_start_event=21, task_end_event=22, task_index=0,
                                clisa_or_not=clisa_or_not
                            )

                            if eeg_data is not None:
                                try:
                                    sub_num = int(sub)
                                    batch = 1 if sub_num < 100 else 2
                                    eeg_data = channel_modify(eeg_data, batch)
                                    if eeg_clisa is not None:
                                        eeg_clisa = channel_modify(eeg_clisa, batch)
                                except:
                                    print(f"  Warning: Cannot determine batch, skipping channel_modify")

                                eeg_save(sub, eeg_data, save_dir_movie)
                                if eeg_clisa is not None:
                                    eeg_save(sub, eeg_clisa, clisa_save_dir_movie)
                                processed_count['movie'] += 1
                                print(f"  ✓ Movie task saved")

                        except Exception as e:
                            print(f"  ✗ Error processing movie task: {e}")

            elif _has_data_in_folder(sub_path):
                # 单文件结构（根目录有 data.bdf 或 data_raw.fif）
                print(f"  Structure: Single file")

                trigger, onset, duration, rawdata, [unit, impedance] = read_data_new(sub_path)

                event_22_count = np.sum(trigger == 22)
                print(f"  Found {event_22_count} task end events")

                if event_22_count >= 50:
                    # 双任务：第一个是交流，第二个是电影
                    print(f"  Detected dual task in single file")

                    # 处理交流任务
                    if task_type in ['communication', 'both']:
                        clisa_dir = clisa_save_dir_communication if clisa_or_not == 'yes' else None
                        if skip_processed and _output_exists(sub, save_dir_communication, clisa_dir):
                            print(f"\n  Skip Communication (already processed)")
                        else:
                            print(f"\n  Processing Communication task (task 0)...")
                            try:
                                video_order = read_video_order_from_csv(questionnaire_dir, sub, 'exp1')
                                eeg_data, eeg_clisa = process_single_task(
                                    rawdata, trigger, onset, duration, video_order,
                                    task_start_event=21, task_end_event=22, task_index=0,
                                    clisa_or_not=clisa_or_not
                                )

                                if eeg_data is not None:
                                    try:
                                        sub_num = int(sub)
                                        batch = 1 if sub_num < 100 else 2
                                        eeg_data = channel_modify(eeg_data, batch)
                                        if eeg_clisa is not None:
                                            eeg_clisa = channel_modify(eeg_clisa, batch)
                                    except:
                                        pass

                                    eeg_save(sub, eeg_data, save_dir_communication)
                                    if eeg_clisa is not None:
                                        eeg_save(sub, eeg_clisa, clisa_save_dir_communication)
                                    processed_count['communication'] += 1
                                    print(f"  ✓ Communication task saved")
                            except Exception as e:
                                print(f"  ✗ Error processing communication task: {e}")

                    # 处理电影任务
                    if task_type in ['movie', 'both']:
                        clisa_dir = clisa_save_dir_movie if clisa_or_not == 'yes' else None
                        if skip_processed and _output_exists(sub, save_dir_movie, clisa_dir):
                            print(f"\n  Skip Movie (already processed)")
                        else:
                            print(f"\n  Processing Movie task (task 1)...")
                            try:
                                video_order = read_video_order_from_csv(questionnaire_dir, sub, 'exp0')
                                eeg_data, eeg_clisa = process_single_task(
                                    rawdata, trigger, onset, duration, video_order,
                                    task_start_event=21, task_end_event=22, task_index=1,
                                    clisa_or_not=clisa_or_not
                                )

                                if eeg_data is not None:
                                    try:
                                        sub_num = int(sub)
                                        batch = 1 if sub_num < 100 else 2
                                        eeg_data = channel_modify(eeg_data, batch)
                                        if eeg_clisa is not None:
                                            eeg_clisa = channel_modify(eeg_clisa, batch)
                                    except:
                                        pass

                                    eeg_save(sub, eeg_data, save_dir_movie)
                                    if eeg_clisa is not None:
                                        eeg_save(sub, eeg_clisa, clisa_save_dir_movie)
                                    processed_count['movie'] += 1
                                    print(f"  ✓ Movie task saved")
                            except Exception as e:
                                print(f"  ✗ Error processing movie task: {e}")

                elif 20 <= event_22_count < 50:
                    # 单任务（约28个视频，假设是交流任务）
                    if task_type in ['communication', 'both']:
                        clisa_dir = clisa_save_dir_communication if clisa_or_not == 'yes' else None
                        if skip_processed and _output_exists(sub, save_dir_communication, clisa_dir):
                            print(f"\n  Skip single task (already processed)")
                        else:
                            print(f"\n  Processing single task (assumed communication)...")
                            try:
                                video_order = read_video_order_from_csv(questionnaire_dir, sub, 'exp1')
                                eeg_data, eeg_clisa = process_single_task(
                                    rawdata, trigger, onset, duration, video_order,
                                    task_start_event=21, task_end_event=22, task_index=0,
                                    clisa_or_not=clisa_or_not
                                )

                                if eeg_data is not None:
                                    try:
                                        sub_num = int(sub)
                                        batch = 1 if sub_num < 100 else 2
                                        eeg_data = channel_modify(eeg_data, batch)
                                        if eeg_clisa is not None:
                                            eeg_clisa = channel_modify(eeg_clisa, batch)
                                    except:
                                        pass

                                    eeg_save(sub, eeg_data, save_dir_communication)
                                    if eeg_clisa is not None:
                                        eeg_save(sub, eeg_clisa, clisa_save_dir_communication)
                                    processed_count['communication'] += 1
                                    print(f"  ✓ Communication task saved")
                            except Exception as e:
                                print(f"  ✗ Error processing communication task: {e}")

            else:
                print(f"  Skip: 无有效数据结构")

        except Exception as e:
            print(f"  ✗ Error processing subject {sub}: {str(e)}")
            error_count += 1
            continue

    print(f"\n{'='*80}")
    print("处理完成!")
    print(f"{'='*80}")
    print(f"成功处理:")
    print(f"  交流任务: {processed_count['communication']} 个受试者")
    print(f"  电影任务: {processed_count['movie']} 个受试者")
    print(f"错误: {error_count} 个受试者")
    print(f"\n输出目录:")
    print(f"  交流任务: {save_dir_communication}")
    print(f"  电影任务: {save_dir_movie}")
    print('='*80)
