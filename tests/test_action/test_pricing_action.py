from src.action.inventory.upload.pricing_action import PricingAction


def test_pricing_action_builds_prices(mocker):
    ftp = mocker.Mock()
    vendor_dao = mocker.Mock()
    vendor_config = mocker.Mock()
    vendor_config.cost_adjustment_config = "adjust"
    vendor_config.sku_map_config = mocker.Mock(file_path="map.csv")
    vendor_dao.get_item.return_value = vendor_config
    ftp.get_file_as_list.return_value = [["PN1", 10.0]]

    mocker.patch("src.action.inventory.upload.pricing_action.get_sku_map", return_value={"PN1": "SKU1"})
    mocker.patch("src.action.inventory.upload.pricing_action.get_adjusted_cost", return_value=12.0)
    mocker.patch("src.action.inventory.upload.pricing_action.get_list_price", return_value=["SKU1", 15.0])

    action = PricingAction(ftp=ftp, vendor_config_dao=vendor_dao)
    action.run(request_=None)

    ftp.start.assert_called_once()
    ftp.write_list_as_csv.assert_called_once()
    ftp.close.assert_called_once()
