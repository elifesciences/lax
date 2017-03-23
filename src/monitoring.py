import rest_framework.decorators
import newrelic.agent

def api_view(*args, **kwargs):
    def decorator(func):
        label = "%s.%s" % (func.__module__, func.__name__)
        framework_decorator = rest_framework.decorators.api_view(*args, **kwargs)
        def labelled_func(*args, **kwargs):
            newrelic.agent.set_transaction_name(label)
            return func(*args, **kwargs)
        return framework_decorator(labelled_func)

    return decorator
