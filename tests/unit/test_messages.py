from protocol.messages import ClientMessage, ServerMessage, MsgType


def test_client_message_defaults():
    m = ClientMessage(type="x")
    assert m.type == "x"
    assert m.payload == {}


def test_client_message_payload():
    m = ClientMessage(type="x", payload={"a": 1})
    assert m.payload == {"a": 1}


def test_server_message_enum_normalization():
    m = ServerMessage(type=MsgType.ROOM_CREATED, payload={"room_id": "X"})
    assert m.type == "room_created"


def test_msgtype_values_are_strings():
    for m in MsgType:
        assert isinstance(m.value, str)