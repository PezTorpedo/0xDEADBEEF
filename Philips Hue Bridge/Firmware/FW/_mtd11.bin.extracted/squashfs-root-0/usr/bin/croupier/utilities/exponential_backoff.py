import urandom


class ExponentialBackOff:
    """
    Implements an exponential backoff strategy.
    """

    def __init__(self, base_delay, max_delay):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_delay = base_delay

    def get_next_delay(self) -> int:
        """
        Calculate the next delay based on the number of attempts.
        """
        self.current_delay = min(urandom.randint(self.base_delay, self.current_delay * 3), self.max_delay)
        print(f"Backing off ...{self.current_delay}")
        return self.current_delay

    def reset(self):
        """
        Reset the backoff strategy.
        """
        self.current_delay = self.base_delay
