#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 clisa_communication 和 clisa_movie 的逐被试 pkl 中提取 6 分类 19 视频数据，
合并为两个单文件，保存到 6_clisa_communication 和 6_clisa_movie。

6 分类与视频 ID 对应关系（输出 data 第二维 0~18 即以下顺序）:
  Anger:        1,2,3   → 类别 0  (data[:, 0:3, :, :])
  Disgust:      4,5,6   → 类别 1  (data[:, 3:6, :, :])
  Neutral:      13,14,15,16 → 类别 2  (data[:, 6:10, :, :])
  Inspiration:  20,21,22   → 类别 3  (data[:, 10:13, :, :])
  Joy:          23,24,25   → 类别 4  (data[:, 13:16, :, :])
  Tenderness:   26,27,28   → 类别 5  (data[:, 16:19, :, :])

输入: output/clisa_communication/*.pkl, output/clisa_movie/*.pkl（每个 shape 为 (28, 31, 7500)，按视频 ID 升序）
输出: output/6_clisa_communication/data_6class_communication.pkl
      output/6_clisa_movie/data_6class_movie.pkl
      每个文件包含: {'data': (n_subs, 19, 31, 7500), 'subject_ids': list}
"""
import os
import pickle as pkl
import numpy as np

# 6 分类使用的 19 个视频 ID（1-based），顺序即上述 Anger→Disgust→Neutral→Inspiration→Joy→Tenderness
# 必须与建模端 Clisa_6-all/config_6class.py 的 SELECTED_19_VIDEOS 完全一致，勿单独修改
VIDEO_IDS_6CLASS = [1, 2, 3, 4, 5, 6, 13, 14, 15, 16, 20, 21, 22, 23, 24, 25, 26, 27, 28]
# 对应在 (28, 31, 7500) 第一维的 0-based 下标
IDX_6CLASS = [vid - 1 for vid in VIDEO_IDS_6CLASS]

OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), 'output')
CLISA_COMMUNICATION_DIR = os.path.join(OUTPUT_ROOT, 'clisa_communication')
CLISA_MOVIE_DIR = os.path.join(OUTPUT_ROOT, 'clisa_movie')
OUT_6CLASS_COMMUNICATION_DIR = os.path.join(OUTPUT_ROOT, '6_clisa_communication')
OUT_6CLASS_MOVIE_DIR = os.path.join(OUTPUT_ROOT, '6_clisa_movie')
OUT_FILE_COMMUNICATION = os.path.join(OUT_6CLASS_COMMUNICATION_DIR, 'data_6class_communication.pkl')
OUT_FILE_MOVIE = os.path.join(OUT_6CLASS_MOVIE_DIR, 'data_6class_movie.pkl')


def _subject_sort_key(name):
    """pkl 文件名排序：002.pkl -> 2, 018.pkl -> 18"""
    base = name.replace('.pkl', '')
    return int(base) if base.isdigit() else 9999


def extract_and_save_one_task(src_dir, out_path, task_name):
    """
    从 src_dir 下所有 *.pkl 读取 (28, 31, 7500)，按 6 分类取 19 段，合并为 (n_subs, 19, 31, 7500) 并保存到 out_path。
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

    subject_ids = [f.replace('.pkl', '') for f in files]
    list_19 = []
    valid_subject_ids = []
    for f in files:
        pkl_path = os.path.join(src_dir, f)
        try:
            with open(pkl_path, 'rb') as fp:
                data = pkl.load(fp)
        except Exception as e:
            print(f"  警告: 读取失败 {pkl_path}: {e}")
            continue
        if not hasattr(data, 'shape') or len(data.shape) != 3:
            print(f"  警告: 形状异常 {pkl_path} shape={getattr(data, 'shape', 'N/A')}")
            continue
        n_vids, n_ch, n_t = data.shape
        if n_vids < 28:
            print(f"  警告: 视频数不足 28 {pkl_path} -> {n_vids}")
            continue
        data_19 = data[IDX_6CLASS, :, :]  # (19, 31, 7500)
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
    print("提取 6 分类 CLISA 数据并合并为单文件")
    print("  6 分类视频 ID:", VIDEO_IDS_6CLASS)
    print("  输出目录: 6_clisa_communication, 6_clisa_movie")
    print()

    extract_and_save_one_task(CLISA_COMMUNICATION_DIR, OUT_FILE_COMMUNICATION, "6_clisa_communication")
    extract_and_save_one_task(CLISA_MOVIE_DIR, OUT_FILE_MOVIE, "6_clisa_movie")

    print("\n完成。")


if __name__ == '__main__':
    main()
