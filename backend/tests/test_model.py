from unittest.mock import Mock

from langchain_core.messages import AIMessage, HumanMessage

from bedrock_chat import model


def test_bounded_model_and_order(monkeypatch):
    client = Mock()
    factory = Mock(return_value=client)
    constructor = Mock()
    constructor.return_value.invoke.return_value = AIMessage(
        content="answer", usage_metadata={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}
    )
    monkeypatch.setattr(model.boto3, "client", factory)
    monkeypatch.setattr(model, "ChatBedrockConverse", constructor)
    model.model.cache_clear()
    result = model.answer("latest", [{"user": "first", "assistant": "earlier"}])
    assert result["text"] == "answer"
    assert result["usage"]["total_tokens"] == 12
    constructor.return_value.invoke.assert_called_once_with([
        HumanMessage("first"), AIMessage("earlier"), HumanMessage("latest")])
    constructor.assert_called_once_with(client=client, model_id="amazon.nova-micro-v1:0",
                                        max_tokens=512, region_name="us-east-1")
    config = factory.call_args.kwargs["config"]
    assert config.connect_timeout == 2 and config.read_timeout == 15
    assert config.retries == {"total_max_attempts": 1}
    assert model.model() is model.model()
    model.model.cache_clear()
