from aiogram.fsm.state import State, StatesGroup

class CreateGiveawayForm(StatesGroup):
    select_channel = State()
    enter_title = State()
    enter_winners_count = State()
    enter_end_time = State()