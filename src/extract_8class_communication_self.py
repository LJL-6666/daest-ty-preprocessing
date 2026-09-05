#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build TY communication self-argmax 8-class input pkl for DAEST cross-subject.

Reuses EEG from output/9_communication/data_9class_communication.pkl; replaces
stimulus labels with per-subject per-video self-rating argmax (exp1, 8 emotions).

Does not overwrite 9_communication / 8_movie_self / any modeling results.
"""

from __future__ import annotations

import json
import os
import pickle as pkl
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

DAEST_DATA_ROOT = os.environ.get("DAEST_DATA_ROOT", "")
QUESTIONNAIRE_DIR = Path(os.path.join(DAEST_DATA_ROOT, "data-tongyong/原始数据/问卷"))
EXP_PREFIX = "exp1"
N_VIDS = 28
VIDEO_IDS = list(range(1, N_VIDS + 1))

EMOTION_COLS = [
    "anger",
    "disgust",
    "fear",
    "sadness",
    "amusement",
    "inspiration",
    "joy",
    "tenderness",
]


def latest_rating_file(subject_id: str) -> Path | None:
    subject_dir = QUESTIONNAIRE_DIR / str(int(subject_id))
    if not subject_dir.is_dir():
        return None
    files = sorted(subject_dir.glob(f"{EXP_PREFIX}*_rating.csv"))
    return files[-1] if files else None


def self_argmax_row(scores: np.ndarray) -> tuple[int, str, float, bool]:
    """all8_zero / all-NaN → label_id=-1（按视频剔除，不映射 anger）。"""
    all_zero = bool(np.nansum(scores) == 0)
    if np.all(np.isnan(scores)) or all_zero:
        return -1, "", float("nan"), True
    scores_for_argmax = np.nan_to_num(scores, nan=-np.inf)
    argmax_id = int(np.argmax(scores_for_argmax))
    return argmax_id, EMOTION_COLS[argmax_id], float(scores[argmax_id]), False


def _invalid_rows(subject_id: str, reason: str, source_file: str = "") -> tuple[np.ndarray, list[dict]]:
    labels = np.full(N_VIDS, -1, dtype=np.int64)
    rows = []
    for vid in VIDEO_IDS:
        rows.append(
            {
                "subject": str(subject_id).zfill(3),
                "videoIndex": vid,
                "self_argmax_id": -1,
                "self_argmax_label8": "INVALID",
                "self_argmax_score": float("nan"),
                "all8_zero": False,
                "valid_label": False,
                "invalid_reason": reason,
                "source_file": source_file,
            }
        )
    return labels, rows


def labels_for_subject(subject_id: str) -> tuple[np.ndarray, list[dict]]:
    """缺文件/缺列/缺视频 → 对应位置 -1，不抛错（保持与 EEG 118 人对齐）。"""
    path = latest_rating_file(subject_id)
    if path is None:
        return _invalid_rows(subject_id, "missing_exp1_rating_csv")

    df = pd.read_csv(path)
    required = {"videoIndex", *EMOTION_COLS}
    missing = required.difference(df.columns)
    if missing:
        return _invalid_rows(subject_id, f"missing_columns:{sorted(missing)}", str(path))

    by_vid: dict[int, dict] = {}
    for row in df.itertuples(index=False):
        vid = int(getattr(row, "videoIndex"))
        scores = np.array([float(getattr(row, c)) for c in EMOTION_COLS], dtype=float)
        argmax_id, argmax_label, max_score, all_zero = self_argmax_row(scores)
        by_vid[vid] = {
            "subject": str(subject_id).zfill(3),
            "videoIndex": vid,
            "self_argmax_id": argmax_id,
            "self_argmax_label8": argmax_label if argmax_id >= 0 else "INVALID_ALL8_ZERO",
            "self_argmax_score": max_score,
            "all8_zero": all_zero,
            "valid_label": argmax_id >= 0,
            "invalid_reason": "all8_zero" if all_zero else "",
            "source_file": str(path),
        }

    labels = np.full(N_VIDS, -1, dtype=np.int64)
    rows: list[dict] = []
    for vid in VIDEO_IDS:
        if vid not in by_vid:
            rows.append(
                {
                    "subject": str(subject_id).zfill(3),
                    "videoIndex": vid,
                    "self_argmax_id": -1,
                    "self_argmax_label8": "INVALID",
                    "self_argmax_score": float("nan"),
                    "all8_zero": False,
                    "valid_label": False,
                    "invalid_reason": "missing_videoIndex",
                    "source_file": str(path),
                }
            )
            continue
        info = by_vid[vid]
        labels[VIDEO_IDS.index(vid)] = int(info["self_argmax_id"])
        rows.append(info)
    return labels, rows


def majority_by_video(label_mat: np.ndarray) -> list[int]:
    """多数票仅统计有效标签（>=0）；全员无效则回退 0（仅供 ME metadata）。"""
    out = []
    for j in range(label_mat.shape[1]):
        vals = [int(x) for x in label_mat[:, j].tolist() if int(x) >= 0]
        if not vals:
            out.append(0)
        else:
            out.append(Counter(vals).most_common(1)[0][0])
    return out


def write_readme(out_dir: Path, out_file: Path, subject_ids: list[str], data_shape: tuple, qc: dict) -> None:
    lines = [
        "# TY 交流任务 自评 argmax 8 类输入数据（DAEST 跨被试）",
        "",
        "本目录由 `extract_8class_communication_self.py` 从 `output/9_communication/data_9class_communication.pkl` + 问卷 `exp1` 生成。",
        "",
        "## 文件",
        "",
        f"- `{out_file.name}`：含 `data`、`subject_ids`、`label_by_subject_video`、`label_by_video`(多数票兜底)、`class_names`",
        "- `self_argmax_by_video.csv`：逐被试×视频自评标签与无效标记",
        "- `qc_summary.json`：标签质控摘要",
        "",
        "## 数据口径",
        "",
        f"- 被试数：{len(subject_ids)}",
        f"- data.shape：{data_shape}",
        "- 视频数：28（与素材 9 类同源 EEG）",
        "- 标签：自评 8 维情绪 argmax（问卷 exp1；无中性列）",
        "- **全 0 / 全 NaN / 缺评：标签=-1（无效），按视频剔除，不映射为 anger**",
        "",
        "## 8 类",
        "",
        "| id | name |",
        "|---:|---|",
    ]
    for i, name in enumerate(EMOTION_COLS):
        lines.append(f"| {i} | {name} |")
    lines.append("| -1 | INVALID（全 0/缺评，训练忽略） |")
    lines.extend(
        [
            "",
            "## 质控摘要",
            "",
            f"- 全 0 评分视频数：{qc['n_all8_zero_videos']}",
            f"- 含全 0 视频的被试数：{qc['n_subjects_with_all8_zero']}",
            f"- 缺评/坏问卷被试数：{qc.get('n_subjects_missing_or_bad_rating', 'n/a')}",
            f"- 有效标签数：{qc.get('n_valid_labels', 'n/a')} / {qc['n_subjects'] * qc['n_videos']}",
            f"- 有效标签分布：{qc['label_counts']}",
            "",
            "## 注意",
            "",
            "- 不覆盖 `9_communication` / `8_movie_self` 与任何已有建模结果。",
            "- DAEST 跨被试 MLP 必须使用 `label_by_subject_video`；`ignore_index=-1`。",
            "- 118 人 extract_fea 的 LDS 占内存大，跑批须串行提特征。",
        ]
    )
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="overwrite existing pkl")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    src_pkl = here / "output" / "9_communication" / "data_9class_communication.pkl"
    out_dir = here / "output" / "8_communication_self"
    out_file = out_dir / "data_8class_communication_self.pkl"

    if not src_pkl.is_file():
        raise FileNotFoundError(f"missing source pkl: {src_pkl}")
    if out_file.exists() and not args.force:
        raise FileExistsError(f"refuse to overwrite existing file: {out_file} (pass --force)")

    with src_pkl.open("rb") as fp:
        src = pkl.load(fp)
    data = np.asarray(src["data"])
    subject_ids = [str(s).zfill(3) for s in src["subject_ids"]]
    if data.shape[0] != len(subject_ids):
        raise ValueError("data / subject_ids length mismatch")
    if data.shape[1] != N_VIDS:
        raise ValueError(f"expected {N_VIDS} videos, got {data.shape[1]}")

    label_mat = np.zeros((len(subject_ids), N_VIDS), dtype=np.int64)
    detail_rows: list[dict] = []
    bad_subjects: list[str] = []
    for i, sid in enumerate(subject_ids):
        labels, rows = labels_for_subject(sid)
        label_mat[i] = labels
        detail_rows.extend(rows)
        reasons = {str(r.get("invalid_reason", "")) for r in rows}
        if any(x.startswith("missing_") for x in reasons):
            bad_subjects.append(sid)

    label_by_video = majority_by_video(label_mat)
    detail_df = pd.DataFrame(detail_rows)
    n_all_zero = int(detail_df["all8_zero"].fillna(False).astype(bool).sum())
    n_sub_zero = int(detail_df.loc[detail_df["all8_zero"] == True, "subject"].nunique())  # noqa: E712
    valid = label_mat[label_mat >= 0]
    counts = {EMOTION_COLS[k]: int(v) for k, v in sorted(Counter(valid.tolist()).items())}
    qc = {
        "n_subjects": len(subject_ids),
        "n_videos": N_VIDS,
        "n_all8_zero_videos": n_all_zero,
        "n_subjects_with_all8_zero": n_sub_zero,
        "n_subjects_missing_or_bad_rating": len(set(bad_subjects)),
        "subjects_missing_or_bad_rating": sorted(set(bad_subjects)),
        "n_valid_labels": int(valid.size),
        "n_invalid_labels": int((label_mat < 0).sum()),
        "invalid_policy": "drop_video_label_minus1_ignore_in_mlp",
        "label_counts": counts,
        "majority_label_by_video": label_by_video,
        "exp_prefix": EXP_PREFIX,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    with out_file.open("wb") as fp:
        pkl.dump(
            {
                "data": data,
                "subject_ids": subject_ids,
                "video_ids": VIDEO_IDS,
                "label_by_subject_video": label_mat,
                "label_by_video": label_by_video,
                "valid_mask": label_mat >= 0,
                "class_names": EMOTION_COLS,
                "label_source": "self_argmax_exp1",
                "n_class": 8,
                "invalid_label_id": -1,
                "invalid_policy": "drop_all8_zero_or_missing_videos",
            },
            fp,
            protocol=pkl.HIGHEST_PROTOCOL,
        )
    detail_df.to_csv(out_dir / "self_argmax_by_video.csv", index=False, encoding="utf-8-sig")
    (out_dir / "qc_summary.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    write_readme(out_dir, out_file, subject_ids, tuple(data.shape), qc)

    print(f"saved: {out_file}")
    print(f"data.shape: {data.shape}")
    print(f"label_by_subject_video: {label_mat.shape}")
    print(f"invalid(-1): {int((label_mat < 0).sum())}; all8_zero videos: {n_all_zero}; bad_rating_subs: {sorted(set(bad_subjects))}")
    print(f"valid label_counts: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
