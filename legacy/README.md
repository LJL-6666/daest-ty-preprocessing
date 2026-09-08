# legacy/ —— 不在主线上的旁支

本目录的脚本**未用于任何已发表结果**，仅作历史留存。

## FACED 的 EEGLAB 旁支

- `faced_concat_by_vid.py`：`Cleaned_Data/subXXX-YY_RELAX.set` → `Cleaned_Data-2/`
- `40_run_faced_eeglab.sh`：调用它的驱动脚本

**为什么不是主线**：DAEST 实际输入 `.mat` 由 `0.05–47 Hz/Processed_data/*.pkl`
转出，那批 pkl 的产出时间是 **2025-09-15**；而 EEGLAB 链路的输入 `.set`
（`Cleaned_Data/`）产出于 **2025-11-13**，晚两个月，时间上不可能产出主线数据。

主线是纯 Python/MNE 链路：`src/main_faced.py` + `src/Preprocessing.py`
（需 MATLAB/EEGLAB 的只有本目录这条旁支）。详见 `docs/04_版本溯源.md`。
