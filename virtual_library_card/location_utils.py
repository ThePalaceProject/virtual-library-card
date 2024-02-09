from localflavor.us.us_states import US_STATES


class LocationUtils:
    @staticmethod
    def get_library_state_name(library):
        state_name = ""
        try:
            state = next(state for state in US_STATES if state[0] == library.us_state)
            state_name = state[1]
        except KeyError as e:
            pass
        return state_name
