from wechat_emoticon_exporter.locate import list_accounts, normalize_wxid


def test_normalize_wxid():
    assert normalize_wxid("wxid_abc123_7e1e") == "wxid_abc123"
    assert normalize_wxid("wxid_abc123") == "wxid_abc123"
    assert normalize_wxid("wxid_ab_cd_1a2b") == "wxid_ab_cd"


def test_list_accounts(tmp_path):
    account = tmp_path / "wxid_test_0001"
    (account / "db_storage").mkdir(parents=True)
    (tmp_path / "all_users").mkdir()
    (tmp_path / "not_an_account").mkdir()

    accounts = list_accounts([str(tmp_path)])
    assert len(accounts) == 1
    assert accounts[0].wxid == "wxid_test"
    assert accounts[0].folder_name == "wxid_test_0001"


def test_list_accounts_missing_root():
    assert list_accounts(["Z:\\definitely\\missing"]) == []
