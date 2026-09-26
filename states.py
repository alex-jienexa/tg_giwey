from aiogram.fsm.state import State, StatesGroup

class CreateGiveawayForm(StatesGroup):
    select_channel = State()
    input_channel_manually = State() # Ввод @username или ID
    enter_title = State()
    enter_winners_count = State()
    enter_end_time = State()

class ChannelManageFS(StatesGroup):
    waiting_for_channel = State()