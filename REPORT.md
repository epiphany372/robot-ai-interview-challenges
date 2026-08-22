# 验证报告

## 应用测试

执行命令：

```powershell
pytest -q
```

测试覆盖：

- 首次进入会产生挥手和欢迎语两个效果。
- 同一人员在场期间重复进入，不会收到第二次欢迎。
- 对话进行中时，人员进入不会触发欢迎。
- 人员离开满10秒后才送客，并且同一次到访只送客一次。
- 人员在10秒内返回会取消待送客状态。
- 已送客的人员再次进入，会开始一次新的到访并再次欢迎。
- 会议进行中时，人员进入不会触发欢迎。
- 对话结束后，同一次到访的重复进入也不会补发欢迎。
- 调用方修改`snapshot()` 返回值，不会修改应用内部状态。
- 验证未知事件类型会明确报错，而不是被忽略。

测试结果：
> ..........
> 
> 10 passed in 0.03s

## 已完成事项

- 实现 `Event` 和 `Effect` 不可变数据模型。
- 实现 `RobotApplication` 事件处理和私有状态管理。
- 实现欢迎、重复进入去重、对话/会议抑制欢迎、延迟送客和再次进入规则。
- 编写pytest自动化测试。
- 编写架构说明，明确业务层与ROS 2/硬件层的边界。

## 未完成事项

- 未连接真实ROS 2环境。
- 未实现将 `Effect` 转换为ROS 2 Action、Service或Topic调用的Robot Bridge。
- 未验证真实机器人是否收到、执行并完成动作。
- 未实现VIP识别、RAG个性化文案和硬件故障恢复机制。

## ROS 2判断题

```text
app          effect_created type=ROBOT_ACTION value=wave_hand
robot_bridge request_submitted task_id=task-17 action=wave_hand
robot_bridge accepted_async task_id=task-17

$ ros2 action info /basic_action_play_v2
Action clients: 1
Action servers: 0

$ ros2 service call /get_robot_mode crb_ros_msg/srv/GetRobotMode "{}"
mode_name: STAND

$ systemctl is-active robot-action.service
inactive
```

### 1. 已经能证明什么

- 应用层成功创建了一个 `ROBOT_ACTION` 类型的 `wave_hand` 效果。
- Robot Bridge已提交动作请求，并记录了 `task_id=task-17`。
- Bridge已记录异步接受事件 `accepted_async`。
- ROS 2中存在一个 Action client。
- 机器人模式查询返回 `STAND`。
- `robot-action.service` 当前处于 `inactive` 状态。

### 2. `accepted_async` 是否代表机器人已经完成挥手

不是。

`accepted_async` 只能证明 Robot Bridge 已经异步接受或登记了该请求。它不代表：

- ROS 2 Action server 已经收到请求；
- 机器人已经开始执行；
- 机器人已经完成动作；
- 动作执行成功。

要证明动作完成，需要看到可用的Action server、执行反馈，以及最终成功结果。

### 3. 问题最可能在哪一层

最可能是机器人动作执行服务未运行或未提供Action server。

证据是：

- `ros2 action info /basic_action_play_v2` 显示 `Action servers: 0`；
- `systemctl is-active robot-action.service` 返回 `inactive`。

因此Action client即使存在，也没有可执行请求的服务端。

### 4. 下一步按什么顺序检查

1. 检查服务状态和失败原因
2. 修复配置、依赖或启动失败原因后，启动服务
3. 再次检查服务状态
4. 再次确认 Action server 已出现： 预期 `Action servers` 不再是 `0`。
5. 再次确认机器人模式安全
6. 在安全环境中发送低风险动作，观察action feedback和最终result。

### 5. 当前能否直接执行真实动作，为什么

不能。

虽然应用层已生成 `wave_hand` 效果，Robot Bridge也记录了请求提交，但当前没有可用的ROS 2 Action server，并且 `robot-action.service` 未运行。因此真实机器人动作执行链路尚未建立，直接执行存在失败或不可预测行为的风险。

应先恢复并验证Action server、确认机器人状态安全，再执行真实动作。