class State:
    def __init__(self, states, name="?", verbose=False):
        self.__verbose = verbose
        self.__name = name
        self.__states = states
        self.__state = "Initial"
        self.__entry = {}
        self.__exit = {}
        self.__event = {"event": None}

    def set_entry(self, state, action):
        if state not in self.__states:
            raise ValueError(f"{self.__name} => Invalid state: {state}")
        self.__entry[state] = action

    def set_exit(self, state, action):
        if state not in self.__states:
            raise ValueError(f"{self.__name} => Invalid state: {state}")
        self.__exit[state] = action

    def event(self, event):
        self.__event = event

    def ignore(self, event):
        if event == self.__event:
            self.__event = None

    def finish(self):
        if self.__event and self.__verbose:
            print(f"{self.__name} => State: {self.__state}, event: {self.__event} was unhandled")

    def set(self, state):
        if state not in self.__states:
            raise ValueError(f"{self.__name} => Invalid state: {state}")

        if self.__state in self.__exit:
            if self.__verbose:
                print(f"{self.__name} => State: {self.__state}.exit")
            self.__exit[self.__state]()

        if self.__verbose:
            print(f"{self.__name} => State: {self.__state}->{state}, event: {self.__event}")
        self.__event = None
        self.__state = state

        if state in self.__entry:
            if self.__verbose:
                print(f"{self.__name} => State: {state}.entry")
            self.__entry[state]()

    def get(self):
        return self.__state
