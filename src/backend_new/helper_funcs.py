import questionary as q
from typing import Any
from itertools import batched
from pathlib import Path

def questionary_select(question_to_ask: str,
                       choose_data: list[dict | str],
                       use_shortcuts: bool = False,
                       enable_pages: bool = False,
                       batch_data: bool = False,
                       batch_size: int = 5,
                       enable_all: str = '',
                       enable_exit: str = '',
                       extra_navigation_options: list[dict | str] = []) -> Any:
    import questionary as q

    if batch_data and not enable_pages:
        raise Exception("Cannot batch data without enabling pages")

    _choose_data = [option for option in choose_data]

    def _add_navigation_buttons(input_list: list[dict | str]):
        if enable_pages or enable_all != '' or enable_exit != '':
            input_list.append(q.Separator())
        if enable_pages:
            input_list.append({"name": "Next ->", "value": "__next__"})
            input_list.append({"name": "Previous <-", "value": "__prev__"})
        if enable_all != '':
            input_list.append({"name": enable_all, "value": "__all__"})
        if enable_exit != '':
            input_list.append({"name": enable_exit, "value": "__exit__"})
        if extra_navigation_options:
            for option in extra_navigation_options:
                input_list.append(option)

    if enable_pages:
        _offset = 0

        while True:
            _batched_choose_data = list(batched(choose_data, batch_size))
            _selected_batched_choose_data = list(_batched_choose_data[_offset])
            _add_navigation_buttons(_selected_batched_choose_data)

            _user_choice = q.select(question_to_ask, choices=_selected_batched_choose_data, use_shortcuts=use_shortcuts).ask()
            if _user_choice == "__next__":
                if _offset + 1 >= len(_batched_choose_data):
                    pass
                else:
                    _offset += 1
            elif _user_choice == "__prev__":
                if _offset > 0:
                    _offset -= 1
            elif _user_choice == "__all__":
                break
            elif _user_choice == "__exit__":
                break
            else:
                break
    else:
        _add_navigation_buttons(_choose_data)
        _user_choice = q.select(question_to_ask, choices=_choose_data, use_shortcuts=use_shortcuts).ask()

    return _user_choice

def read_json_file(file_path: Path) -> dict:
    import json
    return json.loads(file_path.read_text())

def write_json_file(file_path: Path, data: Any, keys: list[str] = None) -> None:
    import json

    _data = read_json_file(file_path)

    _current_level = _data
    for key in keys[:-1]:
        if key not in _current_level or not isinstance(_current_level[key], dict):
            _current_level[key] = {}
        _current_level = _current_level[key]

    if keys:
        _current_level[keys[-1]] = data

    file_path.write_text(json.dumps(_data, indent=4))
