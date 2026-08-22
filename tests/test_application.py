import pytest
from robot_application.application import RobotApplication
from robot_application.models import Event


# 验证首次进入会产生挥手和欢迎语两个效果
def test_first_entry_waves_and_greets():
    app = RobotApplication()

    effects = app.handle_event(
        Event(
            event_type="PERSON_ENTERED",
            timestamp=0,
            person_id="person-1",
        )
    )

    assert [effect.value for effect in effects] == [
        "wave_hand",
        "欢迎光临",
    ]


# 验证同一人员在场期间重复进入，不会收到第二次欢迎
def test_duplicate_entry_does_not_greet_again():
    app = RobotApplication()

    app.handle_event(Event("PERSON_ENTERED", 0, "person-1"))
    effects = app.handle_event(Event("PERSON_ENTERED", 1, "person-1"))

    assert effects == []


# 验证对话进行中时，人员进入不会触发欢迎
def test_entry_during_conversation_does_not_greet():
    app = RobotApplication()

    app.handle_event(Event("CONVERSATION_STARTED", 0))
    effects = app.handle_event(Event("PERSON_ENTERED", 1, "person-1"))

    assert effects == []


# 验证人员离开满10秒后才送客，并且同一次到访只送客一次
def test_farewell_happens_after_ten_seconds_only_once():
    app = RobotApplication(absence_timeout_s=10.0)

    app.handle_event(Event("PERSON_ENTERED", 0, "person-1"))
    app.handle_event(Event("PERSON_LEFT", 5, "person-1"))

    # 离开仅9秒，不能送客
    assert app.handle_event(Event("TICK", 14)) == []

    # 离开满10秒，产生送客效果
    farewell_effects = app.handle_event(Event("TICK", 15))
    assert [effect.value for effect in farewell_effects] == [
        "感谢光临，再见",
    ]

    # 后续Tick不得重复送客
    assert app.handle_event(Event("TICK", 16)) == []


# 验证人员在10秒内返回会取消待送客状态
def test_returning_within_ten_seconds_cancels_farewell():
    app = RobotApplication(absence_timeout_s=10.0)

    app.handle_event(Event("PERSON_ENTERED", 0, "person-1"))
    app.handle_event(Event("PERSON_LEFT", 5, "person-1"))

    # 10秒内返回：不再次欢迎
    assert app.handle_event(Event("PERSON_ENTERED", 10, "person-1")) == []

    # 原本应在15秒送客，但已返回，因此不送客
    assert app.handle_event(Event("TICK", 15)) == []


# 验证已送客的人员再次进入，会开始一次新的到访并再次欢迎
def test_entry_after_farewell_starts_a_new_visit():
    app = RobotApplication(absence_timeout_s=10.0)

    app.handle_event(Event("PERSON_ENTERED", 0, "person-1"))
    app.handle_event(Event("PERSON_LEFT", 5, "person-1"))
    app.handle_event(Event("TICK", 15))

    effects = app.handle_event(Event("PERSON_ENTERED", 20, "person-1"))

    assert [effect.value for effect in effects] == [
        "wave_hand",
        "欢迎光临",
    ]


# 验证会议进行中时，人员进入不会触发欢迎
def test_entry_during_meeting_does_not_greet():
    app = RobotApplication()

    app.handle_event(Event("MEETING_STARTED", 0))
    effects = app.handle_event(Event("PERSON_ENTERED", 1, "person-1"))

    assert effects == []


# 验证对话结束后，同一次到访的重复进入也不会补发欢迎
def test_person_entering_during_conversation_is_not_greeted_later():
    app = RobotApplication()

    app.handle_event(Event("CONVERSATION_STARTED", 0))
    assert app.handle_event(Event("PERSON_ENTERED", 1, "person-1")) == []

    app.handle_event(Event("CONVERSATION_ENDED", 2))

    # 这是同一次到访的重复进入，不应在对话结束后补发欢迎
    assert app.handle_event(Event("PERSON_ENTERED", 3, "person-1")) == []


# 验证调用方修改snapshot返回值，不会修改应用内部状态
def test_snapshot_cannot_modify_internal_state():
    app = RobotApplication()
    app.handle_event(Event("PERSON_ENTERED", 0, "person-1"))

    snapshot = app.snapshot()
    snapshot["conversation_active"] = True
    snapshot["visits"]["person-1"].is_inside = False

    current_state = app.snapshot()

    assert current_state["conversation_active"] is False
    assert current_state["visits"]["person-1"].is_inside is True


# 验证未知事件类型会明确报错，而不是被忽略
def test_unknown_event_type_raises_error():
    app = RobotApplication()

    with pytest.raises(ValueError, match="Unsupported event type"):
        app.handle_event(Event("UNKNOWN_EVENT", 0))