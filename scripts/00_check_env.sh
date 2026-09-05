#!/bin/bash
# 环境检查：Python 包、内存、数据路径
set -uo pipefail

echo "=== 环境 ==="
python -c "import mne, numpy, pandas, scipy, matplotlib; print(f'  mne {mne.__version__} / numpy {numpy.__version__} / pandas {pandas.__version__}')" || exit 1

echo "=== 数据路径 ==="
for v in DAEST_DATA_ROOT DAEST_PREP_ROOT; do
  printf "  %-18s %s\n" "$v" "${!v:-❌ 未设置}"
done

echo "=== 内存 ==="
free -h | head -2

echo "=== 原始脑电目录 ==="
if [ -n "${DAEST_DATA_ROOT:-}" ]; then
  EEG_DIR="${DAEST_DATA_ROOT}/data-tongyong/原始数据/脑电近红外/标准脑电"
  if [ -d "$EEG_DIR" ]; then
    N=$(find "$EEG_DIR" -maxdepth 1 -type d | wc -l)
    echo "  ✅ $EEG_DIR ($((N-1)) 个被试目录)"
  else
    echo "  ❌ $EEG_DIR 不存在"
  fi
fi

echo "=== 问卷目录 ==="
if [ -n "${DAEST_DATA_ROOT:-}" ]; then
  Q_DIR="${DAEST_DATA_ROOT}/data-tongyong/原始数据/问卷"
  if [ -d "$Q_DIR" ]; then
    N=$(find "$Q_DIR" -maxdepth 1 -type d | wc -l)
    echo "  ✅ $Q_DIR ($((N-1)) 个被试目录)"
  else
    echo "  ❌ $Q_DIR 不存在"
  fi
fi
