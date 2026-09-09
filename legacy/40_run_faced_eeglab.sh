#!/bin/bash
# FACED 预处理：EEGLAB .set → 拼接 → .mat
# 需先设置 DAEST_DATA_ROOT 和 EEGLAB_DIR
set -uo pipefail

echo "=== FACED 预处理 ==="

# 检查环境变量
if [ -z "${DAEST_DATA_ROOT:-}" ]; then
  echo "❌ DAEST_DATA_ROOT 未设置"
  exit 1
fi
if [ -z "${EEGLAB_DIR:-}" ]; then
  echo "❌ EEGLAB_DIR 未设置"
  exit 1
fi

FACED_DIR="${DAEST_DATA_ROOT}/data-faced"
CLEANED_DIR="${FACED_DIR}/Cleaned_Data"
OUTPUT_DIR="${FACED_DIR}/Cleaned_Data-2"

echo "输入目录: $CLEANED_DIR"
echo "输出目录: $OUTPUT_DIR"
echo "EEGLAB:   $EEGLAB_DIR"

# 步骤 1: 按播放顺序拼接 .set
echo ""
echo "=== 步骤 1: 拼接 .set ==="
python legacy/faced_concat_by_vid.py \
  --eeglab "$EEGLAB_DIR" \
  || { echo "❌ 拼接失败"; exit 1; }

# 步骤 2: pkl → .mat
echo ""
echo "=== 步骤 2: pkl → .mat ==="
python src/convert_pkl_to_mat.py \
  || { echo "❌ 转换失败"; exit 1; }

echo ""
echo "✅ FACED 预处理完成"
echo "输出: ${FACED_DIR}/0.05–47 Hz_mat/processed_data/*.mat"
