# DAEST · TY 情绪解码 · 预处理

TY 与 FACED 数据集 EEG 预处理流水线：原始脑电 → 建模可用 pkl / mat。

与建模仓库 [`daest-ty-mainline`](https://github.com/LJL-6666/daest-ty-mainline) 联动。

## 产出

### TY 数据集

| pkl | 被试数 | 标签 | 大小 |
|---|---|---|---|
| `data_9class_movie.pkl` | 52 | 素材 9 类 | 2.6 GB |
| `data_9class_communication.pkl` | 118 | 素材 9 类 | 5.8 GB |
| `data_8class_movie_self.pkl` | 52 | 自评 8 类 | 2.6 GB |
| `data_8class_communication_self.pkl` | 118 | 自评 8 类 | 5.8 GB |

口径：250 Hz · 31 通道 · 28 视频 × 30 秒 · 0.05–47 Hz 滤波。

### FACED 数据集

| 输出 | 说明 |
|---|---|
| `0.05–47 Hz/Processed_data/*.pkl` | 每被试一个 pkl（123 人），按播放顺序拼接 |
| `0.05–47 Hz_mat/processed_data/*.mat` | 每被试一个 .mat，供建模仓库 `FACED_05_47` 配置使用 |
| `4–47 Hz/Clisa_data/*.pkl` | CLISA 分支（`--clisa-or-not yes`），在 0.05–47 基础上再 4–47 Hz 带通 |

口径：250 Hz · 32 通道 · 28 视频 × 30 秒 · 0.05–47 Hz 滤波。

**链路为纯 Python/MNE，不需要 MATLAB 或 EEGLAB。** 基于 EEGLAB `.set` 的旁支已移入
`legacy/`，未用于任何已发表结果 —— 判据见 [`docs/04_版本溯源.md`](docs/04_版本溯源.md)。

## 目录

```
src/        11 个核心脚本
            ├─ FACED : main_faced.py, Preprocessing.py, convert_pkl_to_mat.py
            ├─ TY    : main_tongyong.py, Preprocessing_tongyong.py
            └─ 汇总  : extract_{9class,8class,6class}_*.py
scripts/    5 个入口：00 验环境 → 10 TY 预处理 → 20 TY 9类 → 30 TY 8类自评 → 40 FACED
legacy/     不在主线上的旁支（FACED 的 EEGLAB 拼接版），仅历史留存
data/       问卷 CSV（624 个文件，3.7 MB）
results/    QC 摘要、跳过记录
docs/       数据口径、与建模仓库衔接、预处理限制、版本溯源
MANIFEST/   大文件清单、原始数据来源
```

## 复现

```bash
# 1. 设置环境变量
export DAEST_DATA_ROOT=/path/to/TY/data
export DAEST_PREP_ROOT=/path/to/daest-ty-preprocessing

# 2. 验环境
bash scripts/00_check_env.sh

# 3. TY 预处理（原始脑电 → 逐被试 pkl）
bash scripts/10_run_preprocessing.sh

# 4. TY 汇总 9 类
bash scripts/20_extract_9class.sh

# 5. TY 汇总 8 类自评（需问卷）
bash scripts/30_extract_8class.sh

# 6. FACED 预处理（.bdf → MNE → pkl → .mat；加 yes 同时产出 CLISA 分支）
bash scripts/40_run_faced.sh          # 或: bash scripts/40_run_faced.sh yes
```

## 与建模仓库的衔接

建模仓库的 `src/cfgs/data/*.yaml` 通过 `${oc.env:DAEST_PREP_ROOT}` 引用本仓库产出的 pkl / mat。
详见 [`docs/02_与建模仓库的衔接.md`](docs/02_与建模仓库的衔接.md)。

## 限制

见 [`docs/03_预处理限制.md`](docs/03_预处理限制.md)。

## 版本溯源

历史上同一批脚本存在多个副本与分支。哪一份代码产出了哪一份数据、各分支为何不在
主线上，见 [`docs/04_版本溯源.md`](docs/04_版本溯源.md)（以 md5、mtime 与数据产出
时间三重证据固定）。
