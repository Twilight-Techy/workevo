class EvolverError(Exception):
    """Safe public domain error; no private callback exception text."""


class BudgetExceeded(EvolverError):
    pass


class DeadlineExceeded(EvolverError):
    pass


class Conflict(EvolverError):
    pass


class Incompatible(EvolverError):
    pass


class InvalidCandidate(EvolverError):
    pass
