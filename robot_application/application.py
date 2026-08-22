from copy import deepcopy
from dataclasses import dataclass
from typing import Optional

from robot_application.models import Effect, Event


@dataclass
class VisitState:
    """一个人员当前这次到访的内部状态"""

    is_inside: bool = False
    entry_processed: bool = False
    left_at: Optional[float] = None
    farewelled: bool = False


class RobotApplication:
    def __init__(self, absence_timeout_s: float = 10.0):
        self._absence_timeout_s = absence_timeout_s

        # 应用级状态：不属于某一个人
        self._conversation_active = False
        self._meeting_active = False

        # 人员级状态：key是person_id
        self._visits: dict[str, VisitState] = {}

    def handle_event(self, event: Event) -> list[Effect]:
        """只返回本次事件新产生的效果"""

        # 人员相关事件：处理人员到访状态
        if event.event_type == "PERSON_ENTERED":
            return self._handle_person_entered(event)

        if event.event_type == "PERSON_LEFT":
            return self._handle_person_left(event)

        # 对话开始后，后续人员进入不能触发欢迎
        if event.event_type == "CONVERSATION_STARTED":
            self._conversation_active = True
            return []

        # 对话结束后，恢复正常的欢迎判断
        if event.event_type == "CONVERSATION_ENDED":
            self._conversation_active = False
            return []

        # 会议开始后，后续人员进入不能触发欢迎
        if event.event_type == "MEETING_STARTED":
            self._meeting_active = True
            return []

        # 会议结束后，恢复正常的欢迎判断
        if event.event_type == "MEETING_ENDED":
            self._meeting_active = False
            return []

        # TICK用于检查是否有人员离开超过设定时间
        if event.event_type == "TICK":
            return self._handle_tick(event)

        raise ValueError(f"Unsupported event type: {event.event_type}")

    def snapshot(self):
        """返回值不能被外部修改后影响内部状态"""

        return deepcopy(
            {
                "conversation_active": self._conversation_active,
                "meeting_active": self._meeting_active,
                "visits": self._visits,
            }
        )

    def _interaction_active(self) -> bool:
        """对话或会议进行中时，不欢迎新进入的人员"""

        return self._conversation_active or self._meeting_active

    def _handle_person_entered(self, event: Event) -> list[Effect]:
        if event.person_id is None:
            raise ValueError("PERSON_ENTERED requires person_id")

        visit = self._visits.get(event.person_id)

        # 已送客后再次进入：开启一轮新的到访
        if visit is None or visit.farewelled:
            visit = VisitState(is_inside=True, entry_processed=True)
            self._visits[event.person_id] = visit

            # 对话或会议期间进入：记录到访，但不欢迎
            if self._interaction_active():
                return []

            return [
                Effect(
                    effect_type="ROBOT_ACTION",
                    value="wave_hand",
                    reason="first_entry",
                ),
                Effect(
                    effect_type="SPEECH",
                    value="欢迎光临",
                    reason="first_entry",
                ),
            ]

        # 离开后10秒内返回：取消待送客，但不再次欢迎
        if not visit.is_inside:
            visit.is_inside = True
            visit.left_at = None
            return []

        # 已经在场：重复进入事件，不产生任何效果
        return []

    def _handle_person_left(self, event: Event) -> list[Effect]:
        if event.person_id is None:
            raise ValueError("PERSON_LEFT requires person_id")

        visit = self._visits.get(event.person_id)

        # 未登记的人员，或已经离开：忽略重复/无效事件
        if visit is None or not visit.is_inside:
            return []

        visit.is_inside = False
        visit.left_at = event.timestamp

        # 离开时不立即送客，等待后续TICK
        return []

    def _handle_tick(self, event: Event) -> list[Effect]:
        """检查所有已离开的人员，必要时送客"""

        effects: list[Effect] = []

        # 遍历每一位已被应用记录的人员到访状态
        for person_id, visit in self._visits.items():
            should_farewell = (
                    # 人员当前不在场
                    not visit.is_inside
                    # 本次到访尚未送客，避免重复送客
                    and not visit.farewelled
                    # 必须有有效的离开时间
                    and visit.left_at is not None
                    # 当前TICK时间距离离开时间已达到超时阈值
                    and event.timestamp - visit.left_at >= self._absence_timeout_s
            )

            if should_farewell:
                # 先更新状态，确保后续TICK不会重复产生送客效果
                visit.farewelled = True
                effects.append(
                    Effect(
                        effect_type="SPEECH",
                        value="感谢光临，再见",
                        reason=f"absent_for_{self._absence_timeout_s}_seconds",
                    )
                )

        return effects