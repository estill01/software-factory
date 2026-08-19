class StoreError(RuntimeError):
    pass


class StaleState(StoreError):
    pass


class AuthorityDenied(StoreError):
    pass


class InvalidTransition(StoreError):
    pass
