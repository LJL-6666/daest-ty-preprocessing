#!/bin/bash
# FACED 预处理（Python/MNE 链路 —— DAEST 主线正确版）
#
#   Data/subXXX/{data.bdf, evt.bdf, After_remarks.mat}
#     -> src/main_faced.py + src/Preprocessing.py   （MNE，无需 MATLAB/EEGLAB）
#     -> 0.05–47 Hz/Processed_data/subXXX.pkl
#     -> src/convert_pkl_to_mat.py
#     -> 0.05–47 Hz_mat/processed_data/subXXX.mat  （DAEST train_ext 的输入）
#
# 注：仓库 legacy/ 下的 faced_concat_by_vid.py 是基于 EEGLAB .set 的旁支探索，
#     产出时间晚于本链路的 pkl 两个月，未用于任何已发表结果。见 docs/04_版本溯源.md
set -uo pipefail

echo "=== FACED 预处理（Python/MNE） ==="

if [ -z "${DAEST_DATA_ROOT:-}" ]; then
  echo "❌ DAEST_DATA_ROOT 未设置（应指向包含 data-faced/ 的目录）"
  exit 1
fi

FACED_DIR="${DAEST_DATA_ROOT}/data-faced"
PREP_ROOT="${DAEST_PREP_ROOT:-$FACED_DIR}"
CLISA_OR_NOT="${1:-no}"

echo "原始 .bdf : ${FACED_DIR}/Data/subXXX/{data.bdf,evt.bdf}"
echo "播放顺序  : ${FACED_DIR}/Data/subXXX/After_remarks.mat"
echo "被试清单  : ${FACED_DIR}/一些背景/Recording_info.csv"
echo "pkl 输出  : ${PREP_ROOT}/0.05–47 Hz/Processed_data"
echo "clisa 分支: ${CLISA_OR_NOT}"

for f in "${FACED_DIR}/一些背景/Recording_info.csv" "${FACED_DIR}/Data"; do
  [ -e "$f" ] || { echo "❌ 缺少: $f"; exit 1; }
done

echo ""
echo "=== 步骤 1: .bdf → pkl（重采样 250 Hz / 0.05–47 Hz / 坏道插值 / ICA / 平均参考 / 按播放顺序拼接） ==="
( cd src && python main_faced.py --clisa-or-not "${CLISA_OR_NOT}" ) \
  || { echo "❌ 预处理失败"; exit 1; }

echo ""
echo "=== 步骤 2: pkl → .mat ==="
python src/convert_pkl_to_mat.py \
  --pkl-dir "${PREP_ROOT}/0.05–47 Hz/Processed_data" \
  --out-dir "${FACED_DIR}/0.05–47 Hz_mat" \
  || { echo "❌ 转换失败"; exit 1; }

echo ""
echo "✅ FACED 预处理完成"
echo "输出: ${FACED_DIR}/0.05–47 Hz_mat/processed_data/*.mat  （共应为 123 个被试）"
