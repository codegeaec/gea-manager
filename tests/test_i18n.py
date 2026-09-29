from gea.i18n import SUPPORTED_LANGS, catalog_keys, t


def test_catalogs_have_matching_keys():
    keys_by_lang = {lang: catalog_keys(lang) for lang in SUPPORTED_LANGS}
    reference = keys_by_lang[SUPPORTED_LANGS[0]]
    for lang, keys in keys_by_lang.items():
        assert keys == reference, f"{lang} catalog keys differ from {SUPPORTED_LANGS[0]}"


def test_t_falls_back_to_key_when_missing():
    assert t("this.key.does.not.exist") == "this.key.does.not.exist"


def test_t_formats_variables():
    assert "3" in t("doctor.summary_missing", lang="es", count=3)


def test_t_default_lang_is_spanish():
    assert t("common.yes", lang="es") == "sí"
    assert t("common.yes", lang="en") == "yes"


def test_new_command_messages_exist_in_both_languages_with_the_same_placeholders():
    import re

    from gea.i18n import _load_catalog

    en, es = _load_catalog("en"), _load_catalog("es")
    for key in (k for k in en if k.split(".")[0] in {"uninstall", "undo", "delegate", "review"}):
        assert set(re.findall(r"{(\w+)", en[key])) == set(re.findall(r"{(\w+)", es[key])), key
