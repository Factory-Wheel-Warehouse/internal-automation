from importlib import reload

import src.util.aws as aws_module


def test_post_exception_to_sns_publishes(mocker):
    module = reload(aws_module)
    client = mocker.Mock()
    module.boto3_session.client = mocker.Mock(return_value=client)

    module.post_exception_to_sns("boom")

    client.publish.assert_called_once()
