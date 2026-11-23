from django.template import context as _django_context


def _patched_base_context_copy(self):
    duplicate = object.__new__(self.__class__)
    duplicate.__dict__ = self.__dict__.copy()
    duplicate.dicts = self.dicts[:]
    return duplicate


_django_context.BaseContext.__copy__ = _patched_base_context_copy