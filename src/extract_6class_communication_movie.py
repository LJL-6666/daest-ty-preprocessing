#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 output/communication 和 output/movie 的逐被试 pkl 中提取 6 分类 19 视频数据，
合并为两个单文件，保存到 6_communication 和 6_movie（与 extract_6class_clisa 类似的处理）。

6 分类与视频 ID 对应关系（与 extract_6class_clisa 一致）:
  Anger:        1,2,3   → 类别 0
  Disgust:      4,5,6   → 类别 1
  Neutral:      13,14,15,16 → 类别 2
  Inspiration:  20,21,22   → 类别 3
  Joy:          23,24,25   → 类别 4
  Tenderness:   26,27,28   → 类别 5

输入: output/communication/*.pkl, output/movie/*.pkl
      支持两种格式: (28, 31, 7500) 或 (32, 210000)（32=31通道+1触发，210000=28*7500）
输出: output/6_communication/data_6class_communication.pkl
      output/6_movie/data_6class_movie.pkl
      每个文件包含: {'data': (n_subs, 19, 31, 7500), 'subject_ids': list}
"""
import os
import pickle as pkl
import numpy as np

# 6 分类使用的 19 个视频 ID（与 extract_6class_clisa、建模端 config_6class 一致）
VIDEO_IDS_6CLASS = [1, 2, 3, 4, 5, 6, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 27, 28]
IDX_6CLASS = [vid - 1 for vid in VIDEO_IDS_6CLASS]

N_VIDEOS = 28
N_CH = 31
N_T = 7500
# 常规 EEG 保存格式: (32, 28*7500) = (31 通道 + 1 触发, 210000)
CONCAT_SHAPE = (N_CH + 1, N_VIDEOS * N_T)


def _subject_sort_key(name):
    """pkl 文件名排序：002.pkl -> 2, 018.pkl -> 18"""
    base = name.replace('.pkl', '')
    return int(base) if base.isdigit() else 9999


def _to_videos_channels_time(data):
    """
    将 pkl 数据统一为 (28, 31, 7500)。
    支持: (28, 31, 7500) 直接使用; (32, 210000) 按段拆成 (28, 31, 7500)。
    """
    if not hasattr(data, 'shape'):
        return None
    shp = data.shape
    if len(shp) == 3 and shp[0] == N_VIDEOS and shp[1] == N_CH and shp[2] == N_T:
        return data
    if len(shp) == 2 and shp[0] == CONCAT_SHAPE[0] and shp[1] == CONCAT_SHAPE[1]:
        # (32, 210000) -> 每 7500 列为一视频，取前 31 行
        segments = []
        for i in range(N_VIDEOS):
            seg = data[:N_CH, i * N_T : (i + 1) * N_T]  # (31, 7500)
            segments.append(seg)
        return np.stack(segments, axis=0)  # (28, 31, 7500)
    return None


def extract_and_save_one_task(src_dir, out_path, task_name):
    """
    从 src_dir 下所有 *.pkl 读取，统一为 (28, 31, 7500)，按 6 分类取 19 段，
    合并为 (n_subs, 19, 31, 7500) 并保存到 out_path。
    """
    if not os.path.isdir(src_dir):
        print(f"  跳过 {task_name}: 目录不存在 {src_dir}")
        return
    files = sorted(
        [f for f in os.listdir(src_dir) if f.endswith('.pkl')],
        key=lambda f: _subject_sort_key(f),
    )
    if not files:
        print(f"  跳过 {task_name}: 无 .pkl 文件")
        return

    valid_subject_ids = []
    list_19 = []
    for f in files:
        pkl_path = os.path.join(src_dir, f)
        try:
            with open(pkl_path, 'rb') as fp:
                data = pkl.load(fp)
        except Exception as e:
            print(f"  警告: 读取失败 {pkl_path}: {e}")
            continue
        data_3d = _to_videos_channels_time(data)
        if data_3d is None:
            print(f"  警告: 形状不支持 {pkl_path} shape={getattr(data, 'shape', 'N/A')}")
            continue
        data_19 = data_3d[IDX_6CLASS, :, :]  # (19, 31, 7500)
        list_19.append(data_19)
        valid_subject_ids.append(f.replace('.pkl', ''))

    if not list_19:
        print(f"  跳过 {task_name}: 无有效数据")
        return

    data_all = np.stack(list_19, axis=0)  # (n_subs, 19, 31, 7500)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out_dict = {'data': data_all, 'subject_ids': valid_subject_ids}
    with open(out_path, 'wb') as fp:
        pkl.dump(out_dict, fp)
    print(f"  {task_name}: 已保存 {out_path}")
    print(f"    data.shape = {data_all.shape}, subject_ids 数量 = {len(valid_subject_ids)}")


def main():
    OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), 'output')
    COMMUNICATION_DIR = os.path.join(OUTPUT_ROOT, 'communication')
    MOVIE_DIR = os.path.join(OUTPUT_ROOT, 'movie')
    OUT_6CLASS_COMMUNICATION_DIR = os.path.join(OUTPUT_ROOT, '6_communication')
    OUT_6CLASS_MOVIE_DIR = os.path.join(OUTPUT_ROOT, '6_movie')
    OUT_FILE_COMMUNICATION = os.path.join(OUT_6CLASS_COMMUNICATION_DIR, 'data_6class_communication.pkl')
    OUT_FILE_MOVIE = os.path.join(OUT_6CLASS_MOVIE_DIR, 'data_6class_movie.pkl')

    print("提取 6 分类常规 EEG 数据（communication / movie）并合并为单文件")
    print("  6 分类视频 ID:", VIDEO_IDS_6CLASS)
    print("  输出目录: 6_communication, 6_movie")
    print()

    extract_and_save_one_task(COMMUNICATION_DIR, OUT_FILE_COMMUNICATION, "6_communication")
    extract_and_save_one_task(MOVIE_DIR, OUT_FILE_MOVIE, "6_movie")

    print("\n完成。")


if __name__ == '__main__':
    main()
