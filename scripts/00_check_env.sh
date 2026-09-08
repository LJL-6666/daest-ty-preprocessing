#!/bin/bash
# 环境检查：Python 包、内存、数据路径
set -uo pipefail

echo "=== 环境 ==="
python -c "import mne, numpy, pandas, scipy, matplotlib, hdf5storage; print(f'  mne {mne.__version__} / numpy {numpy.__version__} / pandas {pandas.__version__}')" || exit 1

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

echo "=== FACED 原始数据（.bdf 链路，不需要 EEGLAB） ==="
if [ -n "${DAEST_DATA_ROOT:-}" ]; then
  FACED_DATA="${DAEST_DATA_ROOT}/data-faced/Data"
  if [ -d "$FACED_DATA" ]; then
    N=$(find "$FACED_DATA" -maxdepth 1 -type d -name 'sub*' | wc -l)
    NR=$(find "$FACED_DATA" -maxdepth 2 -name 'After_remarks.mat' | wc -l)
    echo "  ✅ $FACED_DATA ($N 个被试目录, $NR 份 After_remarks.mat)"
  else
    echo "  ❌ $FACED_DATA 不存在"
  fi
  REC="${DAEST_DATA_ROOT}/data-faced/一些背景/Recording_info.csv"
  [ -f "$REC" ] && echo "  ✅ $REC" || echo "  ❌ $REC 不存在"
fi
