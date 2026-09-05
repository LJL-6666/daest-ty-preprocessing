#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the complete TY movie 9-class input pkl from preprocessed 28-video files.

Input:
  output/movie/*.pkl, each subject as (28, 31, 7500)

Output:
  output/9_movie/data_9class_movie.pkl
  output/9_movie/README.md

This script does not touch output/6_movie or any existing modeling results.
"""

from __future__ import annotations

import os
import pickle as pkl
from pathlib import Path

import numpy as np

N_VIDEOS = 28
N_CH = 31
N_T = 7500
CONCAT_SHAPE = (N_CH + 1, N_VIDEOS * N_T)

VIDEO_IDS_9CLASS = list(range(1, 29))
CLASS_NAMES_9 = [
    "anger",
    "disgust",
    "fear",
    "sadness",
    "neutral",
    "amusement",
    "inspiration",
    "joy",
    "tenderness",
]
LABEL_9_BY_VIDEO = [
    0,
    0,
    0,
    1,
    1,
    1,
    2,
    2,
    2,
    3,
    3,
    3,
    4,
    4,
    4,
    4,
    5,
    5,
    5,
    6,
    6,
    6,
    7,
    7,
    7,
    8,
    8,
    8,
]


def subject_sort_key(path: Path) -> int:
    return int(path.stem) if path.stem.isdigit() else 999999


def to_videos_channels_time(data: np.ndarray) -> np.ndarray | None:
    """Normalize known saved formats to (28, 31, 7500)."""
    if not hasattr(data, "shape"):
        return None
    if data.shape == (N_VIDEOS, N_CH, N_T):
        return np.asarray(data)
    if data.shape == CONCAT_SHAPE:
        segments = []
        for i in range(N_VIDEOS):
            segments.append(data[:N_CH, i * N_T : (i + 1) * N_T])
        return np.stack(segments, axis=0)
    return None


def write_readme(out_dir: Path, out_file: Path, subject_ids: list[str], data_shape: tuple[int, ...]) -> None:
    lines = [
        "# TY 观影任务 9 类完整输入数据",
        "",
        "本目录由 `extract_9class_movie.py` 从 `output/movie/*.pkl` 汇总生成。",
        "",
        "## 文件",
        "",
        f"- `{out_file.name}`：`{{'data': ndarray, 'subject_ids': list, 'video_ids': list, 'label_9_by_video': list, 'class_names': list}}`",
        "",
        "## 数据口径",
        "",
        f"- 被试数：{len(subject_ids)}",
        f"- data.shape：{data_shape}",
        "- 视频数：28",
        "- 通道数：31",
        "- 每视频点数：7500，即 30 秒 × 250 Hz",
        "- 标签体系：素材标签 9 类",
        "",
        "## 9 类标签映射",
        "",
        "| videoIndex | label_id | label_name |",
        "|---:|---:|---|",
    ]
    for video_id, label_id in zip(VIDEO_IDS_9CLASS, LABEL_9_BY_VIDEO):
        lines.append(f"| {video_id} | {label_id} | {CLASS_NAMES_9[label_id]} |")
    lines.extend(
        [
            "",
            "## 注意",
            "",
            "- 该文件保留 28 个视频，不同于 `output/6_movie/data_6class_movie.pkl` 的 19 视频/6 类版本。",
            "- 生成过程不覆盖已有 6 类数据和任何建模结果。",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    here = Path(__file__).resolve().parent
    src_dir = here / "output" / "movie"
    out_dir = here / "output" / "9_movie"
    out_file = out_dir / "data_9class_movie.pkl"

    if not src_dir.is_dir():
        raise FileNotFoundError(f"missing source dir: {src_dir}")
    if out_file.exists():
        raise FileExistsError(f"refuse to overwrite existing file: {out_file}")

    files = sorted(src_dir.glob("*.pkl"), key=subject_sort_key)
    if not files:
        raise RuntimeError(f"no subject pkl files found in {src_dir}")

    subject_ids: list[str] = []
    data_blocks: list[np.ndarray] = []
    skipped: list[tuple[str, str]] = []
    for path in files:
        try:
            with path.open("rb") as fp:
                raw = pkl.load(fp)
            data = to_videos_channels_time(raw)
            if data is None:
                skipped.append((path.name, f"unsupported shape {getattr(raw, 'shape', None)}"))
                continue
            data_blocks.append(data.astype(np.float64, copy=False))
            subject_ids.append(path.stem.zfill(3))
        except Exception as exc:
            skipped.append((path.name, f"{type(exc).__name__}: {exc}"))

    if not data_blocks:
        raise RuntimeError("no valid movie pkl files could be loaded")

    data_all = np.stack(data_blocks, axis=0)
    out_dir.mkdir(parents=True, exist_ok=True)
    with out_file.open("wb") as fp:
        pkl.dump(
            {
                "data": data_all,
                "subject_ids": subject_ids,
                "video_ids": VIDEO_IDS_9CLASS,
                "label_9_by_video": LABEL_9_BY_VIDEO,
                "class_names": CLASS_NAMES_9,
            },
            fp,
            protocol=pkl.HIGHEST_PROTOCOL,
        )

    if skipped:
        skipped_path = out_dir / "skipped_files.tsv"
        skipped_path.write_text(
            "file\treason\n" + "\n".join(f"{name}\t{reason}" for name, reason in skipped),
            encoding="utf-8",
        )
    write_readme(out_dir, out_file, subject_ids, tuple(data_all.shape))

    print(f"saved: {out_file}")
    print(f"data.shape: {data_all.shape}")
    print(f"subjects: {len(subject_ids)}")
    print(f"skipped: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
