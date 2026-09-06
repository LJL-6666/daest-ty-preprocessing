# 行为与问卷数据说明

## 本目录里有什么

`example_questionnaire/` —— **3 名被试的样例记录**，用于说明文件格式与
`src/main_tongyong.py: read_video_order_from_csv()` 的对齐逻辑。

完整数据集（129 名被试）**不随仓库分发**，见下方「获取完整数据」。

样例已做以下处理：被试编号重编为 `ex01`–`ex03`（与真实编号无对应关系）；
文件名中的采集时间戳由 `YYYYMMDDhhmmss` 截断为 `YYYYMMDD`；不含 `subject_info.txt`。

## 目录与命名

```
example_questionnaire/<被试>/
    exp0_<日期>_rating.csv          任务 0 的逐视频情绪评分
    exp0_<日期>_math.csv            任务 0 的数学干扰任务
    exp1_<日期>_rating.csv          任务 1 的逐视频情绪评分
    exp1_<日期>_math.csv            任务 1 的数学干扰任务
    exp2_concept_similarity.csv     情绪概念两两相似度评定
```

`exp0` / `exp1` 对应两个不同的实验任务（观影 / 讲述）。
**流水线只使用 `*_rating.csv` 的 `videoIndex` 列**，用于把 EEG 试次重排到实际播放顺序；
其余文件为行为学记录，预处理流程不读取。

## 列定义

### `*_rating.csv` —— 每行一个视频，本样例每人 28 行

| 列 | 类型 | 含义 | 取值 |
|---|---|---|---|
| `videoIndex` | float | 视频编号；**行的顺序即实际播放顺序** | 1–28 |
| `videoEmotion` | str | 该视频的素材情绪标签 | `anger` `disgust` `fear` `sadness` `amusement` `inspiration` `joy` `tenderness` `neutral` |
| `percCompleted` | float | 该视频的播放完成度百分比 | 0–100 |
| `anger` `disgust` `fear` `sadness` `amusement` `inspiration` `joy` `tenderness` | float | 八类离散情绪的自评强度 | 0–100 |
| `valence` | float | 效价自评 | 0–100 |
| `arousal` | float | 唤醒度自评 | 0–100 |
| `liking` | float | 喜好度自评 | 0–100 |
| `familiarity` | float | 熟悉度自评 | 0–100 |

> `videoEmotion` 是**素材标签**（9 类），八列离散情绪自评是**被试自评**（8 类，无 neutral）。
> 建模仓库 `daest-ty-mainline` 中「素材 9 类」与「自评 8 类」两套实验即由此区分。

### `*_math.csv` —— 数学干扰任务，每行一个试次

| 列 | 类型 | 含义 |
|---|---|---|
| `blockIndex` | float | 组块编号（本样例 1–6） |
| `responseTime` | float | 反应时，单位秒 |
| `ifCorrect` | float | 是否正确，`1.0` / `0.0` |

**已知缺失**：部分被试的 `responseTime` / `ifCorrect` 为空（超时未作答，或该被试整列未记录）。
样例中 `ex01` 的 `exp1` math 文件即为整列 `ifCorrect` 缺失的情况，保留原样以便看到真实数据形态。

### `exp2_concept_similarity.csv` —— 情绪概念相似度，每行一个情绪词对

| 列 | 类型 | 含义 |
|---|---|---|
| `emotion1` `emotion2` | str | 情绪词对（取值同 `videoEmotion`） |
| `similarity` | float | 主观相似度评分 |

## 获取完整数据

完整的 129 名被试行为与问卷数据依申请获取，请联系仓库作者。

<!-- TODO(作者)：补充申请方式（邮箱或课题组页面），以及是否需要签署数据使用协议。 -->

## 伦理与许可

<!-- TODO(作者)：补充伦理审批单位与批件号，并确认知情同意书是否覆盖「数据公开共享」。
     确认前请勿把完整数据集放回公开仓库。 -->

- 数据已去标识：不含姓名、联系方式或其他直接标识符，被试仅以编号区分。
- 本目录下的**数据**适用 [CC BY 4.0](LICENSE)，与仓库代码的 MIT 许可不同。
  软件许可（MIT）不适用于数据集，故单列。
