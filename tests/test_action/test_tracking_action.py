from src.action.tracking.upload_action import UploadAction


def test_upload_action_invokes_tracking_service(mocker):
    mock_service = mocker.patch(
        "src.action.tracking.upload_action.TrackingUpdateService",
        autospec=True,
    )
    instance = mock_service.return_value

    UploadAction().run(request_=None)

    instance.run.assert_called_once()
