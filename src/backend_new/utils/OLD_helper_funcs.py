from typing import Any
from questionary import Choice
import questionary as q
from itertools import batched

# CONSTANTS

# LOGGER
from backend_new.utils.logger import Logger
logger = Logger(__name__)

# region questionary
def questionary_select(question_to_ask: str,
                       choose_data: list[dict | str] | list[Choice],
                       use_shortcuts: bool = True,
                       enable_pages: bool = False,
                       batch_data: bool = False,
                       batch_size: int = 5,
                       enable_all: str = '',
                       enable_exit: str = '',
                       extra_navigation_options: list[dict | str] | list[Choice] = None) -> Any:
    """
    Abstraction layer for questionary select
    :param question_to_ask: Prompt to display
    :param choose_data: The select data containing a list of dicts or Choice objects
    :param use_shortcuts: Uses shortcuts for each option, can be customized
    :param enable_pages: Enables the page navigation buttons
    :param batch_data: Splits data into batches, enable_pages must be enabled to work
    :param batch_size: How many items per page
    :param enable_all: Enables the "All" button
    :param enable_exit: Enables the "Exit" button
    :param extra_navigation_options: Extra navigation options to add to the end of the list
    :return: The selected option
    """

    if batch_data and not enable_pages:
        raise Exception("Cannot batch data without enabling pages")

    choose_data = [option for option in choose_data]

    def _add_navigation_buttons(input_list: list[dict | str]):
        if enable_pages or enable_all != '' or enable_exit != '' or extra_navigation_options:
            input_list.append(q.Separator())
        if enable_pages:
            input_list.append(Choice("Next ->", value = "__next__", shortcut_key='w'))
            input_list.append(Choice("Previous <-", value= "__prev__", shortcut_key='s'))
        if enable_all != '':
            input_list.append(Choice(enable_all, value= "__all__", shortcut_key='a'))
        if enable_exit != '':
            input_list.append(Choice(enable_exit, value= "__exit__", shortcut_key='e'))
        if extra_navigation_options:
            for option in extra_navigation_options:
                input_list.append(option)

    if enable_pages and batch_data:
        offset = 0

        while True:
            batched_choose_data = list(batched(choose_data, batch_size))
            selected_batched_choose_data = list(batched_choose_data[offset])
            _add_navigation_buttons(selected_batched_choose_data)

            user_choice = q.select(question_to_ask, choices=selected_batched_choose_data, use_shortcuts=use_shortcuts).ask()
            if user_choice == "__next__":
                if offset + 1 >= len(batched_choose_data):
                    pass
                else:
                    offset += 1
            elif user_choice == "__prev__":
                if offset > 0:
                    offset -= 1
            elif user_choice == "__all__":
                break
            elif user_choice == "__exit__":
                break
            else:
                break
    else:
        _add_navigation_buttons(choose_data)
        user_choice = q.select(question_to_ask, choices=choose_data, use_shortcuts=use_shortcuts).ask()

    return user_choice

def questionary_checkbox(question_to_ask: str,
                         choice_data : list[dict | str] | list[Choice]) -> Any:
    """
    Abstraction layer for questionary checkbox
    :param question_to_ask: Prompt to display
    :param choice_data: a list of dicts or Choice objects
    :return: The selected options
    """
    return q.checkbox(question_to_ask, choices=choice_data).ask()
# endregion

