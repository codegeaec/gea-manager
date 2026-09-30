from gea import dryrun, managed_block


def test_upsert_keeps_everything_outside_the_markers_byte_for_byte(tmp_path):
    path = tmp_path / "AGENTS.md"
    mine = "# Mine\n\nrule 1\n\n\ttabbed  \n"
    path.write_text(mine)
    assert managed_block.upsert(path, "gea says hi") is True
    assert path.read_text().startswith(mine)
    assert managed_block.upsert(path, "gea says hi") is False  # idempotent

    managed_block.upsert(path, "new body")
    text = path.read_text()
    assert text.startswith(mine) and "new body" in text and "gea says hi" not in text
    assert text.count(managed_block.START_MARKER) == 1


def test_text_after_the_block_survives_an_update(tmp_path):
    path = tmp_path / "f.md"
    path.write_text(f"top\n{managed_block.render('old')}bottom\n")
    managed_block.upsert(path, "new")
    assert path.read_text().startswith("top\n") and path.read_text().endswith("bottom\n")


def test_remove_restores_the_users_content(tmp_path):
    path = tmp_path / "f.md"
    path.write_text("mine\n")
    managed_block.upsert(path, "block")
    assert managed_block.has_block(path)
    assert managed_block.remove(path) is True
    assert path.read_text() == "mine\n" and not managed_block.has_block(path)
    assert managed_block.remove(path) is False


def test_creates_a_missing_file_and_dry_run_writes_nothing(tmp_path):
    dryrun.enable(True)
    managed_block.upsert(tmp_path / "new" / "a.md", "x")
    assert not (tmp_path / "new").exists()
    dryrun.enable(False)
    managed_block.upsert(tmp_path / "new" / "a.md", "x")
    assert (tmp_path / "new" / "a.md").exists()
