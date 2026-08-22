# 架构说明

## 模块图与依赖方向

```mermaid
flowchart LR
    Source[事件来源<br/>传感器 / 模拟器 / ROS 2]
    App[RobotApplication<br/>业务层]
    State[私有业务状态]
    Effects[Effect 列表]
    Adapter[适配层<br/>ROS 2 / 机器人硬件]

    Source -->|Event| App
    App --> State
    App -->|list[Effect]| Effects
    Effects --> Adapter
```

依赖方向是：事件来源 → 业务层 → 效果 → 适配层。  
业务层不依赖 ROS 2、硬件 SDK、数据库或 AI 服务。

## 模块职责与边界

### `robot_application.models`

负责定义 `Event` 和 `Effect` 数据模型。

不负责保存状态、处理业务规则、调用 ROS 2 或控制机器人。

### `robot_application.application.RobotApplication`

负责处理事件、维护业务状态、判断欢迎或送客，并返回 `Effect` 列表。

不负责执行真实机器人动作、发布 ROS 2 消息或访问外部服务。

### 未来的 ROS 2 / 硬件适配层

负责把 `Effect` 转换为 ROS 2 Action、Service、Topic 或机器人 SDK 调用，并处理异步执行结果。

不负责决定是否欢迎、是否送客或维护业务状态。

## 状态所有权

所有业务状态由 `RobotApplication` 的私有成员拥有：

| 状态 | 所有者 | 作用 |
|---|---|---|
| 人员到访状态 | `_visits` | 记录人员是否在场、离开时间、是否已送客 |
| 对话状态 | `_conversation_active` | 对话期间禁止欢迎 |
| 会议状态 | `_meeting_active` | 会议期间禁止欢迎 |
| 计时配置 | `_absence_timeout_s` | 定义离开多久后送客 |
| 去重状态 | 每个 `VisitState` | 防止重复欢迎和重复送客 |

状态不使用全局可变变量。`snapshot()` 返回状态副本，外部修改不会影响内部状态。

## 未来扩展

### VIP

新增独立的 `VipRecognitionAdapter`，把识别结果转换为人员属性或事件。欢迎策略可根据 VIP 信息生成不同效果，而不修改 ROS 2 适配层。

### RAG

新增 `GreetingContentProvider` 接口，由 RAG 实现提供个性化欢迎文案。业务层只获取文案结果，不直接访问模型 API 或向量数据库。

### ROS 2 导航

新增 `RosNavigationAdapter`，消费例如 `Effect("NAVIGATION", "go_to_lobby", ...)` 的效果，并负责调用 ROS 2 导航 Action。导航执行、反馈、重试和失败处理都位于适配层。

## 避免形成“大类”

`RobotApplication` 只负责迎宾规则和业务状态。VIP 识别、RAG 文案、ROS 2 通信、导航和硬件控制分别通过独立模块或适配器扩展，而不是继续向 `RobotApplication` 添加职责。