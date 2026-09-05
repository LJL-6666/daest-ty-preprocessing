#!/usr/bin/env python3
"""
把 0.05–47 Hz/Processed_data 下的每被试 pkl 转成 FACED 可读的 .mat，
支持断点续传（已存在的 .mat 会跳过）、单文件出错不中断。

用法（在 FACED-base 根目录）:
  python scripts/convert_pkl_to_mat.py
"""
import os
import sys
import re
import argparse
import pickle
import numpy as np
import scipy.io as sio

# 保证能 import 到 FACED-base 根目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 路径配置
DAEST_DATA_ROOT = os.environ.get("DAEST_DATA_ROOT", "")
PKL_DIR = os.path.join(DAEST_DATA_ROOT, "data-faced", "0.05–47 Hz", "Processed_data")
OUT_BASE = os.path.join(DAEST_DATA_ROOT, "data-faced", "0.05–47 Hz_mat")
PROCESSED_SUBDIR = "processed_data"


def convert_one(pkl_path, mat_path):
    """单个 pkl → .mat，与 utils.preprocess.FACED_old2new 逻辑一致。"""
    with open(pkl_path, "rb") as f:
        onesub_data = pickle.load(f, encoding="bytes")
    onesub_data = np.asarray(onesub_data)
    # (vid, channel, time) -> (channel, vid*time)
    new_data = np.transpose(onesub_data, (1, 0, 2)).reshape(onesub_data.shape[1], -1)
    n_samples_one = [[30] * onesub_data.shape[0]]
    sio.savemat(mat_path, {"data_all_cleaned": new_data, "n_samples_one": n_samples_one})


def main():
    parser = argparse.ArgumentParser(description="pkl → .mat 供 FACED 使用（支持断点续传）")
    parser.add_argument("--pkl-dir", default=PKL_DIR, help="每被试一个 pkl 的目录")
    parser.add_argument("--out-dir", default=OUT_BASE, help="输出根目录")
    parser.add_argument("--no-resume", action="store_true", help="不续传，全部重新转换")
    args = parser.parse_args()
    old_dir = os.path.abspath(args.pkl_dir)
    out_base = os.path.abspath(args.out_dir)
    new_dir = os.path.join(out_base, PROCESSED_SUBDIR)

    if not os.path.isdir(old_dir):
        print("错误: pkl 目录不存在:", old_dir)
        sys.exit(1)
    os.makedirs(new_dir, exist_ok=True)

    list_files = [f for f in os.listdir(old_dir) if f.endswith(".pkl")]
    list_files = sorted(list_files, key=lambda x: int(re.search(r"\d+", x).group()))
    n_total = len(list_files)
    print("pkl 目录:", old_dir)
    print("输出 .mat 目录:", new_dir)
    print("共", n_total, "个 pkl，开始转换（已存在的 .mat 将跳过）...")

    n_ok = 0
    n_skip = 0
    n_fail = 0
    for idx, fn in enumerate(list_files):
        base_name, _ = os.path.splitext(fn)
        pkl_path = os.path.join(old_dir, fn)
        mat_path = os.path.join(new_dir, f"{base_name}.mat")
        if not args.no_resume and os.path.isfile(mat_path):
            n_skip += 1
            if (idx + 1) % 20 == 0 or idx == 0:
                print(f"  [{idx+1}/{n_total}] 跳过（已存在）: {fn}")
            continue
        try:
            convert_one(pkl_path, mat_path)
            n_ok += 1
            if (idx + 1) % 20 == 0 or (idx + 1) == n_total:
                print(f"  [{idx+1}/{n_total}] 已写: {fn} -> {base_name}.mat")
        except Exception as e:
            n_fail += 1
            print(f"  [{idx+1}/{n_total}] 失败: {fn} 错误: {e}", file=sys.stderr)

    print()
    print("转换结束: 新写", n_ok, "个, 跳过", n_skip, "个, 失败", n_fail, "个")
    n_mat = len([f for f in os.listdir(new_dir) if f.endswith(".mat")])
    print("当前 .mat 总数:", n_mat, "/", n_total)
    if n_mat >= n_total and n_fail == 0:
        print("转换完成。接下来可执行: python train_ext.py data=FACED_05_47 ...")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
