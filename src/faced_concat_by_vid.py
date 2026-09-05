#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据视频播放顺序拼接 data-faced 数据集的 .set 段文件，并导出为 EEGLAB .set 格式。
输入：
- EEG 段文件目录：${DAEST_DATA_ROOT}/data-faced/Cleaned_Data 下的 subXXX-YY_RELAX.set
- 播放顺序来源：${DAEST_DATA_ROOT}/data-faced/Data/subXXX/After_remarks.mat 中的 vid 字段
输出：
- 拼接后的 .set：${DAEST_DATA_ROOT}/data-faced/Cleaned_Data-2/subXXX_RELAX_concat.set

实现说明：
- Python 端解析 .mat 获取每个被试（subXXX）的 vid 序号（视频播放次序），并据此为该被试的所有 trial(YY) 重新排序
- 通过调用 MATLAB + EEGLAB（无界面）按排序后的文件列表进行加载与合并（pop_loadset + eeg_store + pop_mergeset），最终 pop_saveset 输出为 .set

依赖：
- Python 标准库（os, re, glob, subprocess, argparse, logging）
- SciPy（scipy.io.loadmat）用于读取 .mat
- 系统需安装 MATLAB，且本地已存在 EEGLAB 代码目录（默认 ${EEGLAB_DIR}）
"""
import os
import re
import glob
import argparse
import logging
import subprocess
from typing import Dict, List, Tuple

try:
    from scipy.io import loadmat  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError("需要安装 SciPy 以读取 .mat 文件：pip install scipy")

# 路径配置
DAEST_DATA_ROOT = os.environ.get("DAEST_DATA_ROOT", "")
BASE_DIR = os.path.join(DAEST_DATA_ROOT, "data-faced")
CLEANED_DIR = os.path.join(BASE_DIR, "Cleaned_Data")
RAW_DATA_DIR = os.path.join(BASE_DIR, "Data")
OUTPUT_DIR = os.path.join(BASE_DIR, "Cleaned_Data-2")
EEGLAB_DIR = os.environ.get("EEGLAB_DIR", "")

# 文件名模式：subNNN-YY_RELAX.set
SEGMENT_PATTERN = re.compile(r"^(sub\d+)-(\d+)_RELAX\.set$")


def find_subjects() -> List[str]:
    """在 RAW_DATA_DIR 中查找形如 subXXX 的被试目录。"""
    subs = []
    if not os.path.isdir(RAW_DATA_DIR):
        logging.error("RAW_DATA_DIR 不存在：%s", RAW_DATA_DIR)
        return subs
    for name in sorted(os.listdir(RAW_DATA_DIR)):
        if re.fullmatch(r"sub\d{3}", name) and os.path.isdir(os.path.join(RAW_DATA_DIR, name)):
            subs.append(name)
    return subs


def collect_segments_for_subject(subject: str) -> Dict[int, str]:
    """收集某被试在 CLEANED_DIR 下的所有段文件，返回 trial(YY) -> 绝对路径 的映射。"""
    mapping: Dict[int, str] = {}
    if not os.path.isdir(CLEANED_DIR):
        logging.error("CLEANED_DIR 不存在：%s", CLEANED_DIR)
        return mapping

    pattern = os.path.join(CLEANED_DIR, f"{subject}-*_RELAX.set")
    for path in sorted(glob.glob(pattern)):
        fname = os.path.basename(path)
        m = SEGMENT_PATTERN.match(fname)
        if not m:
            logging.warning("忽略无法匹配模式的文件：%s", fname)
            continue
        sub_id, trial_str = m.groups()
        if sub_id != subject:
            continue
        try:
            trial = int(trial_str)
        except ValueError:
            logging.warning("试次号解析失败：%s", fname)
            continue
        mapping[trial] = os.path.abspath(path)
    return mapping


def get_vid_order_from_mat(subject: str) -> List[Tuple[int, int]]:
    """读取 After_remarks.mat，返回列表 [(trial_index, vid_index)]，trial_index 从 1 开始。
    支持两种结构：
    1) 顶层存在 'vid' / 可选 'trial' 数组
    2) 顶层存在 'After_remark'，为 mat_struct 数组，包含字段 'trial' 和 'vid'
    """
    mat_path = os.path.join(RAW_DATA_DIR, subject, "After_remarks.mat")
    if not os.path.isfile(mat_path):
        raise FileNotFoundError(f"未找到 {mat_path}")

    mat = loadmat(mat_path, squeeze_me=True, struct_as_record=False)

    # 优先处理 'After_remark' 结构（每条 trial 的结构体，内含 trial 与 vid 字段）
    if "After_remark" in mat:
        arr = mat["After_remark"]
        # 统一为可迭代列表
        if hasattr(arr, "tolist"):
            items = arr.tolist()
        else:
            items = list(arr)
        pairs: List[Tuple[int, int]] = []

        def to_int_scalar(x):
            # 将可能的数组/嵌套/标量转换为 int
            try:
                # 处理 numpy 标量或 0d 数组
                import numpy as np  # 局部导入，避免全局依赖
                if isinstance(x, np.ndarray):
                    try:
                        x = x.item()
                    except Exception:
                        if x.size > 0:
                            x = x.flat[0]
                        else:
                            return None
            except Exception:
                pass
            if isinstance(x, (list, tuple)):
                x = x[0] if len(x) > 0 else None
            if x is None:
                return None
            try:
                return int(round(float(x)))
            except Exception:
                return None

        for elem in items:
            # 支持 mat_struct（有属性）、dict-like 或 numpy.void（字段访问）
            t = getattr(elem, "trial", None)
            v = getattr(elem, "vid", None)
            if t is None or v is None:
                # dict-like
                if isinstance(elem, dict):
                    t = elem.get("trial")
                    v = elem.get("vid")
                else:
                    # numpy.void 或支持键访问的对象
                    try:
                        t = elem["trial"]
                        v = elem["vid"]
                    except Exception:
                        pass
            tt = to_int_scalar(t)
            vv = to_int_scalar(v)
            if tt is not None and vv is not None:
                pairs.append((tt, vv))
        if pairs:
            return pairs
        # 若解析失败则继续尝试顶层 'vid'/'trial'

    # 顶层数组形式解析（与 tongyong 类似）
    if "vid" not in mat:
        raise KeyError(f"{mat_path} 中未找到 'vid' 字段")

    vid = mat["vid"]
    # 转为一维整数列表
    if hasattr(vid, "tolist"):
        vid_list = vid.tolist()
    else:
        vid_list = list(vid)

    flat_vid: List[int] = []
    for v in vid_list:
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            for vv in v:
                if vv is None:
                    continue
                flat_vid.append(int(round(float(vv))))
        else:
            flat_vid.append(int(round(float(v))))

    # 试次索引
    if "trial" in mat:
        trial = mat["trial"]
        if hasattr(trial, "tolist"):
            trial_list = trial.tolist()
        else:
            trial_list = list(trial)
        flat_trial: List[int] = []
        for t in trial_list:
            if t is None:
                continue
            if isinstance(t, (list, tuple)):
                for tt in t:
                    if tt is None:
                        continue
                    flat_trial.append(int(round(float(tt))))
            else:
                flat_trial.append(int(round(float(t))))
        n = min(len(flat_trial), len(flat_vid))
        trial_indices = flat_trial[:n]
        flat_vid = flat_vid[:n]
    else:
        trial_indices = list(range(1, len(flat_vid) + 1))

    return list(zip(trial_indices, flat_vid))


def build_ordered_file_list(segments: Dict[int, str], trial_vid_pairs: List[Tuple[int, int]]) -> Tuple[List[str], List[int]]:
    """依据 (trial, vid) 对，将段文件按 vid 升序排序并返回路径列表及对应的 vid 序列。"""
    # 仅保留在 segments 存在的 trial
    filtered = [(trial, vid) for trial, vid in trial_vid_pairs if trial in segments]
    missing_trials = [trial for trial, _ in trial_vid_pairs if trial not in segments]
    if missing_trials:
        logging.warning("缺失段文件的试次：%s", missing_trials)

    # 按 vid 升序
    filtered.sort(key=lambda x: x[1])
    ordered_files = [segments[trial] for trial, _vid in filtered]
    ordered_vids = [vid for _trial, vid in filtered]
    return ordered_files, ordered_vids


def run_matlab_concat(file_list: List[str], out_set_path: str, vids: List[int]) -> None:
    """调用 MATLAB + EEGLAB 合并 file_list 中的 .set 文件并保存到 out_set_path，并在合并后的 EEG.event 中写入每段的视频序号。"""
    if not file_list:
        raise ValueError("file_list 为空，无法拼接")
    if not vids or len(vids) != len(file_list):
        raise ValueError("vids 与 file_list 长度不一致，无法写入视频序号事件")

    out_dir = os.path.dirname(out_set_path)
    out_name = os.path.basename(out_set_path)
    os.makedirs(out_dir, exist_ok=True)

    # 构造 MATLAB -batch 命令字符串
    file_list_str = ", ".join([f"'{p}'" for p in file_list])
    vids_str = " ".join([str(v) for v in vids])
    matlab_cmd = (
        f"addpath(genpath('{EEGLAB_DIR}')); "
        f"[ALLEEG, EEG, CURRENTSET] = eeglab; "
        f"fileList = {{{file_list_str}}}; "
        f"vids = [{vids_str}]; "
        f"ALLEEG = []; EEG = []; CURRENTSET = 0; segLens = zeros(1, numel(fileList)); "
        f"for i = 1:numel(fileList), "
        f"EEG = pop_loadset(fileList{{i}}); "
        f"segLens(i) = EEG.pnts; "
        f"[ALLEEG, EEG, CURRENTSET] = eeg_store(ALLEEG, EEG, i); "
        f"end; "
        f"EEG = pop_mergeset(ALLEEG, 1:numel(fileList), 0); "
        f"EEG = eeg_checkset(EEG); "
        f"startSamples = zeros(1, numel(fileList)); startSamples(1) = 1; "
        f"for i = 2:numel(fileList), startSamples(i) = startSamples(i-1) + segLens(i-1); end; "
        f"for i = 1:numel(fileList), "
        f"EEG.event(end+1).type = 'videoStart'; "
        f"EEG.event(end).latency = startSamples(i); "
        f"EEG.event(end).videoIndex = vids(i); "
        f"end; "
        f"EEG = eeg_checkset(EEG, 'eventconsistency'); "
        f"pop_saveset(EEG, 'filename', '{out_name}', 'filepath', '{out_dir}'); "
        f"exit;"
    )

    logging.info("启动 MATLAB 进行 .set 拼接并写入视频序号事件：输出 -> %s", out_set_path)
    completed = subprocess.run(
        ["matlab", "-batch", matlab_cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        logging.error("MATLAB 执行失败，stderr:\n%s", completed.stderr)
        raise RuntimeError("MATLAB 合并 .set 失败")
    else:
        logging.debug("MATLAB 输出：\n%s", completed.stdout)


def process_subject(subject: str) -> bool:
    """处理单个被试，返回是否成功。"""
    try:
        segs = collect_segments_for_subject(subject)
        if not segs:
            logging.warning("%s 无段文件，跳过", subject)
            return False
        pairs = get_vid_order_from_mat(subject)
        ordered_files, ordered_vids = build_ordered_file_list(segs, pairs)
        if not ordered_files:
            logging.warning("%s 无可拼接文件，跳过", subject)
            return False
        out_path = os.path.join(OUTPUT_DIR, f"{subject}_RELAX_concat.set")
        run_matlab_concat(ordered_files, out_path, ordered_vids)
        logging.info("%s 完成：%s", subject, out_path)
        return True
    except Exception as e:
        logging.exception("%s 处理失败：%s", subject, e)
        return False


def main():
    global EEGLAB_DIR
    parser = argparse.ArgumentParser(description="按视频播放顺序拼接 data-faced 的 .set 段文件")
    parser.add_argument("--subjects", nargs="*", help="指定要处理的被试 ID（如 sub002 sub010），默认处理全部可用被试")
    parser.add_argument("--eeglab", default=EEGLAB_DIR, help="EEGLAB 目录，默认读 EEGLAB_DIR 环境变量")
    parser.add_argument("--verbose", action="store_true", help="显示调试日志")
    args = parser.parse_args()

    EEGLAB_DIR = args.eeglab

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    if not os.path.isdir(CLEANED_DIR):
        logging.error("未找到 Cleaned_Data 目录：%s", CLEANED_DIR)
        return
    if not os.path.isdir(RAW_DATA_DIR):
        logging.error("未找到 Data 目录：%s", RAW_DATA_DIR)
        return

    subjects = args.subjects if args.subjects else find_subjects()
    if not subjects:
        logging.error("未发现可处理的被试目录")
        return

    logging.info("计划处理被试数：%d", len(subjects))
    ok = 0
    for sub in subjects:
        if process_subject(sub):
            ok += 1
    logging.info("处理完成：成功 %d / %d", ok, len(subjects))


if __name__ == "__main__":
    main()