from gea.tasks import store


def _project(tmp_path, location="repo"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "gea.json").write_text(
        f'{{"tasks": {{"location": "{location}"}}, "name": "demo"}}', encoding="utf-8"
    )
    return tmp_path


def test_create_task_allocates_sequential_ids(tmp_path):
    repo = _project(tmp_path)
    p1 = store.create_task("First task", repo_root=repo)
    p2 = store.create_task("Second task", repo_root=repo)
    assert p1.name.startswith("TASK-001-")
    assert p2.name.startswith("TASK-002-")


def test_create_task_home_location_uses_gea_home(tmp_path, monkeypatch):
    monkeypatch.setenv("GEA_HOME", str(tmp_path / "gea-home"))
    repo = _project(tmp_path / "repo", location="home")
    path = store.create_task("Home task", repo_root=repo)
    assert "gea-home" in str(path)
    assert "demo" in str(path)


def test_create_subtask_ids_are_sequential_within_parent(tmp_path):
    repo = _project(tmp_path)
    store.create_task("Parent task", repo_root=repo)
    s1 = store.create_subtask("TASK-001", "Sub one", repo_root=repo)
    s2 = store.create_subtask("TASK-001", "Sub two", repo_root=repo)
    assert s1.name.startswith("TASK-001.1-")
    assert s2.name.startswith("TASK-001.2-")


def test_find_task_path(tmp_path):
    repo = _project(tmp_path)
    created = store.create_task("Findable", repo_root=repo)
    found = store.find_task_path("TASK-001", repo_root=repo)
    assert found == created


def test_set_status_updates_file(tmp_path):
    repo = _project(tmp_path)
    store.create_task("Status test", repo_root=repo)
    assert store.set_status("TASK-001", "in-progress", repo_root=repo) is True
    path = store.find_task_path("TASK-001", repo_root=repo)
    assert store.read_status(path) == "in-progress"


def test_list_tasks_filters_by_status(tmp_path):
    repo = _project(tmp_path)
    store.create_task("A", repo_root=repo)
    store.create_task("B", repo_root=repo)
    store.set_status("TASK-002", "review", repo_root=repo)
    planned = store.list_tasks(status="planned", repo_root=repo)
    review = store.list_tasks(status="review", repo_root=repo)
    assert [t[0] for t in planned] == ["TASK-001"]
    assert [t[0] for t in review] == ["TASK-002"]


def test_close_task_moves_to_done(tmp_path):
    repo = _project(tmp_path)
    store.create_task("Closeable", repo_root=repo)
    assert store.close_task("TASK-001", repo_root=repo) is True
    assert store.find_task_path("TASK-001", repo_root=repo) is not None
    assert (store.tasks_dir(repo) / "done").exists()
    assert store.find_task_path("TASK-001", repo_root=repo).parent.name == "done"


def test_write_index_lists_all_tasks(tmp_path):
    repo = _project(tmp_path)
    store.create_task("A", repo_root=repo)
    index_path = store.task_root(repo) / "INDEX.md"
    assert index_path.exists()
    assert "TASK-001" in index_path.read_text(encoding="utf-8")
